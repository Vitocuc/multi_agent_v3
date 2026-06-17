"""
agents/worker.py

Worker node — implements a feature via Claude API.

The worker has NO git access. Its only job is:
  1. Read the contracts and memory
  2. Write source files
  3. Run tests (via a sandboxed test_runner tool — no shell access)
  4. Fill the milestone report

All git operations (branch, commit, push, PR) are handled by the pipeline
in graph.py using git_ops.py. The worker never touches version control.
"""

from __future__ import annotations
import os
import re
import json
from pathlib import Path

from schemas.graph_state import FeatureContext, WorkerResult
from docker.runner import DockerRunner, DockerNotAvailableError, ImageNotBuiltError

ROOT = Path(__file__).parent.parent

_WORKER_SYSTEM = """You are a worker agent implementing a single software feature.

Your job is to write code and fill the milestone report.
You do NOT handle git, branches, commits, or pull requests.
The pipeline handles all version control — focus entirely on implementation.

Rules:
1. file_read codebase_index.md first (if it exists) — it maps everything built so far.
2. file_read doc1_security_contract.md before writing any code.
3. file_read doc4_milestone_report.md — this is the template you will fill.
4. Use list_files and grep to explore areas you must integrate with before writing.
5. Implement ONLY the feature described in your context. No scope creep.
6. Use test_runner to run: install → lint → test → audit after implementation.
7. Write the completed milestone report to reports/{feature_id}_milestone.md.
8. Stop when the milestone report is written. Do not run git. Do not open PRs.

You have five tools:
- file_read:    read any file in the project
- file_write:   write any file in the project (source code, milestone report)
- list_files:   list directory contents to discover what already exists
- grep:         search for patterns across files to find existing code
- test_runner:  run a named test phase inside Docker (install/lint/test/audit)

Security rules (always apply):
- No secrets or tokens in any file you write
- Validate all external inputs at the boundary
- Auth enforced on every protected route before loading data
- Error responses never contain stack traces or internal paths
- security_checklist_followed: true only if every item in doc1 is addressed"""

_TOOLS = [
    {
        "name": "file_read",
        "description": "Read a file from the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "file_write",
        "description": "Write content to a file in the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to project root.",
                },
                "content": {"type": "string", "description": "Full file content."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "List files and directories in the project. "
            "Use this to discover the existing codebase structure before implementing. "
            "Hidden system directories (.git, node_modules, __pycache__) are excluded."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory to list, relative to project root. Defaults to '.' (project root).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "grep",
        "description": (
            "Search for a pattern across project files. "
            "Returns matching lines with file:line references. "
            "Use this to find existing functions, classes, endpoints, or imports before writing new code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The search pattern (substring or regex).",
                },
                "glob": {
                    "type": "string",
                    "description": (
                        "File glob pattern to limit search scope. "
                        "E.g. '**/*.py', '**/*.ts', 'src/**/*.js'. "
                        "Defaults to all text files."
                    ),
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "test_runner",
        "description": (
            "Run a test phase inside the Docker container. "
            "Returns exit code, stdout summary, and any errors. "
            "Available phases: install, lint, test, audit. "
            "Always run all four in order after implementing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": ["install", "lint", "test", "audit"],
                    "description": "Which phase to run.",
                },
                "command": {
                    "type": "string",
                    "description": (
                        "The exact shell command to run for this phase. "
                        "E.g. 'npm install', 'npm run lint', 'npm test', 'npm audit'."
                    ),
                },
            },
            "required": ["phase", "command"],
        },
    },
]


# ---------------------------------------------------------------------------
# Standing rules loader
# ---------------------------------------------------------------------------


def _load_standing_rules(root: Path) -> str:
    """Load CLAUDE.md and .claude/rules/*.md into the system prompt."""
    parts = []
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        parts.append(claude_md.read_text().strip())

    rules_dir = root / ".claude" / "rules"
    if rules_dir.exists():
        for f in sorted(rules_dir.glob("*.md")):
            content = f.read_text().strip()
            # Strip frontmatter — Claude Code directive, not API content
            content = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL).strip()
            if content:
                parts.append(content)

    return "\n\n---\n\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(context: FeatureContext, root: Path = ROOT) -> WorkerResult:
    """
    Run the worker for one feature.
    Returns WorkerResult — the pipeline reads this to decide next steps.
    """
    import urllib.request

    fid = context["feature_id"]

    # Verify Docker (test_runner tool needs it)
    runner = DockerRunner(root=root)
    try:
        runner.verify()
    except DockerNotAvailableError as e:
        return WorkerResult(
            feature_id=fid,
            success=False,
            milestone_report="",
            error=f"Docker not available: {e}",
        )
    except ImageNotBuiltError as e:
        return WorkerResult(
            feature_id=fid,
            success=False,
            milestone_report="",
            error=f"Test image not built: {e}",
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return WorkerResult(
            feature_id=fid,
            success=False,
            milestone_report="",
            error="ANTHROPIC_API_KEY not set in .env",
        )

    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    mem_str = json.dumps(context["memory"], indent=2)

    # Build initial prompt
    retry_note = context.get("retry_note", "")
    retry_section = (
        f"## Previous attempt failed — read this first\n\n{retry_note}\n\n"
        if retry_note
        else ""
    )

    initial_prompt = (
        f"You are implementing feature {fid}: {context['title']}.\n\n"
        f"{retry_section}"
        "## Your feature block\n"
        f"{context['block_text']}\n\n"
        "## Filtered project memory\n"
        f"```json\n{mem_str}\n```\n\n"
        "## Steps\n"
        "0. file_read codebase_index.md — orient yourself (skip gracefully if not found)\n"
        "1. file_read doc1_security_contract.md\n"
        "2. file_read doc4_milestone_report.md\n"
        "3. Use list_files and grep to explore code you must integrate with\n"
        "4. Implement the feature — write source files using file_write\n"
        "5. test_runner phase=install\n"
        "6. test_runner phase=lint\n"
        "7. test_runner phase=test\n"
        "8. test_runner phase=audit\n"
        f"9. file_write reports/{fid}_milestone.md — fill every field\n\n"
        "Do NOT run git commands. Do NOT open PRs. The pipeline handles that.\n"
        "Start with step 0."
    )

    # Build system prompt: base rules + CLAUDE.md + rules files
    # Sent as a cached content block — identical across all 80 turns so only
    # billed at full token cost once per session (subsequent turns hit cache).
    standing_rules = _load_standing_rules(root)
    system = _WORKER_SYSTEM
    if standing_rules:
        system += "\n\n---\n\n" + standing_rules

    messages = [{"role": "user", "content": initial_prompt}]

    # Agentic loop — 80 turns max
    for turn in range(80):
        payload = json.dumps(
            {
                "model": model,
                "max_tokens": 16384,  # generous — complex features need room
                "system": [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "tools": _TOOLS,
                "messages": messages,
            }
        ).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        last_err = ""
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    resp = json.loads(r.read().decode())
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:300]
                if attempt < 3 and e.code in (500, 502, 503, 529):
                    wait = 10 * attempt
                    print(
                        f"  [worker] HTTP {e.code} — retrying in {wait}s (attempt {attempt}/3)"
                    )
                    import time

                    time.sleep(wait)
                    last_err = f"HTTP {e.code}: {body}"
                    continue
                return WorkerResult(
                    feature_id=fid,
                    success=False,
                    milestone_report="",
                    error=f"HTTP {e.code}: {body}",
                )
            except Exception as e:
                if attempt < 3:
                    wait = 10 * attempt
                    print(
                        f"  [worker] {type(e).__name__} — retrying in {wait}s (attempt {attempt}/3)"
                    )
                    import time

                    time.sleep(wait)
                    last_err = str(e)
                    continue
                return WorkerResult(
                    feature_id=fid, success=False, milestone_report="", error=str(e)
                )
        else:
            return WorkerResult(
                feature_id=fid, success=False, milestone_report="", error=last_err
            )

        stop_reason = resp.get("stop_reason")
        content = resp.get("content", [])
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
                feature_id=fid,
                success=False,
                milestone_report="",
                error="Worker finished but milestone report not found in reports/",
            )

        if stop_reason == "tool_use":
            tool_results = []
            for block in content:
                if block.get("type") != "tool_use":
                    continue
                result_str = _execute_tool(block["name"], block["input"], root, runner)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result_str,
                    }
                )
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return WorkerResult(
        feature_id=fid,
        success=False,
        milestone_report="",
        error="Worker exceeded 80 turns without completing",
    )


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------


def _execute_tool(name: str, inp: dict, root: Path, runner: DockerRunner) -> str:
    try:
        if name == "file_read":
            path = root / inp["path"]
            if not path.exists():
                return f"Error: {inp['path']} not found"
            content = path.read_text()
            if len(content) > 6000:
                content = content[:3000] + "\n...[truncated]...\n" + content[-1500:]
            return content

        elif name == "file_write":
            path = root / inp["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(inp["content"])
            return f"Written: {inp['path']} ({len(inp['content'])} chars)"

        elif name == "list_files":
            directory = inp.get("directory", ".")
            target = root / directory
            if not target.exists():
                return f"Error: directory '{directory}' does not exist"
            if not target.is_dir():
                return f"Error: '{directory}' is not a directory"

            _SKIP_DIRS = {
                ".git",
                "node_modules",
                "__pycache__",
                ".pytest_cache",
                "venv",
                ".venv",
                "dist",
                "build",
                ".mypy_cache",
                ".tox",
            }
            lines: list[str] = []

            def _walk(path: Path, prefix: str = "", depth: int = 0) -> None:
                if depth > 5:
                    return
                try:
                    entries = sorted(
                        path.iterdir(), key=lambda p: (p.is_file(), p.name)
                    )
                except PermissionError:
                    return
                for entry in entries:
                    if entry.name in _SKIP_DIRS:
                        continue
                    lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}")
                    if entry.is_dir():
                        _walk(entry, prefix + "  ", depth + 1)

            _walk(target)
            result_str = "\n".join(lines)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + "\n...[truncated]..."
            return result_str or "(empty directory)"

        elif name == "grep":
            import re as _re

            pattern = inp.get("pattern", "")
            glob_pat = inp.get("glob", "**/*")

            _SKIP_DIRS = {
                ".git",
                "node_modules",
                "__pycache__",
                ".pytest_cache",
                "venv",
                ".venv",
                "dist",
                "build",
                ".mypy_cache",
            }

            try:
                compiled = _re.compile(pattern, _re.IGNORECASE)
            except _re.error:
                compiled = _re.compile(_re.escape(pattern), _re.IGNORECASE)

            matches: list[str] = []
            for filepath in sorted(root.glob(glob_pat)):
                if not filepath.is_file():
                    continue
                if any(skip in filepath.parts for skip in _SKIP_DIRS):
                    continue
                try:
                    text = filepath.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if compiled.search(line):
                        rel = filepath.relative_to(root)
                        matches.append(f"{rel}:{i}: {line.rstrip()}")
                if len(matches) >= 150:
                    matches.append(
                        "...[truncated — too many matches, narrow your pattern]..."
                    )
                    break

            if not matches:
                return f"No matches for '{pattern}'"
            result_str = "\n".join(matches)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + "\n...[truncated]..."
            return result_str

        elif name == "test_runner":
            phase = inp.get("phase", "")
            command = inp.get("command", "")
            if not command:
                return f"Error: command is required for test_runner phase={phase}"

            result = runner.run(command)
            output = result.stdout + result.stderr
            if len(output) > 3000:
                output = output[:1500] + "\n...[truncated]...\n" + output[-800:]
            return (
                f"phase: {phase}\n"
                f"command: {command}\n"
                f"exit_code: {result.exit_code}\n"
                f"summary: {result.summary}\n"
                f"output:\n{output}"
            )

        else:
            return f"Error: unknown tool '{name}'"

    except Exception as e:
        return f"Error executing {name}: {e}"
