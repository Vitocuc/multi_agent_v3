"""
schemas/cto_outputs.py

Typed outputs for every CTO model call.
Code validates these — not prompts.
"""

from __future__ import annotations
import re
from typing import List, Dict
from pydantic import BaseModel, field_validator


class ServiceSpec(BaseModel):
    """
    An auxiliary service the application needs at runtime — a database,
    cache, queue, etc. The validator starts these on the shared Docker
    network before starting the app, so the app can reach them by `name`.
    """

    name: str  # hostname on the shared network — e.g. "db", "redis"
    image: str  # docker image — e.g. "postgres:16-alpine", "redis:7-alpine"
    port: int  # port the service listens on, for the readiness check
    env: Dict[str, str] = {}  # env vars for the SERVICE container itself
    # (e.g. POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)

    @field_validator("name")
    @classmethod
    def valid_hostname(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError(
                f"service name '{v}' must be lowercase letters/digits/hyphens, "
                "starting with a letter — it's used as a Docker container "
                "name and DNS hostname on the shared network"
            )
        return v

    @field_validator("port")
    @classmethod
    def valid_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"service port must be between 1 and 65535, got {v}")
        return v


class ClarificationQuestion(BaseModel):
    question: str
    why_important: str
    sufficient: bool = False

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
    summary: str
    key_decisions: List[Dict[str, str]]
    open_assumptions: List[str]
    tech_stack: Dict[str, str]
    scope_boundary: str
    first_milestone: str
    app_type: str  # "api" | "frontend" | "fullstack"
    app_run_command: str
    app_port: int
    app_env: Dict[str, str] = {}
    services: List[ServiceSpec] = []

    @field_validator("app_type")
    @classmethod
    def valid_app_type(cls, v: str) -> str:
        v = v.strip().lower()
        allowed = {"api", "frontend", "fullstack"}
        if v not in allowed:
            raise ValueError(
                f"app_type must be one of {allowed}, got '{v}'. "
                "Use 'api' for a pure backend/REST/GraphQL service, "
                "'frontend' for a client-side-only app (SPA, static site), "
                "or 'fullstack' for an app that serves both UI and API "
                "(Next.js, Nuxt, Django+templates, Rails, etc.)"
            )
        return v

    @field_validator("tech_stack")
    @classmethod
    def no_blanks(cls, v: Dict[str, str]) -> Dict[str, str]:
        blanks = [k for k, val in v.items() if not val.strip()]
        if blanks:
            raise ValueError(f"tech_stack has blank entries: {blanks}")
        return v

    @field_validator("app_run_command")
    @classmethod
    def app_run_command_set(cls, v: str) -> str:
        if not v.strip():
            raise ValueError(
                "app_run_command must specify how to start the application "
                "(e.g. 'npm run dev', 'uvicorn main:app --host 0.0.0.0 --port 8000') "
                "— the validator runs this in Docker to test the implementation."
            )
        return v

    @field_validator("app_port")
    @classmethod
    def app_port_valid(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"app_port must be between 1 and 65535, got {v}")
        return v


class FeatureBlock(BaseModel):
    feature_id: str
    title: str
    milestone_id: str
    priority: str
    complexity: str
    depends_on: List[str]
    parallel_safe: bool
    description: str
    security_constraints: List[str]
    acceptance_criteria: List[str]
    branch_name: str

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

    batch: List[str]  # feature_ids to spawn now (parallel-safe ones)
    sequential: List[List[str]]  # groups that must run in order after batch
    reasoning: str  # CTO's explanation of the execution plan


class ContractConsistencyCheck(BaseModel):
    all_features_have_suites: bool
    all_security_refs_exist: bool
    all_criteria_testable: bool
    milestone_order_logical: bool
    issues: List[str]
    approved: bool

    @field_validator("approved")
    @classmethod
    def approved_only_if_clean(cls, v: bool, info) -> bool:
        if v and info.data.get("issues"):
            raise ValueError("approved cannot be True when issues list is non-empty")
        return v
