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
from pathlib import Path

import sqlite3 as _sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from schemas.graph_state import GraphState, ValidatorResult
from schemas.pipeline_state import ProjectState, Phase, FeatureStatus, FeatureRecord
from agents import cto as cto_agent
from agents import worker as worker_agent
from agents import validator as validator_agent
from feature_menu import present_and_select
from memory import store as mem_store
from gates import state_store
from docker.runner import build_image, DEFAULT_IMAGE
import git_ops
import os
import subprocess

ROOT = Path(__file__).parent

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"


def c(col: str, txt: str) -> str:
    return f"{col}{txt}{RESET}"


# ---------------------------------------------------------------------------
# Node: CTO orchestrator
# ---------------------------------------------------------------------------


def cto_orchestrator(state: GraphState) -> GraphState:
    """Main routing node. Runs after every node completes."""
    phase = state.get("phase", "clarification")
    provider = state.get("cto_model", "claude")
    ps = state_store.load(ROOT)

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
            return {
                **state,
                "phase": "plan_review",
                "gate_type": "plan_approval",
                "gate_message": (
                    f"Plan ready.\n\nSummary: {plan.summary}\n\n"
                    f"First milestone: {plan.first_milestone}\n\n"
                    "Review doc0_project_brief.md then:\n"
                    "  python run.py resume --decision approve"
                ),
            }

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
            assistant_msg(q.question),
            user_msg(answer),
        ]
        ps.clarification_round += 1
        ps.add_log("info", f"Clarification round {ps.clarification_round}")
        state_store.save(ps, ROOT)
        return {
            **state,
            "clarification_history": new_history,
            "clarification_round": ps.clarification_round,
        }

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
        result = cto_agent.generate_contracts(provider, ROOT)
        features = result["features"]
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
        return {
            **state,
            "phase": "contract_review",
            "gate_type": "contract_approval",
            "gate_message": (
                f"{len(features)} features across "
                f"{len(set(f.get('milestone_id', '?') for f in features))} milestones.\n"
                "Review doc1, doc2, doc3 then:\n"
                "  python run.py resume --decision approve"
            ),
        }

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
        # Ensure Docker test image exists before spawning workers
        image = os.environ.get("TEST_IMAGE", DEFAULT_IMAGE)
        import subprocess

        r = subprocess.run(
            ["docker", "image", "inspect", image], capture_output=True, text=True
        )
        if r.returncode != 0:
            print(c(DIM, f"  Building test image: {image}..."))
            result = build_image(ROOT, image)
            if result.exit_code != 0:
                print(
                    c(RED, f"  ✗ Failed to build test image (exit {result.exit_code})")
                )
                return {
                    **state,
                    "phase": "implementation",
                    "last_error": f"docker build failed: exit {result.exit_code}",
                }
            print(c(GREEN, "  ✓ Test image built"))

        features_raw = _load_features_from_doc2(ROOT)
        passed = [
            fid for fid, fr in ps.features.items() if fr.status == FeatureStatus.PASSED
        ]
        selected = present_and_select(features_raw, passed)
        if not selected:
            print(c(YELLOW, "  No features selected."))
            return {**state, "phase": "complete"}

        spawn = cto_agent.build_spawn_plan(features_raw, selected, passed, provider)
        print(c(DIM, f"\n  Spawn plan: batch={spawn.batch}"))
        print(c(DIM, f"  Reasoning: {spawn.reasoning}\n"))

        contexts = cto_agent.build_feature_contexts(
            features_raw, selected, passed, ROOT
        )

        # Setup git branches for all selected features NOW (before worker runs)
        for fid in selected:
            ctx = contexts.get(fid)
            if not ctx:
                continue
            branch = ctx["branch_name"]
            print(c(DIM, f"  Setting up branch: {branch}"))
            r = git_ops.setup_branch(fid, branch, ROOT)
            if not r.success:
                print(
                    c(YELLOW, f"  ⚠ Branch setup warning for {fid}: {r.stderr[:100]}")
                )

        for fid in selected:
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.SELECTED
        ps.phase = Phase.IMPLEMENTATION
        ps.add_log("info", f"Selected {len(selected)} features: {selected}")
        state_store.save(ps, ROOT)
        return {
            **state,
            "phase": "implementation",
            "selected_features": selected,
            "feature_contexts": contexts,
            "gate_type": None,
        }

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


def _ensure_test_image(state: GraphState) -> bool:
    """Build the Docker test image if it doesn't exist. Returns True if ready."""
    image = os.environ.get("TEST_IMAGE", DEFAULT_IMAGE)
    r = subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True, text=True
    )
    if r.returncode == 0:
        return True
    print(c(DIM, f"  Building test image: {image}..."))
    result = build_image(ROOT, image)
    if result.exit_code != 0:
        print(c(RED, f"  ✗ Failed to build test image (exit {result.exit_code})"))
        return False
    print(c(GREEN, "  ✓ Test image built"))
    return True


def _route_implementation_state(state: GraphState, ps: ProjectState) -> GraphState:
    """Decide what to do next in implementation phase."""
    worker_results = state.get("worker_results", {}) or {}

    if ps.is_complete():
        return {**state, "phase": "complete"}

    # If all SELECTED features are done (passed/skipped/failed), stop looping
    selected = set(state.get("selected_features", []) or [])
    if selected:
        statuses = {
            fid: ps.features[fid].status for fid in selected if fid in ps.features
        }
        done = all(s in ("passed", "skipped", "failed") for s in statuses.values())
        if done:
            if all(s == "failed" for s in statuses.values()):
                # Separate genuine failures from cascading blocks.
                # Blocked features had no chance to run — reset them to pending
                # so they can be selected again once their dependency is retried.
                blocked = [
                    fid
                    for fid in selected
                    if ps.features[fid].last_error.startswith("Blocked:")
                ]
                genuine = [fid for fid in selected if fid not in blocked]
                for fid in blocked:
                    ps.features[fid].status = FeatureStatus.PENDING
                    ps.features[fid].last_error = ""
                if blocked:
                    ps.add_log(
                        "info",
                        f"Reset {len(blocked)} blocked features to pending: {blocked}",
                    )
                    state_store.save(ps, ROOT)
                print(c(RED, f"  ✗ {len(genuine)} feature(s) failed: {genuine}"))
                if blocked:
                    print(
                        c(
                            YELLOW,
                            f"  {len(blocked)} feature(s) unblocked (reset to pending): {blocked}",
                        )
                    )
                print(
                    c(
                        YELLOW,
                        "  Returning to feature selection — retry the failed feature(s).",
                    )
                )
                return {
                    **state,
                    "phase": "feature_selection",
                    "selected_features": [],
                    "feature_contexts": {},
                    "worker_results": {},
                    "git_results": {},
                    "validator_results": {},
                    "merge_results": {},
                    "gate_type": None,
                }
            else:
                print(c(GREEN, "  ✓ All selected features complete."))
            return {**state, "phase": "complete"}

    # Build test image once before any worker runs
    needs_worker = any(
        fid not in worker_results for fid in (state.get("feature_contexts", {}) or {})
    )
    if needs_worker and not _ensure_test_image(state):
        print(c(YELLOW, "  Cannot build test image — aborting."))
        return {**state, "phase": "complete"}

    return state  # routing edges handle next node selection


# ---------------------------------------------------------------------------
# Node: worker
# ---------------------------------------------------------------------------


def worker_node(state: GraphState) -> GraphState:
    """Implement one feature. No git access."""
    contexts = dict(state.get("feature_contexts", {}) or {})
    worker_results = dict(state.get("worker_results", {}) or {})

    for fid, ctx in contexts.items():
        if fid in worker_results:
            continue

        # Block if any dependency failed — don't waste a worker run on doomed code.
        ps = state_store.load(ROOT)
        failed_deps = [
            dep
            for dep in ctx.get("depends_on", [])
            if ps.features.get(dep, FeatureRecord(feature_id=dep)).status
            == FeatureStatus.FAILED
        ]
        if failed_deps:
            error = f"Blocked: dependencies failed — {', '.join(failed_deps)}"
            print(c(RED, f"  ✗ {fid} blocked: {error}"))
            ps.features[fid].status = FeatureStatus.FAILED
            ps.features[fid].last_error = error
            ps.add_log("error", f"{fid} blocked by failed deps", error)
            state_store.save(ps, ROOT)
            return {
                **state,
                "worker_results": {
                    **worker_results,
                    fid: {
                        "feature_id": fid,
                        "success": False,
                        "milestone_report": "",
                        "error": error,
                    },
                },
            }

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
    git_results = dict(state.get("git_results", {}) or {})
    contexts = dict(state.get("feature_contexts", {}) or {})

    for fid, wr in worker_results.items():
        if fid in git_results:
            continue

        ctx = contexts.get(fid, {})
        branch = ctx.get("branch_name", f"feature/{fid.lower()}")
        title = ctx.get("title", fid)
        report = ROOT / "reports" / f"{fid}_milestone.md"

        if not wr.get("success"):
            # Worker failed — skip git, record failure
            git_results[fid] = {
                "success": False,
                "error": "worker_failed",
                "pr_url": "",
            }
            return {**state, "git_results": git_results}

        # The upfront branch-setup loop in feature_selection checks out each
        # selected feature's branch in turn, leaving the LAST one checked out.
        # Re-checkout this feature's branch before committing so we never
        # commit/push this feature's work onto another feature's branch.
        co = git_ops.checkout_branch(branch, ROOT)
        if not co.success:
            print(c(RED, f"  ✗ Could not checkout {branch}: {co.output[:120]}"))
            git_results[fid] = {"success": False, "error": co.output, "pr_url": ""}
            ps = state_store.load(ROOT)
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.FAILED
                ps.features[fid].last_error = f"git checkout failed: {co.stderr[:100]}"
                state_store.save(ps, ROOT)
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
            print(c(DIM, "  You can open it manually on GitHub."))

        git_results[fid] = {"success": True, "error": "", "pr_url": pr_url}

        ps = state_store.load(ROOT)
        if fid in ps.features:
            ps.features[fid].status = FeatureStatus.VALIDATING
            ps.add_log(
                "info", f"PR opened for {fid}: {pr_url} — running validator next"
            )
            state_store.save(ps, ROOT)

        # Validator runs next — human only reviews code that already passed the spec
        return {**state, "git_results": git_results}

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
    val_results = dict(state.get("validator_results", {}) or {})
    provider = state.get("validator_model", "gemini")

    for fid, wr in worker_results.items():
        if fid in val_results:
            continue
        if not wr.get("success"):
            val_results[fid] = ValidatorResult(
                feature_id=fid,
                overall="fail",
                blocking_passed=False,
                failures=["worker_failed"],
                escalations=[],
                results=[],
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
                ps.features[
                    fid
                ].status = FeatureStatus.IN_PROGRESS  # awaiting human gate
                ps.features[fid].validator_result = "pass"
                print(
                    c(GREEN, f"  ✓ {fid} passed validation — awaiting your PR review")
                )
                # Extract memory now — useful context even before merge
                mem = mem_store.load(ROOT)
                added = mem_store.append_from_milestone(
                    wr["milestone_report"], fid, mem
                )
                mem_store.save(mem, ROOT)
                total = sum(len(v) for v in added.values())
                if total:
                    print(c(DIM, f"    Memory: {total} new entries"))
            else:
                ps.features[fid].status = FeatureStatus.FAILED
                ps.features[fid].validator_result = "fail"
                print(c(RED, f"  ✗ {fid} failed validation — returning to worker"))
                if result["failures"]:
                    print(c(RED, f"    Failed: {result['failures']}"))
                if result["escalations"]:
                    print(c(RED, f"    Security escalations: {result['escalations']}"))
            ps.add_log(
                "info" if result["overall"] == "pass" else "warn",
                f"Validator {fid}: {result['overall']}",
            )
            state_store.save(ps, ROOT)

        new_val_results = {**val_results, fid: result}

        # If validation passed: set human gate for PR review
        if result["overall"] == "pass":
            ctx = dict(state.get("feature_contexts", {}) or {}).get(fid, {})
            pr_url = (
                dict(state.get("git_results", {}) or {}).get(fid, {}).get("pr_url", "")
            )
            return {
                **state,
                "validator_results": new_val_results,
                "gate_type": "pr_review",
                "gate_feature": fid,
                "gate_message": (
                    f"[{fid}] {ctx.get('title', '')} passed validation.\n"
                    f"PR: {pr_url or 'check GitHub'}\n\n"
                    "The code passed all spec tests. Now review the diff on GitHub.\n"
                    "Approve the PR there, then run:\n"
                    f"  python run.py gh-check {fid}\n"
                    "  python run.py resume --decision approve"
                ),
            }

        return {**state, "validator_results": new_val_results}

    return state


# ---------------------------------------------------------------------------
# Node: merge_node — pipeline-owned, no AI
# ---------------------------------------------------------------------------


def merge_node(state: GraphState) -> GraphState:
    """
    Merge the feature PR into develop after validation passes.
    Pipeline-owned — no AI involvement.
    """
    val_results = dict(state.get("validator_results", {}) or {})
    merge_results = dict(state.get("merge_results", {}) or {})

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
            try:
                _generate_codebase_index(ROOT)
                print(c(DIM, "  ✓ codebase_index.md updated"))
            except Exception as idx_err:
                print(c(YELLOW, f"  ⚠ codebase_index.md update failed: {idx_err}"))
            ps = state_store.load(ROOT)
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.PASSED
                ps.add_log("info", f"PR merged for {fid} — feature complete")
                state_store.save(ps, ROOT)
        else:
            print(c(YELLOW, f"  ⚠ Auto-merge failed: {r.output[:120]}"))
            print(c(DIM, "  Merge manually on GitHub or re-run after checks pass."))
            ps = state_store.load(ROOT)
            if fid in ps.features:
                ps.features[fid].status = FeatureStatus.FAILED
                ps.features[fid].last_error = f"merge failed: {r.stderr[:100]}"
                state_store.save(ps, ROOT)

        merge_results[fid] = {"success": r.success, "error": r.stderr[:200]}
        return {**state, "merge_results": merge_results}

    return state


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def route_from_cto(state: GraphState) -> str:
    phase = state.get("phase", "clarification")
    gate = state.get("gate_type")

    if gate:
        return "human_gate"
    if phase in (
        "clarification",
        "plan_review",
        "contract_gen",
        "contract_review",
        "feature_selection",
    ):
        return "cto_orchestrator"
    if phase == "implementation":
        return _route_impl(state)
    if phase == "complete":
        return END
    return "cto_orchestrator"


def _route_impl(state: GraphState) -> str:
    """
    Correct execution order per feature:
      worker → git → validator → human_gate → merge
    Validator runs before human review — you only review code that passed the spec.
    """
    contexts = state.get("feature_contexts", {}) or {}
    worker_results = state.get("worker_results", {}) or {}
    git_results = state.get("git_results", {}) or {}
    val_results = state.get("validator_results", {}) or {}
    merge_results = state.get("merge_results", {}) or {}

    # Need merge? (after human gate approved)
    for fid in val_results:
        if fid not in merge_results and val_results[fid].get("overall") == "pass":
            # Only merge if human gate has been cleared (no gate pending)
            if not state.get("gate_type"):
                return "merge"

    # Need human gate? (validator passed, gate set — will trigger interrupt)
    if state.get("gate_type") == "pr_review":
        return "human_gate"

    # Need validation? (after git pushed and PR opened)
    for fid in git_results:
        if fid not in val_results and git_results[fid].get("success"):
            return "validator"

    # Need git commit+PR? (after worker done)
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
    return "validator"  # validator always fires after git — no human gate here


def route_after_validator(state: GraphState) -> str:
    gate = state.get("gate_type")
    return (
        "human_gate" if gate else "cto_orchestrator"
    )  # gate set = pass, no gate = fail


def route_after_gate(state: GraphState) -> str:
    return "merge"  # human approved → merge immediately


def route_after_merge(state: GraphState) -> str:
    return "cto_orchestrator"


# ---------------------------------------------------------------------------
# Pruning checkpointer — keeps only the last N checkpoints per thread
# ---------------------------------------------------------------------------

class _PruningCheckpointer(SqliteSaver):
    """
    SqliteSaver wrapper that prunes old checkpoint rows after every write.

    LangGraph's default SqliteSaver keeps every state transition forever.
    A routing bug that loops 10,000 times produces a 5 GB database.
    This subclass deletes all but the `keep` most recent rows for the
    current thread_id after each put(), capping the DB at a small constant size.
    """

    def __init__(self, conn: _sqlite3.Connection, keep: int = 5):
        super().__init__(conn)
        self._keep = keep

    def put(self, config, checkpoint, metadata, new_versions):
        result = super().put(config, checkpoint, metadata, new_versions)
        try:
            thread_id = config["configurable"]["thread_id"]
            self.conn.execute(
                """
                DELETE FROM checkpoints
                WHERE thread_id = ?
                  AND thread_ts NOT IN (
                      SELECT thread_ts FROM checkpoints
                      WHERE thread_id = ?
                      ORDER BY thread_ts DESC
                      LIMIT ?
                  )
                """,
                (thread_id, thread_id, self._keep),
            )
            self.conn.commit()
        except Exception:
            pass  # pruning is best-effort; never break a write
        return result


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(db_path: str = "checkpoints.db") -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("cto_orchestrator", cto_orchestrator)
    builder.add_node("worker", worker_node)
    builder.add_node("git", git_node)
    builder.add_node("human_gate", human_gate)
    builder.add_node("validator", validator_node)
    builder.add_node("merge", merge_node)

    builder.set_entry_point("cto_orchestrator")

    builder.add_conditional_edges(
        "cto_orchestrator",
        route_from_cto,
        {
            "cto_orchestrator": "cto_orchestrator",
            "worker": "worker",
            "git": "git",
            "validator": "validator",
            "merge": "merge",
            "human_gate": "human_gate",
            END: END,
        },
    )
    builder.add_conditional_edges("worker", route_after_worker, {"git": "git"})
    builder.add_conditional_edges("git", route_after_git, {"validator": "validator"})
    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {"human_gate": "human_gate", "cto_orchestrator": "cto_orchestrator"},
    )
    builder.add_conditional_edges("human_gate", route_after_gate, {"merge": "merge"})
    builder.add_conditional_edges(
        "merge", route_after_merge, {"cto_orchestrator": "cto_orchestrator"}
    )

    conn = _sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = _PruningCheckpointer(conn, keep=5)
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_gate"],
    )


# ---------------------------------------------------------------------------
# Codebase index
# ---------------------------------------------------------------------------


def _generate_codebase_index(root: Path) -> None:
    """
    Write codebase_index.md after each feature merge.
    Workers read this at the start of their session to discover what's already built.
    """
    import re as _re
    from datetime import date

    _SKIP_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "venv",
        ".venv",
        "dist",
        "build",
        ".mypy_cache",
        ".tox",
        "reports",
    }
    _SRC_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb"}

    lines: list[str] = [
        "# Codebase Index\n\n",
        f"_Auto-generated after the last feature merge — {date.today()}_\n\n",
        "Workers: read this first to understand what is already built before writing new code.\n\n",
        "---\n\n",
        "## Directory Structure\n\n```\n",
    ]

    def _walk_tree(path: Path, prefix: str = "", depth: int = 0) -> None:
        if depth > 4:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return
        for entry in entries:
            if entry.name in _SKIP_DIRS or entry.name == "codebase_index.md":
                continue
            lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}\n")
            if entry.is_dir():
                _walk_tree(entry, prefix + "  ", depth + 1)

    _walk_tree(root)
    lines.append("```\n\n")

    lines.append("## Module Definitions\n\n")

    _PY_DEF = _re.compile(r"^(class|def|async def)\s+(\w+)", _re.MULTILINE)
    _JS_DEF = _re.compile(
        r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s+(\w+)|class\s+(\w+)|"
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(?)",
        _re.MULTILINE,
    )

    def _extract_defs(filepath: Path) -> list[str]:
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        ext = filepath.suffix
        defs: list[str] = []
        if ext == ".py":
            for m in _PY_DEF.finditer(text):
                defs.append(f"  {m.group(1)} {m.group(2)}")
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for m in _JS_DEF.finditer(text):
                name = m.group(1) or m.group(2) or m.group(3)
                if name:
                    defs.append(f"  {m.group(0).split('=')[0].strip()}")
        return defs[:25]

    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file() or filepath.suffix not in _SRC_EXTS:
            continue
        if any(skip in filepath.parts for skip in _SKIP_DIRS):
            continue
        rel = filepath.relative_to(root)
        defs = _extract_defs(filepath)
        if defs:
            lines.append(f"### `{rel}`\n")
            lines.append("\n".join(defs))
            lines.append("\n\n")

    (root / "codebase_index.md").write_text("".join(lines))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_features_from_doc2(root: Path):
    from agents.cto import _parse_feature_blocks

    doc2 = root / "contracts" / "doc2_features_contract.md"
    if not doc2.exists():
        return []
    return _parse_feature_blocks(doc2.read_text())
