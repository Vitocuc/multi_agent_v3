#!/usr/bin/env python3
"""
run.py — development assistant.

Commands:
  docker-build                  Build the Docker test image (run once before start)
  start                         Begin a new project
  resume [--decision approve|reject] [--note "..."]
                                Continue after a human gate
  gh-check <feature_id>         Poll GitHub PR — detect approval/merge, flip human_gate
  status                        Show project state and feature board
  memory [feature_id]           Show project memory

Usage:
  python run.py docker-build
  python run.py start
  python run.py resume --decision approve
  python run.py resume --decision reject --note "fix the auth section"
  python run.py gh-check F-01-001
  python run.py status
  python run.py memory
  python run.py memory F-01-002
"""
import sys
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Load env before anything else
def _load_env():
    env = ROOT / ".env"
    if not env.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env, override=False)
    except ImportError:
        import os
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip(); v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

_load_env()

from schemas.pipeline_state import ProjectState, Phase, FeatureStatus
from gates import state_store
from memory import store as mem_store

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
DIM    = "\033[2m"

def c(col: str, txt: str) -> str:
    return f"{col}{txt}{RESET}"

THREAD_ID = "main"


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

def cmd_start():
    doc0 = ROOT / "doc0_project_brief.md"
    if not doc0.exists():
        print(c(RED, "\n✗ doc0_project_brief.md not found."))
        print(c(DIM, "  Fill it in first, then run: python run.py start\n"))
        sys.exit(1)

    state_path = ROOT / "project_state.json"
    if state_path.exists():
        print(c(YELLOW, "\n⚠ project_state.json already exists."))
        print(c(DIM, "  Delete it to restart, or run: python run.py resume\n"))
        sys.exit(1)

    text     = doc0.read_text()
    name_m   = re.search(r"\|\s*project_name\s*\|\s*(.+?)\s*\|", text)
    id_m     = re.search(r"\|\s*project_id\s*\|\s*(.+?)\s*\|", text)
    proj_id  = _clean(id_m.group(1)   if id_m   else "proj-001")
    proj_name = _clean(name_m.group(1) if name_m else "Unnamed project")

    import os
    ps = ProjectState(
        project_id=proj_id,
        project_name=proj_name,
        cto_model=os.environ.get("CTO_MODEL", "claude"),
        validator_model=os.environ.get("VALIDATOR_MODEL", "gemini"),
    )
    ps.add_log("info", "Project started")
    state_store.save(ps, ROOT)

    print(c(BOLD, f"\n── Starting: {proj_name} ──\n"))

    initial_state = {
        "project_id":            proj_id,
        "project_name":          proj_name,
        "phase":                 "clarification",
        "clarification_history": [],
        "clarification_round":   0,
        "plan_approved":         False,
        "contracts_approved":    False,
        "selected_features":     [],
        "feature_contexts":      {},
        "worker_results":        {},
        "validator_results":     {},
        "gate_type":             None,
        "gate_message":          None,
        "gate_feature":          None,
        "gate_note":             None,
        "last_error":            "",
        "consecutive_errors":    0,
        "cto_model":             ps.cto_model,
        "validator_model":       ps.validator_model,
    }

    from graph import build_graph
    g = build_graph(str(ROOT / "checkpoints.db"))
    cfg = {"configurable": {"thread_id": THREAD_ID}}

    try:
        for event in g.stream(initial_state, config=cfg):
            pass
    except KeyboardInterrupt:
        print(c(YELLOW, "\n\nInterrupted. Run 'python run.py resume' to continue."))
    _maybe_print_gate(g, cfg)


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------

def cmd_resume(decision: str = "", note: str = ""):
    from graph import build_graph
    g   = build_graph(str(ROOT / "checkpoints.db"))
    cfg = {"configurable": {"thread_id": THREAD_ID}}

    # Read current graph state
    snap = g.get_state(cfg)
    if snap is None or not snap.values:
        print(c(YELLOW, "\n  No checkpoint found. Run 'python run.py start' first.\n"))
        sys.exit(1)

    current = snap.values
    gate    = current.get("gate_type")

    if not gate and not decision:
        # No gate pending — just continue
        print(c(DIM, "  No gate pending — continuing pipeline...\n"))
        _stream(g, None, cfg)
        return

    if gate and not decision:
        _print_gate(current)
        return

    # Apply decision
    approved = decision.strip().lower() in ("approve", "approved", "yes", "y", "lgtm", "ok")

    ps = state_store.load(ROOT)

    if gate == "plan_approval":
        if approved:
            doc0 = ROOT / "doc0_project_brief.md"
            text = doc0.read_text()
            doc0.write_text(text.replace("shared_plan_approved: false", "shared_plan_approved: true"))
            ps.plan_approved = True
            new_phase = "contract_gen"
            print(c(GREEN, "\n  ✓ Plan approved → generating contracts\n"))
        else:
            new_phase = "clarification"
            print(c(YELLOW, f"\n  Plan rejected. Note: {note}"))

    elif gate == "contract_approval":
        if approved:
            ps.contracts_approved = True
            new_phase = "feature_selection"
            print(c(GREEN, "\n  ✓ Contracts approved → feature selection\n"))
        else:
            new_phase = "contract_gen"
            print(c(YELLOW, f"\n  Contracts rejected. Note: {note}"))

    elif gate == "security_escalation":
        new_phase = current.get("phase", "implementation")
        print(c(YELLOW, "\n  Security escalation acknowledged.\n"))

    else:
        new_phase = current.get("phase", "clarification")

    ps.add_log("info" if approved else "warn",
               f"Gate {gate} resolved: {decision}", note)
    state_store.save(ps, ROOT)

    updated = {**current, "phase": new_phase, "gate_type": None,
               "gate_message": None, "gate_note": note}
    _stream(g, updated, cfg)


def _stream(g, update, cfg):
    try:
        if update:
            g.update_state(cfg, update)
        for _ in g.stream(None, config=cfg):
            pass
    except KeyboardInterrupt:
        print(c(YELLOW, "\n\nInterrupted. Run 'python run.py resume' to continue."))
    _maybe_print_gate(g, cfg)


def _maybe_print_gate(g, cfg):
    try:
        snap = g.get_state(cfg)
        if snap and snap.values and snap.values.get("gate_type"):
            _print_gate(snap.values)
    except Exception:
        pass


def _print_gate(state: dict):
    gate = state.get("gate_type", "")
    msg  = state.get("gate_message", "")
    colours = {
        "plan_approval":      CYAN,
        "contract_approval":  CYAN,
        "security_escalation": RED,
    }
    col = colours.get(gate, YELLOW)
    print()
    print(c(BOLD, f"── Gate: {gate} " + "─" * max(0, 40 - len(gate))))
    print()
    print(c(col, msg))
    print()
    print(c(DIM,  "  To continue:"))
    print(c(CYAN, "  python run.py resume --decision approve"))
    print(c(DIM,  "  python run.py resume --decision reject --note 'your note'"))
    print()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status():
    ps = state_store.load(ROOT)

    print(c(BOLD, f"\n── {ps.project_name} ──────────────────────────\n"))
    print(c(DIM,  f"  Phase:   {ps.phase.value}"))
    print(c(DIM,  f"  Updated: {ps.updated_at[:16]}"))

    ready = ps.ready_features()
    if ready:
        print(c(GREEN, f"  Ready:   {', '.join(ready)}"))
    print()

    icons = {
        "pending":     c(DIM,    "○"),
        "selected":    c(CYAN,   "◎"),
        "in_progress": c(YELLOW, "●"),
        "validating":  c(CYAN,   "⟳"),
        "passed":      c(GREEN,  "✓"),
        "failed":      c(RED,    "✗"),
        "skipped":     c(DIM,    "–"),
    }

    milestones: dict = {}
    for fid, fr in ps.features.items():
        m = fr.milestone_id or "?"
        milestones.setdefault(m, []).append(fid)

    for mid in sorted(milestones):
        print(c(BOLD, f"  {mid}"))
        for fid in sorted(milestones[mid]):
            fr   = ps.features[fid]
            icon = icons.get(fr.status.value, "?")
            deps = c(DIM, f" → {', '.join(fr.depends_on)}") if fr.depends_on else ""
            err  = c(RED, f" {fr.last_error[:50]}") if fr.last_error and fr.status.value == "failed" else ""
            print(f"    {icon}  {fid} — {fr.title}{deps}{err}")
        print()

    # Counts
    counts: dict = {}
    for fr in ps.features.values():
        counts[fr.status.value] = counts.get(fr.status.value, 0) + 1
    print(c(DIM, "  " + " · ".join(f"{v} {k}" for k, v in counts.items() if v) + "\n"))

    if ps.log:
        print(c(DIM, "  Recent:"))
        for e in ps.log[-5:]:
            ts  = e.ts[11:16]
            col = {"info": DIM, "warn": YELLOW, "error": RED}.get(e.level, DIM)
            print(c(DIM, f"    {ts}") + c(col, f"  {e.message}"))
        print()


# ---------------------------------------------------------------------------
# memory
# ---------------------------------------------------------------------------

def cmd_memory(feature_id: str = ""):
    ps  = state_store.load(ROOT)
    mem = mem_store.load(ROOT)

    if feature_id:
        fid = feature_id.upper()
        from agents.cto import _build_chain
        chain    = list(_build_chain(fid, {fid: {"depends_on": ps.features.get(fid, type('', (), {"depends_on": []})()).depends_on if fid in ps.features else []}}))
        filtered = mem_store.filter_for_feature(fid, chain, mem)
        total    = sum(len(v) for v in filtered.values())
        print(c(BOLD, f"\n── Memory for {fid} ({total} entries) ──\n"))
        print(json.dumps(filtered, indent=2))
    else:
        sections = ["architecture_decisions", "failed_approaches",
                    "discovered_constraints", "open_risks"]
        total = sum(len([e for e in mem.get(s, []) if "_comment" not in e]) for s in sections)
        print(c(BOLD, f"\n── Project memory ({total} entries) ──\n"))
        print(json.dumps({
            s: [e for e in mem.get(s, []) if "_comment" not in e]
            for s in sections
        }, indent=2))
    print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(val: str) -> str:
    return val.replace("<!--", "").replace("-->", "").strip()


# ---------------------------------------------------------------------------
# docker-build
# ---------------------------------------------------------------------------

def cmd_docker_build():
    """Build the Docker test image from Dockerfile.test."""
    import os
    from docker.runner import build_image, DEFAULT_IMAGE
    image = os.environ.get("TEST_IMAGE", DEFAULT_IMAGE)
    print(c(BOLD, f"\n── Building test image: {image} ──\n"))
    result = build_image(ROOT, image)
    if result.exit_code == 0:
        print(c(GREEN, f"\n  ✓ Image built: {image}"))
        print(c(DIM,   "  Run 'python run.py start' to begin.\n"))
    else:
        print(c(RED, f"\n  ✗ Build failed (exit {result.exit_code})"))
        print(c(DIM,  "  Check the output above for errors.\n"))
        sys.exit(1)



# ---------------------------------------------------------------------------
# gh-check — poll GitHub PR status and flip human_gate in milestone report
# ---------------------------------------------------------------------------

def cmd_gh_check(feature_id: str) -> None:
    """
    Check whether the GitHub PR for a feature has been approved or merged.
    If approved/merged: writes human_gate: approved into the milestone report
    and advances the feature to the next pipeline step.
    If changes requested: writes human_gate: rejected.

    Requires: gh CLI installed and authenticated, GITHUB_TOKEN in .env.
    """
    import subprocess
    fid = feature_id.upper()

    # Find the PR for this feature
    print(c(BOLD, f"\n── Checking GitHub PR for {fid} ──\n"))

    pr_result = subprocess.run(
        ["gh", "pr", "list",
         "--search", f"[{fid}]",
         "--json", "number,title,state,reviewDecision,mergedAt,headRefName"],
        capture_output=True, text=True,
    )
    if pr_result.returncode != 0:
        print(c(RED, f"  ✗ gh CLI error: {pr_result.stderr.strip()}"))
        print(c(DIM,  "  Make sure gh is installed and GITHUB_TOKEN is set in .env"))
        sys.exit(1)

    try:
        prs = json.loads(pr_result.stdout)
    except json.JSONDecodeError:
        print(c(RED, "  ✗ Could not parse gh output"))
        sys.exit(1)

    if not prs:
        print(c(YELLOW, f"  No PR found with [{fid}] in the title."))
        print(c(DIM,    "  The worker may not have opened it yet, or the title format is wrong."))
        sys.exit(1)

    pr = prs[0]
    number         = pr["number"]
    state          = pr["state"]           # OPEN | MERGED | CLOSED
    review_decision = pr.get("reviewDecision", "")  # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED
    merged_at      = pr.get("mergedAt")

    print(c(DIM, f"  PR #{number}: {pr['title']}"))
    print(c(DIM, f"  State: {state}  |  Review: {review_decision or 'pending'}"))
    print()

    # Determine outcome
    if merged_at or state == "MERGED":
        outcome = "approved"
        print(c(GREEN, "  ✓ PR is merged — marking human_gate: approved"))
    elif review_decision == "APPROVED":
        outcome = "approved"
        print(c(GREEN, "  ✓ PR is approved — marking human_gate: approved"))
    elif review_decision == "CHANGES_REQUESTED":
        outcome = "rejected"
        print(c(RED, "  ✗ PR has changes requested — marking human_gate: rejected"))
    else:
        print(c(YELLOW, "  PR is still pending review. No gate update yet."))
        print(c(DIM,    f"  Check: https://github.com — PR #{number}"))
        return

    # Write human_gate into milestone report
    report_path = ROOT / "reports" / f"{fid}_milestone.md"
    if not report_path.exists():
        print(c(YELLOW, f"  Milestone report not found: {report_path}"))
        print(c(DIM,    "  Cannot update human_gate without the report."))
        sys.exit(1)

    text = report_path.read_text()
    if "human_gate:" not in text:
        print(c(YELLOW, "  human_gate field not found in milestone report."))
        print(c(DIM,    "  Run the validator first: python run.py resume"))
        sys.exit(1)

    import re
    updated = re.sub(
        r"(human_gate:\s*)\S+",
        lambda m: m.group(1) + outcome,
        text,
    )
    report_path.write_text(updated)
    print(c(GREEN if outcome == "approved" else RED,
            f"  human_gate set to: {outcome}"))

    # Update pipeline state
    ps = state_store.load(ROOT)
    if fid in ps.features:
        if outcome == "approved":
            from schemas.pipeline_state import FeatureStatus
            ps.features[fid].status = FeatureStatus.VALIDATING
            ps.add_log("info", f"PR approved for {fid} — moving to validation")
        else:
            from schemas.pipeline_state import FeatureStatus
            ps.features[fid].status = FeatureStatus.FAILED
            ps.features[fid].last_error = "PR review: changes requested"
            ps.add_log("warn", f"PR changes requested for {fid}")
        state_store.save(ps, ROOT)

    print()
    if outcome == "approved":
        print(c(DIM, "  Run `python run.py resume` to trigger validation."))
    else:
        print(c(DIM, "  Address the review comments, push to the same branch, then re-check."))
    print()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args     = sys.argv[1:]
    decision = ""
    note     = ""

    filtered = []
    i = 0
    while i < len(args):
        if args[i] == "--decision" and i + 1 < len(args):
            decision = args[i + 1]; i += 2
        elif args[i] == "--note" and i + 1 < len(args):
            note = args[i + 1]; i += 2
        else:
            filtered.append(args[i]); i += 1
    args = filtered

    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == "start":
        cmd_start()
    elif cmd == "resume":
        cmd_resume(decision=decision, note=note)
    elif cmd == "status":
        cmd_status()
    elif cmd == "memory":
        cmd_memory(args[1] if len(args) > 1 else "")
    elif cmd == "docker-build":
        cmd_docker_build()
    elif cmd == "gh-check":
        if len(args) < 2:
            print(c(RED, "\n✗ gh-check requires a feature_id: python run.py gh-check F-01-001\n"))
            sys.exit(1)
        cmd_gh_check(args[1])
    else:
        print(c(RED, f"\n✗ Unknown command: {cmd}"))
        print(c(DIM, "  Valid: start, resume, status, memory\n"))
        sys.exit(1)


if __name__ == "__main__":
    main()
