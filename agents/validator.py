"""
agents/validator.py

Validator node — generates executable tests from doc3 and runs them against
the live application. Real exit codes determine pass/fail, not LLM opinion.

Flow:
  1. Read ONLY the doc3 test suite for this feature (interface-level specs:
     HTTP method/path/body -> expected status/response). Never source code.
  2. Generate a pytest file implementing each test case as a real HTTP test
     (Gemini — pure code generation, never sees the implementation).
  3. Start the application in Docker (app_run_command/app_port from doc0),
     wait until it responds.
  4. Run the generated tests against the running app in a sibling container
     on the shared docker network.
  5. Map each doc3 test_id to its real pytest result (PASSED/FAILED/ERROR/SKIPPED).
  6. Run three deterministic security checks (pure Python, no LLM) against
     the milestone report — no secrets in logs, security checklist followed,
     dependency audit clean.
  7. overall=pass only if every blocking test_id actually passed AND the
     deterministic security checks pass.

Zero git access. Never modifies application source.
"""
from __future__ import annotations
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple

from llm.router import call, user_msg, assistant_msg
from schemas.graph_state import ValidatorResult as GValidatorResult
from agents.cto import get_app_config
from docker.runner import DockerRunner, DockerNotAvailableError, ImageNotBuiltError

ROOT = Path(__file__).parent.parent

CODEGEN_MAX_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Code generation — Gemini sees only the doc3 spec, never source code
# ---------------------------------------------------------------------------

_CODEGEN_SYSTEM = """You write executable pytest test files from API-level specifications.

You have NEVER seen the implementation source code. You only know the specification given to you.

Rules:
1. Output a SINGLE Python file using pytest and the `requests` library. Nothing else.
2. The application under test is reachable at the base_url given to you.
3. For EVERY test case listed, write exactly one function with the exact name given to you.
   Do not rename, merge, or split these functions.
4. Implement given/when/expected as a real HTTP interaction:
   - "given"    = any setup needed before the action (e.g. create a resource via the API first)
   - "when"     = the HTTP request described (method, path, body, headers)
   - "expected" = assert on status code and/or response body matching the description
5. If a test case describes something that cannot be checked via HTTP
   (e.g. log output, internal checklists, code style, non-functional concerns), write:
     def test_<id>():
         pytest.skip("not verifiable via HTTP — checked separately")
6. Use descriptive assert messages so failures are readable.
7. Output ONLY raw Python code. No markdown fences, no prose, no explanation.
8. The file must run standalone with: pytest <file> -v"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:python)?\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.strip()


def _generate_test_code(
    feature_id: str,
    test_cases: List[Dict],
    base_url:   str,
    provider:   str,
) -> str:
    """
    Generate a pytest file from doc3 test case specs.
    Retries up to CODEGEN_MAX_ATTEMPTS if the output is invalid Python or is
    missing required test function names. Returns best-effort code after
    exhausting attempts.
    """
    required_fns = {tc["test_id"]: f"test_{tc['test_id'].replace('-', '_')}" for tc in test_cases}

    spec_text = "\n\n".join(tc["raw"] for tc in test_cases)
    fn_list   = "\n".join(f"- {tid} -> def {fn}(...)" for tid, fn in required_fns.items())

    prompt = (
        f"Base URL of the running application: {base_url}\n\n"
        f"Test case specifications (from doc3, the validation contract):\n{spec_text}\n\n"
        f"Required function names (use these exactly):\n{fn_list}\n\n"
        "Generate the pytest file now."
    )

    messages  = [user_msg(prompt)]
    last_code = ""

    for attempt in range(1, CODEGEN_MAX_ATTEMPTS + 1):
        raw  = call(provider, messages, _CODEGEN_SYSTEM, temperature=0.2, max_tokens=8192)
        code = _strip_fences(raw)
        last_code = code

        try:
            ast.parse(code)
        except SyntaxError as e:
            messages += [assistant_msg(raw), user_msg(
                f"SyntaxError: {e}. Return the full corrected file, raw Python only."
            )]
            continue

        missing = [fn for fn in required_fns.values() if f"def {fn}" not in code]
        if missing:
            messages += [assistant_msg(raw), user_msg(
                f"Missing required test functions: {missing}. "
                "Return the FULL corrected file with all required functions, raw Python only."
            )]
            continue

        return code

    return last_code  # best effort after exhausting retries


# ---------------------------------------------------------------------------
# doc3 parsing
# ---------------------------------------------------------------------------

def _extract_suite(feature_id: str, root: Path) -> str:
    doc3 = root / "doc3_validation_contract.md"
    if not doc3.exists():
        return ""
    text = doc3.read_text()
    m = re.search(
        rf"### Suite {re.escape(feature_id)}.*?\n(.*?)(?=\n###|\n##|\Z)",
        text, re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _extract_test_cases_yaml(suite_block: str) -> str:
    """
    doc3 has two yaml fences per suite: suite metadata, then test cases under
    a '**Test cases**' heading. Prefer the labelled fence; fall back to the
    first fence that actually contains test_id entries.
    """
    m = re.search(r"\*\*Test cases\*\*\s*```yaml\n(.*?)```", suite_block, re.DOTALL)
    if m:
        return m.group(1)
    for fence in re.findall(r"```yaml\n(.*?)```", suite_block, re.DOTALL):
        if "test_id:" in fence:
            return fence
    return ""


def _parse_test_cases(yaml_text: str) -> List[Dict]:
    """
    Parse the test_cases YAML list into dicts with test_id, type, blocking, raw.
    'raw' is passed to Gemini verbatim — the full given/when/expected for that case.
    """
    cases = []
    blocks = re.split(r"(?=^- test_id:)", yaml_text, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block or "test_id" not in block:
            continue
        tid_m = re.search(r'test_id:\s*"?([\w-]+)"?', block)
        if not tid_m:
            continue
        type_m     = re.search(r"^\s*type:\s*(\w+)", block, re.MULTILINE)
        blocking_m = re.search(r"blocking:\s*(true|false)", block)
        cases.append({
            "test_id":  tid_m.group(1),
            "type":     type_m.group(1) if type_m else "unit",
            "blocking": (blocking_m.group(1) == "true") if blocking_m else True,
            "raw":      block,
        })
    return cases


# ---------------------------------------------------------------------------
# Deterministic security checks — pure Python, no LLM
# ---------------------------------------------------------------------------

_SECRET_PATTERN = re.compile(
    r"(api.?key|token|password|secret|credential)\s*[:=]\s*\S+", re.IGNORECASE,
)


def _check_security(report_text: str) -> Tuple[List[str], List[str]]:
    """
    Run the three global security checks against the milestone report.
    Returns (failures, escalations) — both lists of "SEC-GLOBAL-NN" ids.
    Pure string/regex checks. No model call — deterministic and free.
    """
    failures:    List[str] = []
    escalations: List[str] = []

    # SEC-GLOBAL-02 — security checklist followed
    m = re.search(r"security_checklist_followed:\s*(true|false)", report_text)
    if not m or m.group(1) == "false":
        failures.append("SEC-GLOBAL-02")
        escalations.append("SEC-GLOBAL-02")

    cmds_m    = re.search(r"## Commands run\s*```yaml\n(.*?)```", report_text, re.DOTALL)
    cmds_text = cmds_m.group(1) if cmds_m else ""

    # SEC-GLOBAL-01 — no secrets in command summaries
    if cmds_text and _SECRET_PATTERN.search(cmds_text):
        failures.append("SEC-GLOBAL-01")
        escalations.append("SEC-GLOBAL-01")

    # SEC-GLOBAL-03 — dependency audit ran clean
    audit_entries = re.findall(
        r'cmd:\s*"[^"]*audit[^"]*".*?exit_code:\s*(\d+).*?stdout_summary:\s*"([^"]*)"',
        cmds_text, re.DOTALL | re.IGNORECASE,
    )
    if not audit_entries:
        failures.append("SEC-GLOBAL-03")
        escalations.append("SEC-GLOBAL-03")
    else:
        for exit_code, summary in audit_entries:
            if exit_code != "0" or re.search(r"\b(high|critical)\b", summary, re.IGNORECASE):
                failures.append("SEC-GLOBAL-03")
                escalations.append("SEC-GLOBAL-03")
                break

    return failures, escalations


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(
    feature_id:       str,
    milestone_report: str,
    provider:         str  = "gemini",
    root:             Path = ROOT,
) -> GValidatorResult:
    suite_block = _extract_suite(feature_id, root)
    yaml_text   = _extract_test_cases_yaml(suite_block)
    test_cases  = _parse_test_cases(yaml_text)

    app_config = get_app_config(root)
    app_cmd    = app_config["run_command"]
    app_port   = app_config["port"]

    container_name = f"app-{feature_id.lower()}"
    base_url       = f"http://{container_name}:{app_port}"

    results:     List[Dict] = []
    runtime_note = ""

    if test_cases and app_cmd and app_port:
        # 1. Generate executable tests from doc3 — Gemini sees only the spec
        test_code = _generate_test_code(feature_id, test_cases, base_url, provider)

        validation_dir = root / "validation"
        validation_dir.mkdir(exist_ok=True)
        (validation_dir / f"{feature_id}_test.py").write_text(test_code)

        # 2. Start the app and run the generated tests against it
        runner = DockerRunner(root=root)
        try:
            runner.verify()
            runner.start_app(app_cmd, app_port, container_name)
            ready = runner.wait_for_app(container_name, app_port)

            if not ready:
                logs = runner.get_app_logs(container_name)
                runtime_note = f"App did not become ready. Last logs:\n{logs[-800:]}"
                for tc in test_cases:
                    results.append({
                        "test_id": tc["test_id"], "status": "fail",
                        "notes": "app did not start — see milestone report note",
                        "type": tc["type"], "blocking": tc["blocking"],
                    })
            else:
                rel_path = f"validation/{feature_id}_test.py"
                pr = runner.run(
                    f"python3 -m pytest {rel_path} -v --tb=short -p no:cacheprovider",
                    network=runner.network,
                )
                output = pr.stdout + pr.stderr
                runtime_note = f"pytest exit {pr.exit_code}"

                for tc in test_cases:
                    fn = f"test_{tc['test_id'].replace('-', '_')}"
                    m  = re.search(rf"::{re.escape(fn)}\s+(PASSED|FAILED|ERROR|SKIPPED)", output)
                    if m:
                        status_raw = m.group(1)
                        status = {"PASSED": "pass", "FAILED": "fail",
                                  "ERROR": "fail", "SKIPPED": "skip"}[status_raw]
                        note = "" if status != "fail" else _extract_failure_reason(output, fn)
                    else:
                        status = "fail"
                        note   = "generated test function not found in pytest output"
                    results.append({
                        "test_id": tc["test_id"], "status": status, "notes": note,
                        "type": tc["type"], "blocking": tc["blocking"],
                    })

        except (DockerNotAvailableError, ImageNotBuiltError) as e:
            runtime_note = str(e)
            for tc in test_cases:
                results.append({
                    "test_id": tc["test_id"], "status": "fail",
                    "notes": f"docker error: {e}",
                    "type": tc["type"], "blocking": tc["blocking"],
                })
        finally:
            try:
                runner.stop_app(container_name)
            except Exception:
                pass

    elif not (app_cmd and app_port):
        runtime_note = (
            "app_run_command / app_port missing from doc0 shared plan — "
            "cannot start the app to run executable tests. "
            "Only deterministic security checks were run."
        )
    else:
        runtime_note = "No test cases found in doc3 for this feature."

    # 3. Deterministic security checks — always run, pure Python
    sec_failures, sec_escalations = _check_security(milestone_report)

    # 4. Combine
    exec_failures    = [r["test_id"] for r in results if r["status"] == "fail"]
    exec_escalations = [r["test_id"] for r in results
                         if r["status"] == "fail" and r["type"] == "security"]
    blocking_failed  = [r["test_id"] for r in results
                         if r["status"] == "fail" and r["blocking"]]

    failures    = list(dict.fromkeys(exec_failures + sec_failures))
    escalations = list(dict.fromkeys(exec_escalations + sec_escalations))

    blocking_passed = not blocking_failed and not sec_failures
    overall = "pass" if blocking_passed else "fail"

    result = GValidatorResult(
        feature_id=feature_id,
        overall=overall,
        blocking_passed=blocking_passed,
        failures=failures,
        escalations=escalations,
        results=(
            [{"test_id": r["test_id"], "status": r["status"], "notes": r["notes"]} for r in results]
            + _security_check_results(sec_failures)
        ),
    )

    _write_to_report(feature_id, result, root, runtime_note)
    return result


def _security_check_results(failures: List[str]) -> List[Dict]:
    labels = {
        "SEC-GLOBAL-01": "No secrets in command output",
        "SEC-GLOBAL-02": "Security checklist followed",
        "SEC-GLOBAL-03": "Dependency audit clean",
    }
    return [
        {"test_id": sid, "status": "fail" if sid in failures else "pass", "notes": label}
        for sid, label in labels.items()
    ]


def _extract_failure_reason(pytest_output: str, fn_name: str) -> str:
    """Pull a short assertion message for a failed test from pytest -v --tb=short output."""
    m = re.search(
        rf"{re.escape(fn_name)}.*?\n(.*?AssertionError.*?)(?=\n_{{5,}}|\nFAILED|\Z)",
        pytest_output, re.DOTALL,
    )
    if not m:
        return "see validation/ pytest output for details"
    line = m.group(1).strip().splitlines()[-1]
    return line[:150]


# ---------------------------------------------------------------------------
# Write result back into the milestone report
# ---------------------------------------------------------------------------

def _write_to_report(feature_id: str, result: GValidatorResult, root: Path, note: str) -> None:
    from datetime import datetime, timezone
    report = root / "reports" / f"{feature_id}_milestone.md"
    if not report.exists():
        return

    now  = datetime.now(timezone.utc).isoformat()
    text = report.read_text()
    safe_note = note[:200].replace('"', "'").replace("\n", " ")

    block = (
        f"```yaml\nvalidator_result:\n"
        f'  run_at: "{now}"\n'
        f'  overall: {result["overall"]}\n'
        f'  blocking_passed: {str(result["blocking_passed"]).lower()}\n'
        f"  human_gate: pending\n"
        f'  failures: {json.dumps(result["failures"])}\n'
        f'  escalations: {json.dumps(result["escalations"])}\n'
        f'  generated_test_file: "validation/{feature_id}_test.py"\n'
        f'  note: "{safe_note}"\n'
        f"```"
    )

    new = re.sub(
        r"(## Validator result.*?```yaml\n).*?(```)",
        lambda m: m.group(1).rstrip() + "\n" + block[7:],
        text, flags=re.DOTALL, count=1,
    )
    report.write_text(new if new != text else text + f"\n\n## Validator result\n\n{block}\n")
