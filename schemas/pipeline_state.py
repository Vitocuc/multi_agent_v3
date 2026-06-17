"""
schemas/pipeline_state.py

Persistent execution state — written to project_state.json after every transition.
Survives process restarts, graph interrupts, and crashes.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class Phase(str, Enum):
    CLARIFICATION = "clarification"
    PLAN_REVIEW = "plan_review"
    CONTRACT_GEN = "contract_gen"
    CONTRACT_REVIEW = "contract_review"
    FEATURE_SELECTION = "feature_selection"
    IMPLEMENTATION = "implementation"
    COMPLETE = "complete"
    FAILED = "failed"


class FeatureStatus(str, Enum):
    PENDING = "pending"
    SELECTED = "selected"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FeatureRecord(BaseModel):
    feature_id: str
    title: str = ""
    milestone_id: str = ""
    status: FeatureStatus = FeatureStatus.PENDING
    depends_on: List[str] = Field(default_factory=list)
    retry_count: int = 0
    last_error: str = ""
    validator_result: str = ""


class LogEntry(BaseModel):
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = "info"
    message: str
    detail: str = ""


class ProjectState(BaseModel):
    project_id: str = ""
    project_name: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    phase: Phase = Phase.CLARIFICATION
    clarification_round: int = 0
    plan_approved: bool = False
    contracts_approved: bool = False

    features: Dict[str, FeatureRecord] = Field(default_factory=dict)

    cto_model: str = "claude"
    validator_model: str = "gemini"

    last_error: str = ""
    consecutive_errors: int = 0
    log: List[LogEntry] = Field(default_factory=list)

    def add_log(self, level: str, message: str, detail: str = "") -> None:
        self.log.append(LogEntry(level=level, message=message, detail=detail))
        if len(self.log) > 200:
            self.log = self.log[-200:]
        self.updated_at = datetime.utcnow().isoformat()

    def ready_features(self) -> List[str]:
        passed = {
            fid
            for fid, fr in self.features.items()
            if fr.status == FeatureStatus.PASSED
        }
        return [
            fid
            for fid, fr in self.features.items()
            if fr.status == FeatureStatus.PENDING
            and all(dep in passed for dep in fr.depends_on)
        ]

    def is_complete(self) -> bool:
        return bool(self.features) and all(
            fr.status in (FeatureStatus.PASSED, FeatureStatus.SKIPPED)
            for fr in self.features.values()
        )
