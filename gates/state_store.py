"""gates/state_store.py — atomic load/save of project_state.json."""
from __future__ import annotations
import json
from pathlib import Path
from schemas.pipeline_state import ProjectState

FILE = "project_state.json"


def load(root: Path) -> ProjectState:
    p = root / FILE
    if not p.exists():
        return ProjectState()
    try:
        return ProjectState.model_validate(json.loads(p.read_text()))
    except Exception as e:
        raise RuntimeError(f"Cannot load {p}: {e}")


def save(state: ProjectState, root: Path) -> None:
    p   = root / FILE
    tmp = p.with_suffix(".tmp")
    tmp.write_text(state.model_dump_json(indent=2))
    tmp.replace(p)
