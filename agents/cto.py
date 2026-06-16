"""
agents/cto.py

CTO orchestrator agent.
Each method = one atomic model call with typed, validated output.
"""
from __future__ import annotations
import json
import re
import yaml
from pathlib import Path
from typing import List, Dict, Optional

from llm.router  import call, user_msg, assistant_msg
from llm.retry   import call_structured
from schemas.cto_outputs import (
    ClarificationQuestion, SharedPlan, FeatureBlock,
    SpawnPlan, ContractConsistencyCheck, ServiceSpec,
)
from schemas.graph_state  import FeatureContext, GraphState
from memory import store as mem_store

ROOT = Path(__file__).parent.parent

_BASE = (
    "You are a CTO orchestrating a software project. "
    "Reason carefully. Return only valid JSON matching the requested schema. "
    "No prose. No markdown fences."
)

_CLARIFY_SYS = _BASE + (
    "\nTask: identify the single most important gap in the project brief. "
    "If you have enough to write a solid plan, set sufficient: true."
)

_PLAN_SYS = _BASE + (
    "\nTask: write a complete shared plan. All tech_stack fields must be filled. "
    "No TBD. Be specific enough that a developer can start immediately. "
    "\n\n"
    "You must decide app_type — one of:\n"
    "  'api'       — pure backend (REST/GraphQL/gRPC). No browser UI served.\n"
    "  'frontend'  — client-side only (SPA, static site). No significant API.\n"
    "  'fullstack' — serves both UI and API from the same process "
    "(Next.js, Nuxt, Django+templates, Rails, Laravel, etc.)\n\n"
    "This determines how the validator tests the app:\n"
    "  api       → pytest + requests (HTTP assertions)\n"
    "  frontend / fullstack → Playwright (browser-level: click, fill, assert on DOM)\n\n"
    "You must also decide app_run_command (the exact shell command that starts "
    "the application in development mode, e.g. 'npm run dev' or "
    "'uvicorn main:app --host 0.0.0.0 --port 8000') and app_port (the integer "
    "port it listens on) — the validator runs this command in Docker and tests "
    "against it, so it must be concrete and correct for the chosen tech stack.\n\n"
    "If the application needs a database, cache, queue, or any other backing "
    "service to run, list each one in `services`: a name (lowercase, used as both "
    "the Docker container name and DNS hostname — e.g. 'db', 'redis'), a "
    "concrete image (e.g. 'postgres:16-alpine', 'redis:7-alpine'), the port it "
    "listens on, and any env vars the SERVICE container itself needs. "
    "Then set `app_env` to the env vars the APPLICATION needs to connect to "
    "those services, using the service `name` as the hostname. "
    "If the app needs nothing beyond itself, leave services and app_env empty."
)

_CONTRACT_SYS = _BASE + (
    "\nTask: generate project contracts. "
    "Acceptance criteria: Given/When/Then format only. "
    "Every feature must have at least one security test in the validation contract."
)

_SPAWN_SYS = _BASE + (
    "\nTask: given the approved features and DAG, decide the execution plan. "
    "Identify which features can run in parallel (parallel_safe: true, no unmet deps). "
    "Group sequential features that must wait for others."
)

_CONSISTENCY_SYS = _BASE + (
    "\nTask: check your own contracts for consistency. "
    "Every feature in doc2 must have a matching test suite in doc3. "
    "Every security constraint ref in doc2 must exist in doc1."
)


# ---------------------------------------------------------------------------
# Phase 1 — Clarification
# ---------------------------------------------------------------------------

def get_next_question(history: List[Dict], provider: str, root: Path = ROOT) -> ClarificationQuestion:
    doc0 = (root / "doc0_project_brief.md").read_text()
    msgs = [user_msg(
        f"Project brief:\n\n{doc0}\n\n"
        "Return a ClarificationQuestion JSON: "
        "{question: str, why_important: str, sufficient: bool}. "
        "One question only, or set sufficient: true if you have enough."
    )] + history
    return call_structured(provider, msgs, _CLARIFY_SYS, ClarificationQuestion,
                           label="ClarificationQuestion")


def write_plan(history: List[Dict], provider: str, root: Path = ROOT) -> SharedPlan:
    doc0 = (root / "doc0_project_brief.md").read_text()
    msgs = [user_msg(
        f"Project brief + clarification log:\n\n{doc0}\n\n"
        "Return a SharedPlan JSON with ALL fields: "
        "{summary, key_decisions, open_assumptions, tech_stack, scope_boundary, "
        "first_milestone, app_type, app_run_command, app_port, app_env, services}.\n\n"
        "app_type: 'api' (pure backend), 'frontend' (client-side only), or "
        "'fullstack' (serves both UI and API — Next.js, Nuxt, Django+templates, etc.).\n"
        "app_run_command: exact shell command to start in dev mode.\n"
        "app_port: integer port it listens on.\n"
        "services: list of {name, image, port, env} for any database/cache/queue "
        "needed (empty list if none).\n"
        "app_env: env vars the app needs to connect to those services (empty dict if none)."
    )] + history
    plan = call_structured(provider, msgs, _PLAN_SYS, SharedPlan, label="SharedPlan")
    _write_plan_to_doc0(root, plan)
    return plan


def revise_plan(history: List[Dict], rejection_note: str,
                provider: str, root: Path = ROOT) -> SharedPlan:
    doc0 = (root / "doc0_project_brief.md").read_text()
    msgs = [user_msg(
        f"Brief:\n\n{doc0}\n\nRejection note: {rejection_note}\n\n"
        "Revise the SharedPlan to address the feedback. Return SharedPlan JSON "
        "with ALL fields: summary, key_decisions, open_assumptions, tech_stack, "
        "scope_boundary, first_milestone, app_type, app_run_command, app_port, "
        "app_env, services."
    )] + history
    plan = call_structured(provider, msgs, _PLAN_SYS, SharedPlan, label="SharedPlan (revision)")
    _write_plan_to_doc0(root, plan)
    return plan


# ---------------------------------------------------------------------------
# Phase 2 — Contract generation
# ---------------------------------------------------------------------------

def generate_contracts(provider: str, root: Path = ROOT) -> Dict:
    """
    Generate all three contracts using the template files as format references.
    Templates (doc1/doc2/doc3) must exist in the repo root — they define the
    exact structure the CTO must produce. The generated files overwrite the templates.
    """
    doc0 = (root / "doc0_project_brief.md").read_text()
    tpl1 = _load_template(root, "doc1_security_contract.md")
    tpl2 = _load_template(root, "doc2_features_contract.md")
    tpl3 = _load_template(root, "doc3_validation_contract.md")

    # ── Security contract ────────────────────────────────────────────────────
    sec_raw = call(provider, [user_msg(
        f"Approved project plan:\n\n{doc0}\n\n"
        "Generate a complete, filled doc1_security_contract.md.\n\n"
        "Rules:\n"
        "- Fill every YAML field — no placeholders, no TBD\n"
        "- threat_model: name specific actors and their attack vectors\n"
        "- auth.mechanism: concrete choice (JWT, session, OAuth2, API key)\n"
        "- data.pii_fields: list actual field names from this domain\n"
        "- Security checklist: 8+ items, each actionable\n"
        "- Reproduce the exact template structure below, filled for this project\n\n"
        f"TEMPLATE:\n\n{tpl1}\n\n"
        "Return the complete filled markdown. No placeholders. No comments."
    )], _CONTRACT_SYS, temperature=0.2, max_tokens=8192)
    _save(root, "doc1_security_contract.md", sec_raw)

    # ── Features contract ────────────────────────────────────────────────────
    feat_raw = call(provider, [user_msg(
        f"Approved plan:\n\n{doc0}\n\n"
        f"Security contract (doc1, already written):\n{sec_raw[:2000]}\n\n"
        "Generate a complete, filled doc2_features_contract.md.\n\n"
        "Rules:\n"
        "- feature_id format: F-MM-NNN (M = milestone number, N = sequence)\n"
        "- acceptance_criteria: Given/When/Then format — every criterion testable\n"
        "- security_constraints: ref doc1 by exact section heading\n"
        "- depends_on: explicit feature_id list (empty [] only if truly independent)\n"
        "- branch_name: kebab-case, e.g. feature/F-01-001-user-login\n"
        "- Fill the milestone map and the feature status tracker table\n"
        "- Reproduce the exact template structure below, filled for this project\n\n"
        f"TEMPLATE:\n\n{tpl2}\n\n"
        "Return the complete filled markdown. No placeholders."
    )], _CONTRACT_SYS, temperature=0.2, max_tokens=8192)
    _save(root, "doc2_features_contract.md", feat_raw)

    # Parse feature blocks for state population and doc3 generation
    features = _parse_feature_blocks(feat_raw)
    criteria_summary = json.dumps([
        {"id": f["feature_id"], "criteria": f.get("acceptance_criteria", [])}
        for f in features
    ], indent=2)

    # ── Validation contract ──────────────────────────────────────────────────
    # Determine test format based on app_type so doc3 cases are the right shape
    # for the validator's code-gen prompt.
    app_type = "api"
    app_type_m = re.search(r'app_type:\s*"?([\w]+)"?', doc0)
    if app_type_m:
        app_type = app_type_m.group(1).lower()

    if app_type == "api":
        interface_rule = (
            "CRITICAL: for feature-specific tests, given/when/expected must be written "
            "at the HTTP INTERFACE level (HTTP method + path + request body/headers, and "
            "expected status code + response body shape) — concrete enough that someone "
            "who has NEVER seen the source code could write a `requests`-based pytest "
            "test from this description alone. Example:\n"
            "  given: \"no user exists with email a@b.com\"\n"
            "  when: \"POST /api/users {email: a@b.com, password: secret123}\"\n"
            "  expected: \"201 Created, body contains id and email, no password field\""
        )
    else:
        interface_rule = (
            "CRITICAL: the app_type is '" + app_type + "', so tests will run in a "
            "real browser via Playwright. For feature-specific tests, given/when/expected "
            "must be written at the BROWSER INTERACTION level — what a user sees, clicks, "
            "and types in the UI — concrete enough that someone who has NEVER seen the "
            "source code could write a Playwright test from this description alone. "
            "Use the running app's URL (already known to the test generator). Example:\n"
            "  given: \"user is on the registration page at /register\"\n"
            "  when: \"user fills in email 'a@b.com', password 'secret123', clicks Submit\"\n"
            "  expected: \"page navigates to /dashboard, heading 'Welcome' is visible\"\n\n"
            "Security tests that are best verified at the API level (e.g. rate limiting, "
            "auth headers) may still use HTTP-level given/when/expected — mark those "
            "with verified_via: executable_test_api so the generator uses requests for them."
        )

    val_raw = call(provider, [user_msg(
        f"Feature acceptance criteria from doc2:\n{criteria_summary}\n\n"
        f"app_type: {app_type}\n\n"
        "Generate a complete, filled doc3_validation_contract.md.\n\n"
        "Rules:\n"
        "- Every feature in doc2 must have a Suite block (suite_id = feature_id)\n"
        "- Every acceptance criterion must appear as a test case\n"
        "- Every suite must include at least one security test (type: security)\n"
        f"- {interface_rule}\n"
        "- verified_via for feature-specific tests: 'executable_test' "
        "(the validator generates real test code from given/when/expected and runs it "
        "against the live application — requests-based for 'api', "
        "Playwright-based for 'frontend'/'fullstack')\n"
        "- verified_via for the three global security tests stays milestone-report-based "
        "(e.g. milestone_report.security_checklist_followed, "
        "milestone_report.commands_run[*].exit_code) — these are checked deterministically\n"
        "- Always include SEC-GLOBAL-01, SEC-GLOBAL-02, SEC-GLOBAL-03 exactly as in the template\n"
        "- human_gate_required: true for auth, PII, payment features\n"
        "- Reproduce the exact template structure below, filled for this project\n\n"
        f"TEMPLATE:\n\n{tpl3}\n\n"
        "Return the complete filled markdown. No placeholders."
    )], _CONTRACT_SYS, temperature=0.2, max_tokens=8192)
    _save(root, "doc3_validation_contract.md", val_raw)

    # Self-consistency check
    _consistency_check(features, val_raw, provider)

    return {"features": features, "sec": sec_raw, "feat": feat_raw, "val": val_raw}


# ---------------------------------------------------------------------------
# Phase 3 — Spawn planning (CTO as orchestrator)
# ---------------------------------------------------------------------------

def build_spawn_plan(
    features:      List[Dict],
    selected_ids:  List[str],
    passed_ids:    List[str],
    provider:      str,
) -> SpawnPlan:
    """
    Given selected features and which ones are already passed,
    decide which to run now (parallel batch) and which wait (sequential groups).
    """
    selected = [f for f in features if f["feature_id"] in selected_ids]
    summary  = json.dumps([{
        "feature_id":   f["feature_id"],
        "title":        f.get("title", ""),
        "depends_on":   f.get("depends_on", []),
        "parallel_safe": f.get("parallel_safe", True),
    } for f in selected], indent=2)

    msgs = [user_msg(
        f"Features to execute:\n{summary}\n\n"
        f"Already passed: {passed_ids}\n\n"
        "Return a SpawnPlan JSON: "
        "{batch: [feature_ids to run now in parallel], "
        "sequential: [[group1_ids], [group2_ids], ...], "
        "reasoning: str}. "
        "batch = features with no unmet dependencies and parallel_safe: true. "
        "sequential = ordered groups that must wait for previous groups to pass."
    )]
    return call_structured(provider, msgs, _SPAWN_SYS, SpawnPlan, label="SpawnPlan")


def build_feature_contexts(
    features:     List[Dict],
    feature_ids:  List[str],
    passed_ids:   List[str],
    root:         Path = ROOT,
) -> Dict[str, FeatureContext]:
    """
    Build worker context for each selected feature.
    Injects: feature block, filtered memory, security constraints.
    """
    mem = mem_store.load(root)
    ctx: Dict[str, FeatureContext] = {}

    for f in features:
        fid = f["feature_id"]
        if fid not in feature_ids:
            continue

        depends_chain = _build_chain(fid, {f["feature_id"]: f for f in features})
        filtered_mem  = mem_store.filter_for_feature(fid, list(depends_chain), mem)

        ctx[fid] = FeatureContext(
            feature_id=fid,
            title=f.get("title", ""),
            milestone_id=f.get("milestone_id", ""),
            depends_on=f.get("depends_on", []),
            priority=f.get("priority", "medium"),
            block_text=f.get("_raw", ""),
            memory=filtered_mem,
            branch_name=f.get("branch_name", f"feature/{fid.lower()}"),
            retry_note="",
        )

    return ctx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_template(root: Path, filename: str) -> str:
    """
    Load a contract template file.
    These live in the repo root and define the exact structure the CTO must produce.
    If the template does not exist, return a minimal fallback hint.
    """
    p = root / filename
    return p.read_text() if p.exists() else f"(template {filename} not found — produce standard structure)"


def append_clarification_round(root: Path, n: int, question: str, answer: str) -> None:
    doc0 = root / "doc0_project_brief.md"
    text = doc0.read_text()
    entry = f'\n---\nround: {n}\nquestion: "{question}"\nanswer: "{answer}"\nresolved: true\n---'
    text = text.replace("## Shared plan", entry + "\n\n## Shared plan") \
        if "## Shared plan" in text else text + entry
    doc0.write_text(text)


def _write_plan_to_doc0(root: Path, plan: SharedPlan) -> None:
    doc0 = root / "doc0_project_brief.md"
    text = doc0.read_text()
    block = (
        f"shared_plan_approved: false\n\n"
        f"summary: >\n  {plan.summary}\n\n"
        f"key_decisions:\n" +
        "".join(f"  - {d['decision']}: {d['rationale']}\n" for d in plan.key_decisions) +
        f"\nopen_assumptions:\n" +
        "".join(f"  - {a}\n" for a in plan.open_assumptions) +
        f"\ntech_stack:\n" +
        "".join(f"  {k}: {v}\n" for k, v in plan.tech_stack.items()) +
        f'\nscope_boundary: "{plan.scope_boundary}"\n'
        f'first_milestone: "{plan.first_milestone}"\n'
        f'app_type: "{plan.app_type}"\n'
        f'app_run_command: "{plan.app_run_command}"\n'
        f"app_port: {plan.app_port}\n"
        f"\n"
        f"# Auxiliary services (databases, caches, queues) and env vars the\n"
        f"# application needs. The validator starts every service on the shared\n"
        f"# Docker network, waits for each to be reachable, then starts the app\n"
        f"# with app_env injected, so the app can reach services by their `name`.\n"
        f"```yaml\n"
        + yaml.dump({
            "app_env":  plan.app_env,
            "services": [s.model_dump() for s in plan.services],
        }, sort_keys=False, default_flow_style=False)
        + "```\n"
    )
    text = re.sub(r"shared_plan_approved: false.*$", block, text, flags=re.DOTALL)
    doc0.write_text(text)


def get_app_config(root: Path = ROOT) -> Dict[str, object]:
    """
    Read the application's runtime config from the approved shared plan in doc0:
    app_type, run_command, port, env vars, and auxiliary services (db, cache, etc.)
    Used by the validator to know HOW to test (Playwright vs requests) and
    WHAT to start before running tests.
    Returns empty/zero/api defaults if not found.
    """
    default: Dict[str, object] = {
        "app_type":    "api",
        "run_command": "",
        "port":        0,
        "env":         {},
        "services":    [],
    }

    doc0 = root / "doc0_project_brief.md"
    if not doc0.exists():
        return default
    text = doc0.read_text()

    type_m = re.search(r'app_type:\s*"?([\w]+)"?', text)
    cmd_m  = re.search(r'app_run_command:\s*"(.*?)"', text)
    port_m = re.search(r"app_port:\s*(\d+)", text)

    default["app_type"]    = type_m.group(1).lower() if type_m else "api"
    default["run_command"] = cmd_m.group(1) if cmd_m else ""
    default["port"]        = int(port_m.group(1)) if port_m else 0

    yaml_m = re.search(r"```yaml\n(app_env:.*?)\n```", text, re.DOTALL)
    if yaml_m:
        try:
            extra = yaml.safe_load(yaml_m.group(1)) or {}
            default["env"]      = extra.get("app_env", {}) or {}
            default["services"] = extra.get("services", []) or []
        except yaml.YAMLError:
            pass

    return default


def _save(root: Path, filename: str, content: str) -> None:
    (root / filename).write_text(content.strip() + "\n")


def _parse_feature_blocks(feat_raw: str) -> List[Dict]:
    features = []
    for m in re.finditer(r"### (F-\d+-\d+)[^\n]*\n(.*?)(?=\n###|\Z)", feat_raw, re.DOTALL):
        fid  = m.group(1)
        body = m.group(2)
        meta: Dict = {"feature_id": fid, "_raw": m.group(0).strip()}
        yaml_m = re.search(r"```yaml\n(.*?)```", body, re.DOTALL)
        if yaml_m:
            for line in yaml_m.group(1).splitlines():
                line = line.strip()
                if ":" not in line or line.startswith("#"):
                    continue
                k, _, v = line.partition(":")
                k = k.strip(); v = v.split("#")[0].strip().strip('"').strip("'")
                if v.startswith("[") and v.endswith("]"):
                    meta[k] = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
                elif v.lower() == "true":  meta[k] = True
                elif v.lower() == "false": meta[k] = False
                else:                      meta[k] = v
        criteria_m = re.search(r"\*\*Acceptance criteria\*\*(.*?)(?=\*\*|\Z)", body, re.DOTALL)
        if criteria_m:
            meta["acceptance_criteria"] = [
                line.strip().lstrip("- []").strip()
                for line in criteria_m.group(1).splitlines()
                if line.strip().startswith("- ")
            ]
        features.append(meta)
    return features


def _build_chain(fid: str, feature_map: Dict[str, Dict], visited: set = None) -> set:
    if visited is None:
        visited = set()
    if fid in visited:
        return visited
    visited.add(fid)
    for dep in feature_map.get(fid, {}).get("depends_on", []):
        _build_chain(dep, feature_map, visited)
    return visited


def _consistency_check(features: List[Dict], val_raw: str, provider: str) -> None:
    feature_ids = [f["feature_id"] for f in features]
    suite_ids   = re.findall(r"### Suite (F-\d+-\d+)", val_raw)
    missing     = [fid for fid in feature_ids if fid not in suite_ids]
    check = call_structured(provider, [user_msg(
        f"Features: {feature_ids}\n"
        f"Validation suites found: {suite_ids}\n"
        f"Missing suites: {missing}\n\n"
        "Return a ContractConsistencyCheck JSON: "
        "{all_features_have_suites, all_security_refs_exist, "
        "all_criteria_testable, milestone_order_logical, issues, approved}."
    )], _CONSISTENCY_SYS, ContractConsistencyCheck, label="ConsistencyCheck")
    if not check.approved:
        raise RuntimeError(f"Contract consistency failed: {'; '.join(check.issues)}")
