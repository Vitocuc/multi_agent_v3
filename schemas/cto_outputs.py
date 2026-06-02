"""
schemas/cto_outputs.py

Typed outputs for every CTO model call.
Code validates these — not prompts.
"""
from __future__ import annotations
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class ClarificationQuestion(BaseModel):
    question:      str
    why_important: str
    sufficient:    bool = False

    @field_validator("question")
    @classmethod
    def single_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        if v.count("?") > 1:
            raise ValueError(
                f"Must contain exactly one question — found {v.count('?')} "
                "question marks. Ask one thing at a time."
            )
        return v


class SharedPlan(BaseModel):
    summary:          str
    key_decisions:    List[Dict[str, str]]
    open_assumptions: List[str]
    tech_stack:       Dict[str, str]
    scope_boundary:   str
    first_milestone:  str

    @field_validator("tech_stack")
    @classmethod
    def no_blanks(cls, v: Dict[str, str]) -> Dict[str, str]:
        blanks = [k for k, val in v.items() if not val.strip()]
        if blanks:
            raise ValueError(f"tech_stack has blank entries: {blanks}")
        return v


class FeatureBlock(BaseModel):
    feature_id:          str
    title:               str
    milestone_id:        str
    priority:            str
    complexity:          str
    depends_on:          List[str]
    parallel_safe:       bool
    description:         str
    security_constraints: List[str]
    acceptance_criteria: List[str]
    branch_name:         str

    @field_validator("acceptance_criteria")
    @classmethod
    def given_when_then(cls, v: List[str]) -> List[str]:
        for c in v:
            if not any(kw in c.lower() for kw in ("given", "when", "then")):
                raise ValueError(
                    f"Acceptance criterion must use Given/When/Then: '{c[:60]}'"
                )
        return v


class SpawnPlan(BaseModel):
    """
    Output of cto.build_spawn_plan().
    The CTO decides which features to run in this batch and in what order.
    """
    batch:       List[str]           # feature_ids to spawn now (parallel-safe ones)
    sequential:  List[List[str]]     # groups that must run in order after batch
    reasoning:   str                 # CTO's explanation of the execution plan


class ContractConsistencyCheck(BaseModel):
    all_features_have_suites:  bool
    all_security_refs_exist:   bool
    all_criteria_testable:     bool
    milestone_order_logical:   bool
    issues:                    List[str]
    approved:                  bool

    @field_validator("approved")
    @classmethod
    def approved_only_if_clean(cls, v: bool, info) -> bool:
        if v and info.data.get("issues"):
            raise ValueError("approved cannot be True when issues list is non-empty")
        return v
