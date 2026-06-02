"""
agents/worker.py

Worker node — implements a feature via Claude API with tool use.

bash tool calls run inside the Docker test container (docker/runner.py).
file_write and file_read operate on the host filesystem (project root).

Docker is required — the worker fails fast with a clear error if the
container image is not built or the daemon is not running.
"""
from __future__ import annotations
import os
import re
import json
from pathlib import Path
from typing import Optional

from schemas.graph_state import FeatureContext, WorkerResult
from docker.runner import DockerRunner, DockerNotAvailableError, ImageNotBuiltError

ROOT = Path(__file__).parent.parent

_WORKER_SYSTEM = """You are a worker agent implementing a single software feature.

Rules you must follow without exception:
1. Read doc1_security_contract.md before writing any code.
2. Implement ONLY the feature described in your context — no scope creep.
3. Create your branch from develop: git fetch origin && git checkout develop 2>/dev/null || git checkout -b develop && git checkout -b {branch_name}
4. Commands run inside Docker — paths are relative to /project (the repo root).
5. Run: install deps → lint → tests → dependency audit. Record every command.
6. Fill reports/{feature_id}_milestone.md completely (copy from doc4_milestone_report.md).
7. Open a PR targeting develop: gh pr create --base develop --title "[{feature_id}] {title}" --body "$(cat reports/{feature_id}_milestone.md)"
8. Do not merge. Stop after opening the PR.
9. No secrets in code, logs, or milestone report summaries.
10. All inputs validated. Auth enforced on every protected route.
11. security_checklist_followed: true only if EVERY item in doc1 checklist is addressed.

You have three tools:
- bash: runs inside the Docker test container. The project is mounted at /project.
- file_write: writes a file to the project on the host filesystem.
- file_read: reads a file from the project on the host filesystem."""

_TOOLS = [
    {
        "name": "bash",
        "description": (
            "Run a shell command inside the Docker test container. "
            "The project root is mounted at /project. "
            "Use this for: git, npm/pip/cargo, lint, test, audit, gh CLI."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command. Paths relative to /project.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "file_write",
        "description": "Write content to a file in the project (host filesystem).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "Path relative to project root"},
                "content": {"type": "string", "description": "File content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "file_read",
        "description": "Read a file from the project (host filesystem).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to project root"},
            },
            "required": ["path"],
        },
    },
]


# ---------------------------------------------------------------------------
# Standing rules loader
# ---------------------------------------------------------------------------

def _load_standing_rules(root: Path) -> str:
    """
    Load CLAUDE.md and all .claude/rules/*.md files.
    Injected into the API system prompt so the worker receives the same
    instructions it would get running Claude Code manually.
    Strips paths: frontmatter — those are Claude Code directives, not API content.
    """
    parts = []

    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        parts.append(claude_md.read_text().strip())

    rules_dir = root / ".claude" / "rules"
    if rules_dir.exists():
        for f in sorted(rules_dir.glob("*.md")):
            content = f.read_text().strip()
            content = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL).strip()
            if content:
                parts.append(content)

    return "\n\n---\n\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Main worker entry point
# ---------------------------------------------------------------------------

def run(context: FeatureContext, root: Path = ROOT) -> WorkerResult:
    """
    Run the worker for a feature.
    1. Verifies Docker is available and the test image is built.
    2. Calls Claude API in an agentic tool-use loop.
    3. bash tool calls run inside Docker; file_* calls operate on host.
    4. Returns WorkerResult with the milestone report text.
    """
    import urllib.request
    import urllib.error

    fid = context["feature_id"]

    # ── Step 1: verify Docker before calling the API ─────────────────────────
    runner = DockerRunner(root=root)
    try:
        runner.verify()
    except DockerNotAvailableError as e:
        return WorkerResult(
            feature_id=fid, success=False, milestone_report="",
            error=f"Docker not available: {e}",
        )
    except ImageNotBuiltError as e:
        return WorkerResult(
            feature_id=fid, success=False, milestone_report="",
            error=f"Test image not built: {e}",
        )

    # ── Step 2: check API key ─────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return WorkerResult(
            feature_id=fid, success=False, milestone_report="",
            error="ANTHROPIC_API_KEY not set in .env",
        )

    model   = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    mem_str = json.dumps(context["memory"], indent=2)

    # ── Step 3: build initial prompt ─────────────────────────────────────────
    initial_prompt = (
        f"You are implementing feature {fid}: {context['title']}.\n\n"
        f"## Feature block\n{context['block_text']}\n\n"
        f"## Filtered project memory\n```json\n{mem_str}\n```\n\n"
        "## Your task\n"
        "1. file_read doc1_security_contract.md\n"
        "2. file_read doc4_milestone_report.md (the template)\n"
        f"3. Set up branch from develop:\n   bash → git fetch origin && (git checkout develop 2>/dev/null || git checkout -b develop origin/develop 2>/dev/null || git checkout -b develop) && git checkout -b {context['branch_name']}\n"
        "4. Implement the feature\n"
        "5. Run: install → lint → test → audit (all inside Docker via bash tool)\n"
        f"6. file_write reports/{fid}_milestone.md with completed report\n"
        f"7. bash → git add . && git commit && git push -u origin {context['branch_name']}"
        f" && gh pr create --base develop"
        f" --title '[{fid}] {context['title']}'"
        f" --body \"$(cat reports/{fid}_milestone.md)\"\n\n"
        "Start by reading doc1_security_contract.md."
    )

    # ── Step 4: build system prompt ───────────────────────────────────────────
    standing_rules = _load_standing_rules(root)
    base_system    = _WORKER_SYSTEM.format(
        branch_name=context["branch_name"],
        feature_id=fid,
        title=context["title"],
    )
    system = base_system
    if standing_rules:
        system += "\n\n---\n\n" + standing_rules

    messages = [{"role": "user", "content": initial_prompt}]

    # ── Step 5: agentic loop ──────────────────────────────────────────────────
    for turn in range(40):   # 40 turns: generous for complex features
        payload = json.dumps({
            "model":      model,
            "max_tokens": 4096,
            "system":     system,
            "tools":      _TOOLS,
            "messages":   messages,
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read().decode())
        except Exception as e:
            return WorkerResult(feature_id=fid, success=False,
                                milestone_report="", error=str(e))

        stop_reason = resp.get("stop_reason")
        content     = resp.get("content", [])
        messages.append({"role": "assistant", "content": content})

        if stop_reason == "end_turn":
            report_path = root / "reports" / f"{fid}_milestone.md"
            if report_path.exists():
                return WorkerResult(
                    feature_id=fid,
                    success=True,
                    milestone_report=report_path.read_text(),
                    error="",
                )
            return WorkerResult(
                feature_id=fid, success=False, milestone_report="",
                error="Worker finished but milestone report not found in reports/",
            )

        if stop_reason == "tool_use":
            tool_results = []
            for block in content:
                if block.get("type") != "tool_use":
                    continue
                result_str = _execute_tool(
                    name=block["name"],
                    inp=block["input"],
                    root=root,
                    runner=runner,
                )
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block["id"],
                    "content":     result_str,
                })
            messages.append({"role": "user", "content": tool_results})
            continue

        break   # unexpected stop reason

    return WorkerResult(
        feature_id=fid, success=False, milestone_report="",
        error="Worker exceeded maximum turns (40) without completing",
    )


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def _execute_tool(
    name:   str,
    inp:    dict,
    root:   Path,
    runner: DockerRunner,
) -> str:
    """
    Execute a single tool call.
    - bash      → runs inside Docker via runner
    - file_write / file_read → operate on host filesystem
    """
    try:
        if name == "bash":
            result = runner.run(inp["command"])
            output = result.stdout + result.stderr
            # Truncate long output before returning to LLM
            if len(output) > 3000:
                output = output[:1500] + "\n...[truncated]...\n" + output[-800:]
            return (
                f"exit_code: {result.exit_code}\n"
                f"summary: {result.summary}\n"
                f"output:\n{output}"
            )

        elif name == "file_write":
            path = root / inp["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(inp["content"])
            return f"Written: {inp['path']} ({len(inp['content'])} chars)"

        elif name == "file_read":
            path = root / inp["path"]
            if not path.exists():
                return f"Error: {inp['path']} not found"
            content = path.read_text()
            if len(content) > 4000:
                content = content[:2000] + "\n...[truncated]...\n" + content[-1000:]
            return content

        else:
            return f"Error: unknown tool '{name}'"

    except Exception as e:
        return f"Error executing {name}: {e}"
