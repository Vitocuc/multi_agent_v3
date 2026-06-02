"""
graph.py

LangGraph StateGraph — the development assistant pipeline.

Nodes:
  cto_orchestrator   reads state, decides next action, spawns contexts
  worker             implements one feature via Claude API with tools
  validator          validates one feature via Gemini against doc3
  human_gate         writes gate to state, triggers LangGraph interrupt

Edges:
  Conditional — the CTO routes based on GraphState after each node completes.

Checkpointer:
  SqliteSaver → checkpoints.db — every node write persisted.
  Graph is resumable after any interrupt or crash.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Annotated, Dict, List, Optional

from langgraph.graph      import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages

from schemas.graph_state  import GraphState, FeatureContext, WorkerResult, ValidatorResult
from schemas.pipeline_state import ProjectState, Phase, FeatureStatus, FeatureRecord
from agents  import cto as cto_agent
from agents  import worker as worker_agent
from agents  import validator as validator_agent
from feature_menu import present_and_select
from memory  import store as mem_store
from gates   import state_store
import json

ROOT = Path(__file__).parent

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
DIM    = "\033[2m"

def c(col: str, txt: str) -> str:
    return f"{col}{txt}{RESET}"


# ---------------------------------------------------------------------------
# Node: CTO orchestrator
# ---------------------------------------------------------------------------

def cto_orchestrator(state: GraphState) -> GraphState:
    """
    Main routing node. Reads phase and decides what to do next.
    Runs after every other node completes.
    """
    phase    = state.get("phase", "clarification")
    provider = state.get("cto_model", "claude")
    ps       = state_store.load(ROOT)

    # ── CLARIFICATION ───────────────────────────────────────────────────────
    if phase == "clarification":
        history = state.get("clarification_history", [])
        print(c(CYAN, "  CTO: clarifying..."))

        q = cto_agent.get_next_question(history, provider, ROOT)

        if q.sufficient:
            print(c(DIM, "  CTO: enough info. Writing plan..."))
            plan = cto_agent.write_plan(history, provider, ROOT)
            ps.plan_approved = False
            ps.add_log("info", "Plan ready for review")
            state_store.save(ps, ROOT)
            return {**state,
                "phase":       "plan_review",
                "gate_type":   "plan_approval",
                "gate_message": (
                    f"Plan ready.\n\nSummary: {plan.summary}\n\n"
                    f"First milestone: {plan.first_milestone}\n\n"
                    "Review doc0_project_brief.md then run:\n"
                    "  python run.py resume --decision approve"
                ),
            }

        # Ask the question interactively
        print()
        print(c(BOLD, f"CTO (round {state.get('clarification_round', 0) + 1}):"))
        print(q.question)
        print(c(DIM, f"  Why: {q.why_important}"))
        print()
        print(c(CYAN, "Your answer (Enter to skip): "), end="", flush=True)
        try:
            answer = input().strip() or "[skipped]"
        except (EOFError, KeyboardInterrupt):
            answer = "[interrupted]"

        cto_agent.append_clarification_round(
            ROOT, state.get("clarification_round", 0) + 1, q.question, answer
        )
        from llm.router import assistant_msg, user_msg
        new_history = list(state.get("clarification_history", [])) + [
            assistant_msg(q.question), user_msg(answer)
        ]
        ps.clarification_round += 1
        ps.add_log("info", f"Clarification round {ps.clarification_round}")
        state_store.save(ps, ROOT)
        return {**state,
            "clarification_history": new_history,
            "clarification_round":   ps.clarification_round,
        }

    # ── PLAN REVIEW (gate pending — will be interrupted) ────────────────────
    if phase == "plan_review":
        if state.get("gate_type"):
            return state  # gate handler will interrupt
        # Gate was cleared by human → move to contract gen
        ps.plan_approved = True
        ps.phase = Phase.CONTRACT_GEN
        ps.add_log("info", "Plan approved → generating contracts")
        state_store.save(ps, ROOT)
        return {**state, "phase": "contract_gen", "gate_type": None, "gate_message": None}

    # ── CONTRACT GENERATION ─────────────────────────────────────────────────
    if phase == "contract_gen":
        print(c(CYAN, "  CTO: generating contracts..."))
        result = cto_agent.generate_contracts(provider, ROOT)
        features = result["features"]

        # Populate pipeline state
        for f in features:
            fid = f["feature_id"]
            ps.features[fid] = FeatureRecord(
                feature_id=fid,
                title=f.get("title", ""),
                milestone_id=f.get("milestone_id", ""),
                depends_on=f.get("depends_on", []),
            )
        ps.phase = Phase.CONTRACT_REVIEW
        ps.add_log("info", f"Contracts generated: {len(features)} features")
        state_store.save(ps, ROOT)

        return {**state,
            "phase":          "contract_review",
            "gate_type":      "contract_approval",
            "gate_message":   (
                f"{len(features)} features across "
                f"{len(set(f.get('milestone_id','?') for f in features))} milestones.\n"
                "Review doc1, doc2, doc3 then run:\n"
                "  python run.py resume --decision approve"
            ),
        }

    # ── CONTRACT REVIEW (gate) ───────────────────────────────────────────────
    if phase == "contract_review":
        if state.get("gate_type"):
            return state
        ps.contracts_approved = True
        ps.phase = Phase.FEATURE_SELECTION
        ps.add_log("info", "Contracts approved → feature selection")
        state_store.save(ps, ROOT)
        return {**state, "phase": "feature_selection", "gate_type": None}

    # ── FEATURE SELECTION ────────────────────────────────────────────────────
    if phase == "feature_selection":
        features_raw = _load_features_from_doc2(ROOT)
        passed       = [fid for fid, fr in ps.features.items()
                        if fr.status == FeatureStatus.PASSED]
        selected     = present_and_select(features_raw, passed)

        if not selected:
            print(c(YELLOW, "  No features selected. Exiting."))
            return {**state, "phase": "complete"}

        # Build spawn plan
        spawn = cto_agent.build_spawn_plan(features_raw, selected, passed, provider)
        print(c(DIM, f"\n  Spawn plan: batch={spawn.batch}"))
        print(c(DIM, f"  Reasoning: {spawn.reasoning}\n"))

        # Build contexts
        contexts = cto_agent.build_feature_contexts(features_raw, selected, passed, ROOT)

        # Mark selected in state
        for fid in selected:
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.SELECTED
        ps.phase = Phase.IMPLEMENTATION
        ps.add_log("info", f"Selected {len(selected)} features: {selected}")
        state_store.save(ps, ROOT)

        return {**state,
            "phase":            "implementation",
            "selected_features": selected,
            "feature_contexts":  contexts,
            "gate_type": None,
        }

    # ── IMPLEMENTATION ───────────────────────────────────────────────────────
    if phase == "implementation":
        worker_results = dict(state.get("worker_results", {}) or {})
        val_results    = dict(state.get("validator_results", {}) or {})
        selected       = list(state.get("selected_features", []))

        # All selected features validated?
        all_done = all(
            fid in val_results and val_results[fid]["overall"] in ("pass", "fail")
            for fid in selected
        )
        if all_done:
            passed_now = [fid for fid in selected
                          if val_results.get(fid, {}).get("overall") == "pass"]
            failed_now = [fid for fid in selected
                          if val_results.get(fid, {}).get("overall") == "fail"]
            print(c(GREEN, f"\n  Batch complete: {len(passed_now)} passed, {len(failed_now)} failed."))
            ps.phase = Phase.COMPLETE if not failed_now else ps.phase
            state_store.save(ps, ROOT)
            return {**state, "phase": "complete" if not failed_now else "implementation"}

        return state  # worker/validator nodes will fire

    # ── COMPLETE ─────────────────────────────────────────────────────────────
    if phase == "complete":
        print(c(GREEN, "\n  ✓ All selected features complete.\n"))
        ps.phase = Phase.COMPLETE
        state_store.save(ps, ROOT)
        return {**state, "phase": "complete"}

    return state


# ---------------------------------------------------------------------------
# Node: worker
# ---------------------------------------------------------------------------

def worker_node(state: GraphState) -> GraphState:
    """
    Run worker for the next pending feature context.
    One feature per node invocation.
    """
    contexts       = dict(state.get("feature_contexts", {}) or {})
    worker_results = dict(state.get("worker_results", {}) or {})
    val_results    = dict(state.get("validator_results", {}) or {})

    # Find next feature not yet worked on or validated
    for fid, ctx in contexts.items():
        if fid in worker_results:
            continue
        print(c(BOLD, f"\n  → Worker: {fid} — {ctx['title']}"))

        result = worker_agent.run(ctx, ROOT)

        if result["success"]:
            print(c(GREEN, f"  ✓ Worker {fid}: milestone report filed"))
            ps = state_store.load(ROOT)
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.VALIDATING
                ps.add_log("info", f"Worker {fid} complete")
                state_store.save(ps, ROOT)
        else:
            print(c(RED, f"  ✗ Worker {fid} failed: {result['error']}"))
            ps = state_store.load(ROOT)
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.FAILED
                ps.features[fid].last_error = result["error"]
                ps.add_log("error", f"Worker {fid} failed", result["error"])
                state_store.save(ps, ROOT)

        return {**state,
            "worker_results": {**worker_results, fid: result}
        }

    return state


# ---------------------------------------------------------------------------
# Node: validator
# ---------------------------------------------------------------------------

def validator_node(state: GraphState) -> GraphState:
    """
    Run validator for the next feature that has a worker result but no validator result.
    """
    worker_results = dict(state.get("worker_results", {}) or {})
    val_results    = dict(state.get("validator_results", {}) or {})
    provider       = state.get("validator_model", "gemini")

    for fid, wr in worker_results.items():
        if fid in val_results:
            continue
        if not wr.get("success"):
            # Skip validation for failed workers
            val_results[fid] = ValidatorResult(
                feature_id=fid, overall="fail", blocking_passed=False,
                failures=["worker_failed"], escalations=[], results=[],
            )
            return {**state, "validator_results": val_results}

        print(c(CYAN, f"  Validating {fid}..."))
        result = validator_agent.run(
            feature_id=fid,
            milestone_report=wr["milestone_report"],
            provider=provider,
            root=ROOT,
        )

        ps = state_store.load(ROOT)
        if fid in ps.features:
            if result["overall"] == "pass":
                ps.features[fid].status = FeatureStatus.PASSED
                ps.features[fid].validator_result = "pass"
                print(c(GREEN, f"  ✓ {fid} passed validation"))
                # Extract memory
                mem   = mem_store.load(ROOT)
                added = mem_store.append_from_milestone(wr["milestone_report"], fid, mem)
                mem_store.save(mem, ROOT)
                total = sum(len(v) for v in added.values())
                if total:
                    print(c(DIM, f"    Memory: {total} new entries"))
            else:
                ps.features[fid].status = FeatureStatus.FAILED
                ps.features[fid].validator_result = "fail"
                print(c(RED, f"  ✗ {fid} failed: {result['failures']}"))
                if result["escalations"]:
                    print(c(RED, f"    Escalations: {result['escalations']}"))
            ps.add_log("info" if result["overall"] == "pass" else "warn",
                       f"Validator {fid}: {result['overall']}")
            state_store.save(ps, ROOT)

        return {**state,
            "validator_results": {**val_results, fid: result}
        }

    return state


# ---------------------------------------------------------------------------
# Node: human gate
# ---------------------------------------------------------------------------

def human_gate(state: GraphState) -> GraphState:
    """
    Writes the gate to state. LangGraph will interrupt_before this node,
    causing the graph to pause and wait for resume.
    """
    return state  # state already contains gate_type + gate_message


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------

def route_from_cto(state: GraphState) -> str:
    """Route after CTO orchestrator runs."""
    phase    = state.get("phase", "clarification")
    gate     = state.get("gate_type")

    if gate:
        return "human_gate"
    if phase == "clarification":
        return "cto_orchestrator"
    if phase in ("plan_review", "contract_review"):
        return "cto_orchestrator"
    if phase == "contract_gen":
        return "cto_orchestrator"
    if phase == "feature_selection":
        return "cto_orchestrator"
    if phase == "implementation":
        return _route_implementation(state)
    if phase == "complete":
        return END
    return "cto_orchestrator"


def _route_implementation(state: GraphState) -> str:
    contexts       = state.get("feature_contexts", {}) or {}
    worker_results = state.get("worker_results", {}) or {}
    val_results    = state.get("validator_results", {}) or {}

    # Any feature needs a validator?
    for fid in worker_results:
        if fid not in val_results:
            return "validator"

    # Any feature needs a worker?
    for fid in contexts:
        if fid not in worker_results:
            return "worker"

    # All done
    return "cto_orchestrator"


def route_after_worker(state: GraphState) -> str:
    return "validator"


def route_after_validator(state: GraphState) -> str:
    return "cto_orchestrator"


def route_after_gate(state: GraphState) -> str:
    return "cto_orchestrator"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(db_path: str = "checkpoints.db") -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("cto_orchestrator", cto_orchestrator)
    builder.add_node("worker",           worker_node)
    builder.add_node("validator",        validator_node)
    builder.add_node("human_gate",       human_gate)

    builder.set_entry_point("cto_orchestrator")

    builder.add_conditional_edges("cto_orchestrator", route_from_cto, {
        "cto_orchestrator": "cto_orchestrator",
        "worker":           "worker",
        "validator":        "validator",
        "human_gate":       "human_gate",
        END:                END,
    })
    builder.add_conditional_edges("worker",    route_after_worker,    {"validator": "validator"})
    builder.add_conditional_edges("validator", route_after_validator, {"cto_orchestrator": "cto_orchestrator"})
    builder.add_conditional_edges("human_gate", route_after_gate,     {"cto_orchestrator": "cto_orchestrator"})

    checkpointer = SqliteSaver.from_conn_string(db_path)
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_gate"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_features_from_doc2(root: Path):
    from agents.cto import _parse_feature_blocks
    doc2 = root / "doc2_features_contract.md"
    if not doc2.exists():
        return []
    return _parse_feature_blocks(doc2.read_text())
