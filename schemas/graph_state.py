"""
schemas/graph_state.py

LangGraph graph state — the TypedDict that flows between every node.
This is ephemeral per graph run.
Persistent execution state lives in project_state.json (schemas/pipeline_state.py).
"""
from __future__ import annotations
from typing import TypedDict, Optional, List, Dict, Any


class FeatureContext(TypedDict):
    feature_id:   str
    title:        str
    milestone_id: str
    depends_on:   List[str]
    priority:     str
    block_text:   str          # raw feature block from doc2
    memory:       Dict         # filtered memory.json for this feature
    branch_name:  str


class WorkerResult(TypedDict):
    feature_id:        str
    success:           bool
    milestone_report:  str     # raw text of the filed doc4
    error:             str


class ValidatorResult(TypedDict):
    feature_id:      str
    overall:         str       # pass | fail
    blocking_passed: bool
    failures:        List[str]
    escalations:     List[str]
    results:         List[Dict]


class GraphState(TypedDict):
    # Project identity
    project_id:   str
    project_name: str

    # Phase tracking
    phase:        str          # clarification | plan_review | contract_gen |
                               # contract_review | feature_selection |
                               # implementation | complete | failed

    # CTO clarification
    clarification_history: List[Dict]   # [{role, content}]
    clarification_round:   int
    plan_approved:         bool
    contracts_approved:    bool

    # Feature execution
    selected_features:  List[str]              # user-selected feature_ids
    feature_contexts:   Dict[str, FeatureContext]
    worker_results:     Dict[str, WorkerResult]
    validator_results:  Dict[str, ValidatorResult]

    # Gate management
    gate_type:    Optional[str]   # set by human_gate node → interrupts graph
    gate_message: Optional[str]
    gate_feature: Optional[str]
    gate_note:    Optional[str]   # set by human on resume

    # Error tracking
    last_error:         str
    consecutive_errors: int

    # CTO model choice
    cto_model:       str   # claude | gemini
    validator_model: str   # gemini | claude
