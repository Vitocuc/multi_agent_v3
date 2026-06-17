"""
feature_menu.py

Presents the full feature list and captures user selection.
Called by the CTO orchestrator node before spawning workers.
"""

from __future__ import annotations
from typing import List, Dict

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
DIM = "\033[2m"
CYAN = "\033[36m"


def c(colour: str, text: str) -> str:
    return f"{colour}{text}{RESET}"


def present_and_select(features: List[Dict], passed_ids: List[str]) -> List[str]:
    """
    Print the feature list grouped by milestone.
    Let the user select which features to run.
    Returns list of selected feature_ids.
    """
    # Group by milestone
    milestones: Dict[str, List[Dict]] = {}
    for f in features:
        m = f.get("milestone_id", "M-??")
        milestones.setdefault(m, []).append(f)

    print(c(BOLD, "\n── Feature selection ──────────────────────────\n"))
    print(c(DIM, "  All features from the contracts. Select what to implement.\n"))

    all_ids = []
    for mid in sorted(milestones):
        print(c(BOLD, f"  {mid}"))
        for f in milestones[mid]:
            fid = f["feature_id"]
            title = f.get("title", "")
            priority = f.get("priority", "medium")
            deps = f.get("depends_on", [])
            prio_c = {
                "critical": "\033[31m",
                "high": YELLOW,
                "medium": DIM,
                "low": DIM,
            }.get(priority, DIM)
            dep_str = c(DIM, f"  → needs {', '.join(deps)}") if deps else ""
            done_str = c(GREEN, " ✓") if fid in passed_ids else ""
            print(f"    [{fid}] {title}{done_str}  {c(prio_c, priority)}{dep_str}")
            all_ids.append(fid)
        print()

    print(c(DIM, "  Commands:"))
    print(c(DIM, "    all         — run all features"))
    print(c(DIM, "    M-01        — run all features in a milestone"))
    print(c(DIM, "    F-01-001    — run a specific feature"))
    print(c(DIM, "    F-01-001,F-01-002  — comma-separated list"))
    print(c(DIM, "    skip F-01-003 all  — all except specified"))
    print()
    print(c(CYAN, "  Your selection: "), end="", flush=True)

    try:
        raw = input().strip()
    except (EOFError, KeyboardInterrupt):
        print(c(YELLOW, "\n\nInterrupted."))
        return []

    return _parse_selection(raw, features, passed_ids)


def _parse_selection(
    raw: str,
    features: List[Dict],
    passed_ids: List[str],
) -> List[str]:
    raw = raw.strip()
    all_ids = [f["feature_id"] for f in features]
    pending_ids = [fid for fid in all_ids if fid not in passed_ids]

    if not raw or raw.lower() == "all":
        return pending_ids

    # Milestone selection: M-01
    if raw.upper().startswith("M-"):
        parts = [p.strip().upper() for p in raw.split(",")]
        result = []
        for f in features:
            if (
                f.get("milestone_id", "").upper() in parts
                and f["feature_id"] not in passed_ids
            ):
                result.append(f["feature_id"])
        return result

    # Skip syntax: "skip F-01-003 all" or "all skip F-01-003"
    lower = raw.lower()
    if "skip" in lower:
        tokens = raw.replace(",", " ").split()
        skip_ids = set()
        for t in tokens:
            t = t.upper()
            if t.startswith("F-") and "-" in t[2:]:
                skip_ids.add(t)
        return [fid for fid in pending_ids if fid not in skip_ids]

    # Comma-separated feature IDs
    parts = [p.strip().upper() for p in raw.replace(" ", ",").split(",") if p.strip()]
    valid = [p for p in parts if p in all_ids]
    if not valid:
        print(c(YELLOW, "  No valid feature IDs found. Running all pending features."))
        return pending_ids
    return [fid for fid in valid if fid not in passed_ids]
