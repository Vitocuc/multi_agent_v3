# Multi-agent pipeline architecture

This document describes how the pipeline agents interact and how each worker
sees the evolving codebase. Read it before modifying any pipeline component.

---

## Agent roles

| Agent | Tools | Git access | Writes code | Writes to disk |
|---|---|---|---|---|
| **CTO orchestrator** | LLM (Claude or Gemini) | No | No | Contracts, memory |
| **Worker** | file_read, file_write, list_files, grep, test_runner | No | Yes | Source files, milestone report |
| **Validator** | LLM (Gemini) | No | No | Reads milestone report only |
| **git_node** | subprocess (git, gh) | Yes | No | Branch, commit, push, PR |
| **merge_node** | subprocess (gh) | Yes | No | Merges PR, updates codebase_index.md |

No agent except `git_node` and `merge_node` touches version control.
No agent except `worker` writes application source files.

---

## Execution order per feature

```
worker → git_node → validator → human_gate → merge_node → cto_orchestrator
```

1. **worker** — reads contracts + codebase_index.md, writes code, files milestone report
2. **git_node** — commits all files the worker wrote, pushes, opens PR
3. **validator** — reads milestone report against doc3, runs generated tests
4. **human_gate** — pipeline pauses; human reviews PR on GitHub and approves
5. **merge_node** — merges PR into `develop`, regenerates `codebase_index.md`
6. **cto_orchestrator** — picks next feature

Validator runs *before* the human gate. You only review code that already passed
the spec — if it fails validation it goes back to the worker, not to you.

---

## How workers see the codebase

### The problem

Each worker is a fresh LLM session with no memory of previous workers.
It starts knowing only what's in its system prompt and initial prompt.
Without discovery tools it can only read files whose paths it already knows —
meaning it would duplicate code or write conflicting implementations.

### The solution: two layers

**Layer 1 — `codebase_index.md` (coarse map)**

After every successful merge, `merge_node` calls `_generate_codebase_index()`
in `graph.py`. This writes `codebase_index.md` at the project root containing:

- Full directory tree (depth 4, skipping build artifacts)
- Top-level function and class definitions for every source file

Workers read this as step 0 of their session. It tells them what exists and
where without requiring them to know paths in advance.

**Layer 2 — `list_files` and `grep` (fine navigation)**

Workers have two discovery tools:

- `list_files(directory)` — lists a directory subtree (depth 5, skips `.git`,
  `node_modules`, `__pycache__`, etc.)
- `grep(pattern, glob)` — searches for a pattern across files, returns
  `file:line: content` matches (up to 150 hits)

These let a worker navigate from the coarse map to the exact code it needs
to integrate with before writing anything.

### Reading order for workers

```
0. file_read codebase_index.md        ← what's already built
1. file_read doc1_security_contract.md
2. file_read doc4_milestone_report.md
3. list_files / grep                  ← explore integration points
4. implement
5. test_runner x4
6. file_write milestone report
```

---

## codebase_index.md lifecycle

| Event | Effect on codebase_index.md |
|---|---|
| First worker runs | File does not exist — worker skips step 0 |
| First merge completes | File is created by merge_node |
| Each subsequent merge | File is overwritten with the current state |
| Worker session starts | Worker reads it (or skips if missing) |
| Worker writes code | Worker must NOT modify codebase_index.md |

The file is always a snapshot of the codebase *after the last merged feature*.
Workers on parallel branches may see a slightly stale index — they should use
`grep` to verify assumptions before relying on it.

---

## System prompt and token caching

The worker calls the Anthropic API directly (not through Claude Code CLI).
The system prompt is assembled in `agents/worker.py` by `_load_standing_rules()`,
which reads `CLAUDE.md` and every file in `.claude/rules/*.md` from disk and
concatenates them into the `system` field before each API call.

To avoid re-paying full token cost on every turn of the 40-turn agentic loop,
the system prompt is sent as a cached content block:

```python
"system": [{"type": "text", "text": system,
            "cache_control": {"type": "ephemeral"}}]
```

Anthropic caches it after the first call; subsequent turns within 5 minutes
pay ~10% of the original token cost. The `messages` list (which grows each
turn) is not cached — only the static system prompt qualifies.

---

## Adding new tools to the worker

All worker tools are defined in `agents/worker.py`:

- `_TOOLS` — JSON schema definitions sent to the Claude API
- `_execute_tool()` — Python implementation of each tool
- `_WORKER_SYSTEM` — system prompt (list tools here when adding)
- `initial_prompt` — step list (add discovery steps here)

When adding a tool: update all four locations, then update CLAUDE.md reading
order and this doc.

Do not give workers git tools. All version control is pipeline-owned.

---

## Failure handling

If the worker fails: `worker_results[fid]["success"] == False`.
`git_node`, `validator`, and `merge_node` all short-circuit on worker failure.
`cto_orchestrator` routes back to the worker with a `retry_note` in the context.

If `merge_node` merge fails (e.g. GitHub checks still running): the pipeline
prints a warning and asks for manual merge. `codebase_index.md` is only updated
on a successful `gh pr merge` — a failed merge leaves the previous index intact.
