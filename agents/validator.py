"""
agents/validator.py

Validator node — reads doc3 test suite + milestone report, calls Gemini,
returns a typed ValidatorResult. Never reads source code.
"""
from __future__ import annotations
import re
import json
from pathlib import Path
from typing import Dict, List

from llm.retry       import call_structured
from schemas.graph_state import ValidatorResult as GValidatorResult
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent.parent

_SYSTEM = """You are a strict spec-driven validator.

Rules:
1. You NEVER read source code. Only the test suite and the milestone report.
2. A test PASSES when the milestone report has clear evidence the expected outcome was achieved.
3. Absence of evidence = FAIL (not skip).
4. Security test failures always go in escalations, even if blocking: false.
5. security_checklist_followed: false = automatic SEC-GLOBAL-02 escalation.
6. Return ONLY valid JSON. No prose. No fences.

Return schema:
{
  "suite_id": str,
  "overall": "pass" | "fail",
  "blocking_passed": bool,
  "results": [{"test_id": str, "status": "pass"|"fail"|"skip", "notes": str}],
  "failures": [str],
  "escalations": [str]
}"""


class _ValidatorOutput(BaseModel):
    suite_id:        str
    overall:         str
    blocking_passed: bool
    results:         List[Dict] = Field(default_factory=list)
    failures:        List[str]  = Field(default_factory=list)
    escalations:     List[str]  = Field(default_factory=list)


def run(
    feature_id: str,
    milestone_report: str,
    provider:   str  = "gemini",
    root:       Path = ROOT,
) -> GValidatorResult:
    """
    Validate a feature.
    milestone_report: text content of the filed doc4.
    Returns a ValidatorResult for the graph state.
    """
    suite_block, global_tests = _extract_suite(feature_id, root)

    prompt = (
        f"Feature: {feature_id}\n\n"
        f"Test suite (doc3):\n{suite_block}\n\n"
        f"Global security tests:\n{global_tests}\n\n"
        f"Milestone report (only evidence source):\n{milestone_report}\n\n"
        "Validate every test case. Return the ValidatorResult JSON."
    )

    from llm.router import user_msg
    output = call_structured(
        provider=provider,
        messages=[user_msg(prompt)],
        system=_SYSTEM,
        schema=_ValidatorOutput,
        temperature=0.1,
        label="ValidatorResult",
    )

    # Write result back into the milestone report file
    _write_to_report(feature_id, output, root)

    return GValidatorResult(
        feature_id=feature_id,
        overall=output.overall,
        blocking_passed=output.blocking_passed,
        failures=output.failures,
        escalations=output.escalations,
        results=output.results,
    )


def _extract_suite(feature_id: str, root: Path):
    doc3 = root / "doc3_validation_contract.md"
    if not doc3.exists():
        return f"(doc3 not found)", ""
    text = doc3.read_text()
    suite_m = re.search(
        rf"### Suite {re.escape(feature_id)}.*?\n(.*?)(?=\n###|\n##|\Z)",
        text, re.DOTALL,
    )
    global_m = re.search(
        r"## Cross-feature security tests\s*```yaml\n(.*?)```", text, re.DOTALL,
    )
    return (
        suite_m.group(1).strip() if suite_m else f"(no suite found for {feature_id})",
        global_m.group(1).strip() if global_m else "",
    )


def _write_to_report(feature_id: str, output: _ValidatorOutput, root: Path) -> None:
    from datetime import datetime, timezone
    report = root / "reports" / f"{feature_id}_milestone.md"
    if not report.exists():
        return
    now  = datetime.now(timezone.utc).isoformat()
    text = report.read_text()
    block = (
        f"```yaml\nvalidator_result:\n"
        f'  run_at: "{now}"\n'
        f"  overall: {output.overall}\n"
        f"  blocking_passed: {str(output.blocking_passed).lower()}\n"
        f"  human_gate: pending\n"
        f"  failures: {json.dumps(output.failures)}\n"
        f"  escalations: {json.dumps(output.escalations)}\n"
        f"```"
    )
    new = re.sub(
        r"(## Validator result.*?```yaml\n).*?(```)",
        lambda m: m.group(1).rstrip() + "\n" + block[7:],
        text, flags=re.DOTALL, count=1,
    )
    report.write_text(new if new != text else text + f"\n\n## Validator result\n\n{block}\n")
