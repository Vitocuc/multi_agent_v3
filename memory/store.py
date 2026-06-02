"""
memory/store.py — append-only project memory.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

MEMORY_FILE = "memory.json"

EMPTY: Dict[str, Any] = {
    "_meta": {"schema_version": "1.0"},
    "architecture_decisions": [],
    "failed_approaches":      [],
    "discovered_constraints": [],
    "open_risks":             [],
}


def load(root: Path) -> Dict[str, Any]:
    p = root / MEMORY_FILE
    if not p.exists():
        return dict(EMPTY)
    return json.loads(p.read_text())


def save(mem: Dict[str, Any], root: Path) -> None:
    p   = root / MEMORY_FILE
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(mem, indent=2, ensure_ascii=False))
    tmp.replace(p)


def filter_for_feature(
    feature_id:    str,
    depends_chain: List[str],
    mem:           Dict[str, Any],
) -> Dict[str, Any]:
    def real(e: Dict) -> bool:
        return "_comment" not in e

    return {
        "architecture_decisions": [
            e for e in mem.get("architecture_decisions", [])
            if real(e) and e.get("feature_id") in depends_chain
        ],
        "failed_approaches": [
            e for e in mem.get("failed_approaches", []) if real(e)
        ],
        "discovered_constraints": [
            e for e in mem.get("discovered_constraints", [])
            if real(e) and (
                feature_id in e.get("affects_features", [])
                or not e.get("affects_features")
            )
        ],
        "open_risks": [
            e for e in mem.get("open_risks", [])
            if real(e) and (
                e.get("severity") in ("high", "critical")
                or feature_id in e.get("blocking_features", [])
            )
        ],
    }


def append_from_milestone(
    report_text: str, feature_id: str, mem: Dict[str, Any]
) -> Dict[str, List[str]]:
    now   = datetime.now(timezone.utc).isoformat()
    added: Dict[str, List[str]] = {
        "architecture_decisions": [], "failed_approaches": [],
        "discovered_constraints": [], "open_risks": [],
    }
    issues_m = re.search(r"## Issues discovered\s*```yaml\n(.*?)```", report_text, re.DOTALL)
    if not issues_m:
        return added
    for block in re.split(r"(?=^\s*- issue_id:)", issues_m.group(1), flags=re.MULTILINE):
        block = block.strip()
        if not block or "issue_id" not in block:
            continue
        issue = _simple_yaml(block.replace("- issue_id:", "issue_id:"))
        if not issue.get("issue_id"):
            continue
        iid        = issue["issue_id"]
        severity   = issue.get("severity", "low")
        resolution = issue.get("resolution", "")
        desc       = issue.get("description", "")
        notes      = issue.get("resolution_notes", "")
        no_retry   = str(issue.get("do_not_retry", "false")).lower() == "true"

        if resolution in ("unresolved", "workaround") or no_retry:
            eid = f"FA-{iid}"
            mem["failed_approaches"].append({
                "entry_id": eid, "feature_id": feature_id, "timestamp": now,
                "what_was_tried": desc, "why_it_failed": notes,
                "do_not_retry": no_retry, "alternative_used": notes if resolution == "workaround" else "",
            })
            added["failed_approaches"].append(eid)

        if severity in ("high", "critical") and resolution == "unresolved":
            rid = f"OR-{iid}"
            mem["open_risks"].append({
                "risk_id": rid, "feature_id": feature_id, "timestamp": now,
                "severity": severity, "description": desc,
                "mitigation_status": "open", "security_deviation": False,
                "blocking_features": [], "resolution_notes": notes,
            })
            added["open_risks"].append(rid)

        if issue.get("source") in ("env", "api", "infra", "library"):
            cid = f"DC-{iid}"
            mem["discovered_constraints"].append({
                "constraint_id": cid, "feature_id": feature_id, "timestamp": now,
                "source": issue.get("source"), "description": desc,
                "affects_features": [], "contract_update_needed": severity in ("high", "critical"),
                "workaround": notes,
            })
            added["discovered_constraints"].append(cid)

    sec_m = re.search(r"security_checklist_followed:\s*(true|false)", report_text)
    if sec_m and sec_m.group(1) == "false":
        n_m   = re.search(r"security_checklist_notes:\s*\"?(.*?)\"?\n", report_text)
        notes = n_m.group(1).strip() if n_m else "no notes"
        rid   = f"OR-SEC-{feature_id}"
        mem["open_risks"].append({
            "risk_id": rid, "feature_id": feature_id, "timestamp": now,
            "severity": "high", "description": f"Security checklist not followed: {notes}",
            "mitigation_status": "open", "security_deviation": True,
            "blocking_features": [], "resolution_notes": notes,
        })
        added["open_risks"].append(rid)
    return added


def _simple_yaml(text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip(); v = v.split("#")[0].strip().strip('"').strip("'")
        if v.lower() == "true":   out[k] = True
        elif v.lower() == "false": out[k] = False
        elif v == "":              out[k] = None
        else:                      out[k] = v
    return out
