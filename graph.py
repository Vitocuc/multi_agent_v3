"""
graph.py

LangGraph StateGraph — the development assistant pipeline.

Nodes:
  cto_orchestrator   reads state, decides next action, spawns contexts
  worker             implements feature (file_write/file_read/test_runner only — NO git)
  git_node           pipeline-owned: branch setup before worker, commit+PR after worker
  human_gate         pauses graph — human reviews PR on GitHub
  validator          validates milestone report vs doc3 (Gemini, NO git)
  merge_node         pipeline-owned: merges PR into develop after approval + validation

Correct execution order per feature:
  worker → git_node (commit+push+PR) → human_gate → validator → merge_node → cto

Workers and validators have zero git access.
All version control is handled by git_node and merge_node using git_ops.py.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, List, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from schemas.graph_state  import GraphState, FeatureContext, WorkerResult, ValidatorResult
from schemas.pipeline_state import ProjectState, Phase, FeatureStatus, FeatureRecord
from agents  import cto as cto_agent
from agents  import worker as worker_agent
from agents  import validator as validator_agent
from feature_menu import present_and_select
from memory  import store as mem_store
from gates   import state_store
import git_ops
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
    """Main routing node. Runs after every node completes."""
    phase    = state.get("phase", "clarification")
    provider = state.get("cto_model", "claude")
    ps       = state_store.load(ROOT)

    # ── CLARIFICATION ────────────────────────────────────────────────────────
    if phase == "clarification":
        history = state.get("clarification_history", [])
        print(c(CYAN, "  CTO: clarifying..."))
        q = cto_agent.get_next_question(history, provider, ROOT)

        if q.sufficient:
            print(c(DIM, "  CTO: has enough. Writing plan..."))
            plan = cto_agent.write_plan(history, provider, ROOT)
            ps.add_log("info", "Plan ready for review")
            state_store.save(ps, ROOT)
            return {**state, "phase": "plan_review", "gate_type": "plan_approval",
                    "gate_message": (
                        f"Plan ready.\n\nSummary: {plan.summary}\n\n"
                        f"First milestone: {plan.first_milestone}\n\n"
                        "Review doc0_project_brief.md then:\n"
                        "  python run.py resume --decision approve"
                    )}

        print()
        print(c(BOLD, f"CTO (round {state.get('clarification_round', 0) + 1}):"))
        print(q.question)
        print(c(DIM,  f"  Why: {q.why_important}"))
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
        return {**state, "clarification_history": new_history,
                "clarification_round": ps.clarification_round}

    # ── PLAN REVIEW (gate) ───────────────────────────────────────────────────
    if phase == "plan_review":
        if state.get("gate_type"):
            return state
        ps.plan_approved = True
        ps.phase = Phase.CONTRACT_GEN
        ps.add_log("info", "Plan approved")
        state_store.save(ps, ROOT)
        return {**state, "phase": "contract_gen", "gate_type": None}

    # ── CONTRACT GENERATION ──────────────────────────────────────────────────
    if phase == "contract_gen":
        print(c(CYAN, "  CTO: generating contracts..."))
        result   = cto_agent.generate_contracts(provider, ROOT)
        features = result["features"]
        for f in features:
            fid = f["feature_id"]
            ps.features[fid] = FeatureRecord(
                feature_id=fid, title=f.get("title", ""),
                milestone_id=f.get("milestone_id", ""),
                depends_on=f.get("depends_on", []),
            )
        ps.phase = Phase.CONTRACT_REVIEW
        ps.add_log("info", f"Contracts generated: {len(features)} features")
        state_store.save(ps, ROOT)
        return {**state, "phase": "contract_review",
                "gate_type": "contract_approval",
                "gate_message": (
                    f"{len(features)} features across "
                    f"{len(set(f.get('milestone_id','?') for f in features))} milestones.\n"
                    "Review doc1, doc2, doc3 then:\n"
                    "  python run.py resume --decision approve"
                )}

    # ── CONTRACT REVIEW (gate) ───────────────────────────────────────────────
    if phase == "contract_review":
        if state.get("gate_type"):
            return state
        ps.contracts_approved = True
        ps.phase = Phase.FEATURE_SELECTION
        ps.add_log("info", "Contracts approved")
        state_store.save(ps, ROOT)
        return {**state, "phase": "feature_selection", "gate_type": None}

    # ── FEATURE SELECTION ────────────────────────────────────────────────────
    if phase == "feature_selection":
        features_raw = _load_features_from_doc2(ROOT)
        passed       = [fid for fid, fr in ps.features.items()
                        if fr.status == FeatureStatus.PASSED]
        selected     = present_and_select(features_raw, passed)
        if not selected:
            print(c(YELLOW, "  No features selected."))
            return {**state, "phase": "complete"}

        spawn = cto_agent.build_spawn_plan(features_raw, selected, passed, provider)
        print(c(DIM, f"\n  Spawn plan: batch={spawn.batch}"))
        print(c(DIM, f"  Reasoning: {spawn.reasoning}\n"))

        contexts = cto_agent.build_feature_contexts(features_raw, selected, passed, ROOT)

        # Setup git branches for all selected features NOW (before worker runs)
        for fid in selected:
            ctx = contexts.get(fid)
            if not ctx:
                continue
            branch = ctx["branch_name"]
            print(c(DIM, f"  Setting up branch: {branch}"))
            r = git_ops.setup_branch(fid, branch, ROOT)
            if not r.success:
                print(c(YELLOW, f"  ⚠ Branch setup warning for {fid}: {r.stderr[:100]}"))

        for fid in selected:
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.SELECTED
        ps.phase = Phase.IMPLEMENTATION
        ps.add_log("info", f"Selected {len(selected)} features: {selected}")
        state_store.save(ps, ROOT)
        return {**state, "phase": "implementation",
                "selected_features": selected,
                "feature_contexts":  contexts,
                "gate_type": None}

    # ── IMPLEMENTATION ───────────────────────────────────────────────────────
    if phase == "implementation":
        return _route_implementation_state(state, ps)

    # ── COMPLETE ─────────────────────────────────────────────────────────────
    if phase == "complete":
        print(c(GREEN, "\n  ✓ All selected features complete.\n"))
        ps.phase = Phase.COMPLETE
        state_store.save(ps, ROOT)
        return {**state, "phase": "complete"}

    return state


def _route_implementation_state(state: GraphState, ps: ProjectState) -> GraphState:
    """Decide what to do next in implementation phase."""
    worker_results  = state.get("worker_results", {}) or {}
    val_results     = state.get("validator_results", {}) or {}
    git_results     = state.get("git_results", {}) or {}
    merge_results   = state.get("merge_results", {}) or {}
    contexts        = state.get("feature_contexts", {}) or {}

    if ps.is_complete():
        return {**state, "phase": "complete"}
    return state  # routing edges handle next node selection


# ---------------------------------------------------------------------------
# Node: worker
# ---------------------------------------------------------------------------

def worker_node(state: GraphState) -> GraphState:
    """Implement one feature. No git access."""
    contexts       = dict(state.get("feature_contexts", {}) or {})
    worker_results = dict(state.get("worker_results",  {}) or {})

    for fid, ctx in contexts.items():
        if fid in worker_results:
            continue
        print(c(BOLD, f"\n  → Worker: {fid} — {ctx['title']}"))

        result = worker_agent.run(ctx, ROOT)

        ps = state_store.load(ROOT)
        if fid in ps.features:
            if result["success"]:
                print(c(GREEN, f"  ✓ Worker {fid}: milestone report filed"))
                ps.features[fid].status = FeatureStatus.IN_PROGRESS
                ps.add_log("info", f"Worker {fid} complete — pipeline will commit+push")
            else:
                print(c(RED, f"  ✗ Worker {fid} failed: {result['error']}"))
                ps.features[fid].status = FeatureStatus.FAILED
                ps.features[fid].last_error = result["error"]
                ps.add_log("error", f"Worker {fid} failed", result["error"])
            state_store.save(ps, ROOT)

        return {**state, "worker_results": {**worker_results, fid: result}}

    return state


# ---------------------------------------------------------------------------
# Node: git_node — pipeline-owned, no AI
# ---------------------------------------------------------------------------

def git_node(state: GraphState) -> GraphState:
    """
    Pipeline-owned git operations. Fires after worker completes.
    1. Commits all files the worker wrote
    2. Pushes to origin
    3. Opens PR targeting develop
    No AI involved — pure Python subprocess via git_ops.py.
    """
    worker_results = dict(state.get("worker_results", {}) or {})
    git_results    = dict(state.get("git_results",    {}) or {})
    contexts       = dict(state.get("feature_contexts", {}) or {})

    for fid, wr in worker_results.items():
        if fid in git_results:
            continue

        ctx        = contexts.get(fid, {})
        branch     = ctx.get("branch_name", f"feature/{fid.lower()}")
        title      = ctx.get("title", fid)
        report     = ROOT / "reports" / f"{fid}_milestone.md"

        if not wr.get("success"):
            # Worker failed — skip git, record failure
            git_results[fid] = {"success": False, "error": "worker_failed", "pr_url": ""}
            return {**state, "git_results": git_results}

        print(c(CYAN, f"  Git: committing {fid}..."))

        # Commit + push
        r = git_ops.commit_and_push(fid, branch, ROOT)
        if not r.success:
            print(c(RED, f"  ✗ Git commit/push failed: {r.output[:120]}"))
            git_results[fid] = {"success": False, "error": r.output, "pr_url": ""}
            ps = state_store.load(ROOT)
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.FAILED
                ps.features[fid].last_error = f"git push failed: {r.stderr[:100]}"
                state_store.save(ps, ROOT)
            return {**state, "git_results": git_results}

        print(c(GREEN, f"  ✓ Pushed {branch}"))

        # Open PR
        print(c(CYAN, f"  Git: opening PR for {fid}..."))
        pr_r = git_ops.open_pr(fid, title, report, ROOT)
        pr_url = ""
        if pr_r.success:
            pr_url = pr_r.stdout.strip()
            print(c(GREEN, f"  ✓ PR opened: {pr_url}"))
        else:
            print(c(YELLOW, f"  ⚠ PR open failed: {pr_r.output[:120]}"))
            print(c(DIM,    "  You can open it manually on GitHub."))

        git_results[fid] = {"success": True, "error": "", "pr_url": pr_url}

        ps = state_store.load(ROOT)
        if fid in ps.features:
            ps.features[fid].status = FeatureStatus.IN_PROGRESS
            ps.add_log("info", f"PR opened for {fid}: {pr_url}")
            state_store.save(ps, ROOT)

        # Set human gate — pipeline pauses here for PR review
        return {**state,
                "git_results": git_results,
                "gate_type":   "pr_review",
                "gate_feature": fid,
                "gate_message": (
                    f"PR opened for [{fid}] {title}\n"
                    f"URL: {pr_url or 'check GitHub'}\n\n"
                    "Review the PR diff on GitHub, then:\n"
                    "  python run.py gh-check " + fid + "\n"
                    "  python run.py resume --decision approve"
                )}

    return state


# ---------------------------------------------------------------------------
# Node: human gate
# ---------------------------------------------------------------------------

def human_gate(state: GraphState) -> GraphState:
    """LangGraph interrupts before this node. Graph pauses until resume."""
    return state


# ---------------------------------------------------------------------------
# Node: validator
# ---------------------------------------------------------------------------

def validator_node(state: GraphState) -> GraphState:
    """
    Validate milestone report vs doc3 test suite.
    Fires AFTER human gate approval — validator never runs on unreviewed code.
    """
    worker_results = dict(state.get("worker_results", {}) or {})
    val_results    = dict(state.get("validator_results", {}) or {})
    provider       = state.get("validator_model", "gemini")

    for fid, wr in worker_results.items():
        if fid in val_results:
            continue
        if not wr.get("success"):
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
                    print(c(RED, f"    Security escalations: {result['escalations']}"))
            ps.add_log("info" if result["overall"] == "pass" else "warn",
                       f"Validator {fid}: {result['overall']}")
            state_store.save(ps, ROOT)

        return {**state, "validator_results": {**val_results, fid: result}}

    return state


# ---------------------------------------------------------------------------
# Node: merge_node — pipeline-owned, no AI
# ---------------------------------------------------------------------------

def merge_node(state: GraphState) -> GraphState:
    """
    Merge the feature PR into develop after validation passes.
    Pipeline-owned — no AI involvement.
    """
    val_results    = dict(state.get("validator_results", {}) or {})
    merge_results  = dict(state.get("merge_results",    {}) or {})

    for fid, vr in val_results.items():
        if fid in merge_results:
            continue
        if vr.get("overall") != "pass":
            merge_results[fid] = {"success": False, "error": "validation_failed"}
            return {**state, "merge_results": merge_results}

        print(c(CYAN, f"  Merging PR for {fid}..."))
        r = git_ops.merge_pr(fid, ROOT)

        if r.success:
            print(c(GREEN, f"  ✓ PR merged for {fid}"))
            ps = state_store.load(ROOT)
            if fid in ps.features:
                ps.add_log("info", f"PR merged for {fid}")
                state_store.save(ps, ROOT)
        else:
            print(c(YELLOW, f"  ⚠ Auto-merge failed: {r.output[:120]}"))
            print(c(DIM,    "  Merge manually on GitHub or re-run after checks pass."))

        merge_results[fid] = {"success": r.success, "error": r.stderr[:200]}
        return {**state, "merge_results": merge_results}

    return state


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_from_cto(state: GraphState) -> str:
    phase = state.get("phase", "clarification")
    gate  = state.get("gate_type")

    if gate:
        return "human_gate"
    if phase in ("clarification", "plan_review", "contract_gen",
                 "contract_review", "feature_selection"):
        return "cto_orchestrator"
    if phase == "implementation":
        return _route_impl(state)
    if phase == "complete":
        return END
    return "cto_orchestrator"


def _route_impl(state: GraphState) -> str:
    contexts       = state.get("feature_contexts", {}) or {}
    worker_results = state.get("worker_results",   {}) or {}
    git_results    = state.get("git_results",      {}) or {}
    val_results    = state.get("validator_results",{}) or {}
    merge_results  = state.get("merge_results",    {}) or {}

    # Need merge?
    for fid in val_results:
        if fid not in merge_results:
            return "merge"

    # Need validation? (only after git_results confirm PR was opened)
    for fid in git_results:
        if fid not in val_results and git_results[fid].get("success"):
            return "validator"

    # Need git commit+PR?
    for fid in worker_results:
        if fid not in git_results:
            return "git"

    # Need worker?
    for fid in contexts:
        if fid not in worker_results:
            return "worker"

    return "cto_orchestrator"


def route_after_worker(state: GraphState) -> str:
    return "git"

def route_after_git(state: GraphState) -> str:
    gate = state.get("gate_type")
    return "human_gate" if gate else "validator"

def route_after_gate(state: GraphState) -> str:
    return "validator"

def route_after_validator(state: GraphState) -> str:
    return "merge"

def route_after_merge(state: GraphState) -> str:
    return "cto_orchestrator"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(db_path: str = "checkpoints.db") -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("cto_orchestrator", cto_orchestrator)
    builder.add_node("worker",           worker_node)
    builder.add_node("git",              git_node)
    builder.add_node("human_gate",       human_gate)
    builder.add_node("validator",        validator_node)
    builder.add_node("merge",            merge_node)

    builder.set_entry_point("cto_orchestrator")

    builder.add_conditional_edges("cto_orchestrator", route_from_cto, {
        "cto_orchestrator": "cto_orchestrator",
        "worker":           "worker",
        "git":              "git",
        "validator":        "validator",
        "merge":            "merge",
        "human_gate":       "human_gate",
        END:                END,
    })
    builder.add_conditional_edges("worker",     route_after_worker,    {"git":              "git"})
    builder.add_conditional_edges("git",        route_after_git,       {"human_gate":       "human_gate",
                                                                         "validator":        "validator"})
    builder.add_conditional_edges("human_gate", route_after_gate,      {"validator":        "validator"})
    builder.add_conditional_edges("validator",  route_after_validator,  {"merge":            "merge"})
    builder.add_conditional_edges("merge",      route_after_merge,      {"cto_orchestrator": "cto_orchestrator"})

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
