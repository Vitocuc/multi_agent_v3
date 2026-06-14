# Development assistant — documentation

A pipeline that helps you build software projects. You describe the idea, the system plans it, implements features, and validates them. You stay in control at every key decision point.

**Last updated: 14 June 2026**

---

## Changelog

| Date | Change |
|---|---|
| 14 Jun 2026 | Validator rewritten: generates executable pytest from doc3, runs it against the live app — real exit codes, not LLM opinion |
| 14 Jun 2026 | Added `app_run_command` / `app_port` to the shared plan — CTO decides how to start the app for testing |
| 14 Jun 2026 | Global security checks (SEC-GLOBAL-01/02/03) are now deterministic Python, not LLM-judged |
| 14 Jun 2026 | `docker/runner.py` gains app lifecycle: shared network, `start_app`/`wait_for_app`/`stop_app` |
| 14 Jun 2026 | `Dockerfile.test` adds `pytest` + `requests` for validator-generated tests |
| 3 Jun 2026 | Corrected execution order: validator now runs before human gate, not after |
| 2 Jun 2026 | Separated git operations from worker — workers have zero git access |
| 2 Jun 2026 | Added `git_node` and `merge_node` to LangGraph graph |
| 2 Jun 2026 | Corrected execution order: worker → git → human gate → validator → merge |
| 2 Jun 2026 | Added `gh-check` command for GitHub PR approval detection |
| 2 Jun 2026 | Fixed Gemini 2.5 Flash: disabled extended thinking, added 503/429 retry, added response guard |
| 2 Jun 2026 | Worker tools changed from bash+file to file_read+file_write+test_runner |
| 2 Jun 2026 | Raised worker max_tokens from 4096 to 16384 |
| 2 Jun 2026 | Enforced `develop` as base branch for all PRs; `main` ← `develop` is a human milestone decision |
| 2 Jun 2026 | Docker test runner for CI commands; git runs on host via subprocess |

---

## Table of contents

1. [How it works](#how-it-works)
2. [Repository structure](#repository-structure)
3. [Setup](#setup)
4. [First run — step by step](#first-run)
5. [Commands reference](#commands-reference)
6. [The execution graph](#the-execution-graph)
7. [The six phases](#the-six-phases)
8. [Separation of concerns — who does what](#separation-of-concerns--who-does-what)
9. [Contract files](#contract-files)
10. [Human gates — what requires your input](#human-gates)
11. [Project memory](#project-memory)
12. [Docker environment](#docker-environment)
13. [How the validator works](#how-the-validator-works)
14. [Branch strategy](#branch-strategy)
15. [Model configuration](#model-configuration)
16. [Troubleshooting](#troubleshooting)
17. [File ownership — what you can and cannot edit](#file-ownership--what-you-can-and-cannot-edit)

---

## How it works

The pipeline has three agent roles and one pipeline role.

**Agent roles (AI):**
- **CTO orchestrator** — plans the project, generates contracts, decides which features to run and in what order. Uses Claude or Gemini.
- **Worker agents** — implement one feature each via the Claude API. Tools: `file_read`, `file_write`, `test_runner`. No git access.
- **Validator agents** — generate executable tests from the doc3 spec (Gemini, never sees source code), run them against the live application in Docker, and run deterministic security checks on the milestone report. Never touch git.

**Pipeline role (Python, no AI):**
- **git_ops.py** — owns all version control: branch setup, commit, push, PR creation, merge. Called by `git_node` and `merge_node` in the graph. Workers and validators have zero git access.

**Three principles:**
- Planning is slow and careful. The CTO asks clarifying questions before producing anything.
- Implementation is code-focused and git-free. Workers write files and test them. The pipeline handles version control.
- Validation is independent. A different model validates against a spec written before implementation began. It never reads code.

**You interact with the system at five points only:**
1. Filling in `doc0_project_brief.md`
2. Answering CTO clarifying questions in the terminal
3. Approving or rejecting gates (plan, contracts)
4. Selecting which features to implement
5. Reviewing and approving the PR on GitHub

Everything else is automatic.

---

## Repository structure

```
your-project/
│
│  ── Entry points ──────────────────────────────────────────────
├── run.py                     The only command you type
├── graph.py                   LangGraph StateGraph (all nodes + edges)
├── feature_menu.py            CLI feature selector (called by graph)
├── git_ops.py                 All git/GitHub operations (no AI, pure Python)
│
│  ── Schemas ────────────────────────────────────────────────────
├── schemas/
│   ├── graph_state.py         TypedDict flowing between LangGraph nodes
│   ├── pipeline_state.py      Persistent Pydantic state → project_state.json
│   └── cto_outputs.py         Typed outputs for every CTO model call
│
│  ── LLM layer ──────────────────────────────────────────────────
├── llm/
│   ├── router.py              Model-agnostic caller (Claude + Gemini)
│   └── retry.py               Structured output with auto-correction + retry
│
│  ── Agents ─────────────────────────────────────────────────────
├── agents/
│   ├── cto.py                 CTO: clarify, plan, contracts, spawn plan
│   ├── worker.py              Worker: file_read / file_write / test_runner only
│   └── validator.py           Validator: Gemini against doc3 — no git
│
│  ── Infrastructure ─────────────────────────────────────────────
├── memory/
│   └── store.py               Append-only project memory (memory.json)
├── gates/
│   └── state_store.py         Atomic read/write of project_state.json
├── docker/
│   └── runner.py              Runs test commands inside the Docker container
│
│  ── Contract documents ─────────────────────────────────────────
├── doc0_project_brief.md      YOU fill this in before starting
├── doc1_security_contract.md  Template → CTO fills at runtime
├── doc2_features_contract.md  Template → CTO fills at runtime
├── doc3_validation_contract.md Template → CTO fills at runtime
├── doc4_milestone_report.md   Template → worker copies per feature
│
│  ── Worker instructions ────────────────────────────────────────
├── CLAUDE.md                  Standing instructions for the worker agent
├── .claude/rules/
│   ├── security.md            Security implementation rules
│   ├── git.md                 Branch strategy and PR checklist
│   └── milestone-report.md   How to fill doc4 correctly
│
│  ── Runtime files (auto-generated, do not edit) ────────────────
├── project_state.json         Persistent execution state
├── memory.json                Accumulated project memory
├── checkpoints.db             LangGraph checkpoints (SQLite)
├── reports/                   Milestone reports filed by workers
│   └── F-01-001_milestone.md
├── validation/                Validator-generated pytest files (commit these)
│   └── F-01-001_test.py
│
│  ── Docker ─────────────────────────────────────────────────────
├── Dockerfile.test            Test runner image (Node 20 + Python 3 + pytest + requests)
│
│  ── Config ─────────────────────────────────────────────────────
├── requirements.txt           Python dependencies
├── .env.example               Copy to .env and fill in keys
└── .gitignore
```

---

## Setup

**Prerequisites:** Python 3.11+, Docker Desktop (or Docker Engine), `git`, `gh` CLI authenticated to GitHub.

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Set up environment variables
cp .env.example .env
# Open .env and fill in:
#   ANTHROPIC_API_KEY  — from console.anthropic.com
#   GEMINI_API_KEY     — from aistudio.google.com
#   GITHUB_TOKEN       — from github.com/settings/tokens (needs repo + workflow scope)

# 3. Build the Docker test image (once per machine)
python run.py docker-build
```

The Docker build takes 2–4 minutes the first time. It installs Node 20, npm, Python 3, pip-audit, and the GitHub CLI. The `GITHUB_TOKEN` is forwarded into the container when the pipeline opens PRs — it is never written to any file.

---

## First run

### Step 1 — fill in doc0

Open `doc0_project_brief.md` and fill in every section. You don't need to be exhaustive — the CTO will ask follow-up questions. The more specific you are, the fewer rounds it takes.

Key fields:
- **What we are building** — 3–10 sentences: the product, who uses it, the problem it solves
- **Tech stack** — list what you know; leave rows blank if undecided
- **Hard constraints** — things that cannot change (compliance, deadlines, existing systems)
- **Non-goals** — what this project explicitly will not do

Do not touch `Clarification log` or `Shared plan` — the CTO manages those.

### Step 2 — start the pipeline

```bash
python run.py start
```

The CTO reads your brief and asks clarifying questions one at a time. Answer in the terminal.

```
CTO (round 1):
What authentication mechanism do you want to use — JWT, session-based,
or a third-party provider like Auth0?

Your answer (Enter to skip): JWT with 15 minute expiry and refresh tokens
```

Type `skip` or press Enter to move past a question. The CTO flags it as an open assumption.

### Step 3 — approve the plan

When the CTO has enough information it writes a shared plan and pauses:

```
── Gate: plan_approval ────────────────────────────────

Plan ready.

Summary: A REST API for task management using Node/Express with JWT auth ...
First milestone: users can register, log in, and create tasks.

Review doc0_project_brief.md then run:
  python run.py resume --decision approve
```

The shared plan now also includes `app_run_command` and `app_port` — the exact
command and port the CTO decided the application will use (e.g. `npm run dev`
on port `3000`). **Check these carefully** — the validator runs this command
verbatim in Docker to start the app and test it. If it's wrong for your stack,
reject with a note.

```bash
python run.py resume --decision approve
# or
python run.py resume --decision reject --note "auth should use sessions not JWT"
# or
python run.py resume --decision reject --note "app_run_command should be 'python manage.py runserver 0.0.0.0:8000'"
```

### Step 4 — approve the contracts

After plan approval the CTO generates doc1, doc2, doc3 automatically and pauses again:

```
── Gate: contract_approval ────────────────────────────

8 features across 2 milestones.
Review doc1, doc2, doc3 then:
  python run.py resume --decision approve
```

Read all three files carefully. This is the most important gate — everything downstream depends on contract quality.

```bash
python run.py resume --decision approve
```

### Step 5 — select features

The feature menu appears:

```
── Feature selection ──────────────────────────

  M-01
    [F-01-001] User registration    high
    [F-01-002] User login           high
    [F-01-003] Password reset       medium  → needs F-01-001

  M-02
    [F-02-001] User profile         medium  → needs F-01-002

  Commands:
    all                    run all features
    M-01                   run all features in a milestone
    F-01-001               run a specific feature
    F-01-001,F-01-002      comma-separated list
    skip F-01-003 all      all except specified

  Your selection:
```

Select what to implement. The CTO decides which features run in parallel based on the dependency graph.

### Step 6 — workers implement, git commits, you review

For each feature the pipeline:

1. **Sets up a git branch** from `develop` (`git_ops.py`, no AI)
2. **Worker implements** — writes source files, runs tests via Docker, fills milestone report (no git access)
3. **Pipeline commits and pushes** all files the worker wrote (`git_ops.py`)
4. **Pipeline opens a PR** targeting `develop` with the milestone report as the PR body
5. **Validator runs** — generates a pytest file from doc3, starts the app in Docker, runs the tests against it for real, and runs deterministic security checks on the milestone report
6. **If validation passes — pipeline pauses** for your PR review
7. **If validation fails — pipeline routes back to the worker** — you never see the PR

```
── Gate: pr_review ────────────────────────────

[F-01-001] User registration passed validation.
PR: https://github.com/you/repo/pull/12

The code passed all spec tests. Now review the diff on GitHub.
Approve the PR there, then run:
  python run.py gh-check F-01-001
  python run.py resume --decision approve
```

Go to GitHub. Review the diff. If it looks good, approve the PR there, then run:

```bash
python run.py gh-check F-01-001   # detects your GitHub approval
python run.py resume --decision approve
```

### Step 7 — validator runs, PR merges

The validator already ran before this gate (Step 6.5). To recap what happened:

1. **Validator** read only the doc3 test suite, generated a pytest file from it (Gemini — never sees source code), started the app in Docker with `app_run_command`, and ran the generated tests against it for real
2. Each doc3 `test_id` got a real PASSED/FAILED/ERROR/SKIPPED result from pytest — not an LLM opinion
3. The three global security checks ran as pure Python against the milestone report
4. `overall: pass` only because every blocking test_id actually passed and the security checks were clean

After your PR approval:

5. Pipeline **merges the PR** into `develop` automatically
6. Memory is updated with what the worker discovered
7. Next unblocked features become ready

### Step 8 — repeat or complete

The pipeline loops back to the feature selection phase. Select the next batch or end the session.

---

## Commands reference

```bash
# One-time setup
python run.py docker-build

# Begin a new project
python run.py start

# Continue after any gate or interruption
python run.py resume
python run.py resume --decision approve
python run.py resume --decision reject --note "your note here"

# Detect GitHub PR approval and update pipeline state
python run.py gh-check F-01-001

# Check project state at any time
python run.py status

# Inspect project memory
python run.py memory
python run.py memory F-01-002
```

`gh-check` polls GitHub for the PR associated with a feature ID. If the PR is approved or merged, it writes `human_gate: approved` into the milestone report and marks the feature ready for validation. Run it after you approve the PR on GitHub, then run `resume`.

---

## The execution graph

The LangGraph graph has six nodes. Execution order per feature:

```
cto_orchestrator
      │
      ├── worker_node        (Claude API: file_read / file_write / test_runner)
      │        │
      │   git_node           (Python: commit, push, gh pr create)
      │        │
      │   validator_node     (Gemini: generates pytest from doc3, runs it
      │        │               against the live app in Docker — real results)
      │        │
      │   human_gate         (PAUSE — you review code that already passed spec)
      │        │
      │   merge_node         (Python: gh pr merge into develop)
      │        │
      └── cto_orchestrator   (loop: unlock next features, or complete)
```

Validator runs before human review by design — you only spend time reviewing code that already passed real, executed tests. If validation fails, the pipeline routes back to the worker without ever showing you the PR.

Nodes that run AI: `cto_orchestrator`, `worker_node`, `validator_node` (code generation only — the test execution itself is Python + Docker, not AI).
Nodes that run Python only: `git_node`, `merge_node`, `human_gate`.

The graph is checkpointed to `checkpoints.db` after every node. A crash or `Ctrl+C` at any point is safe — `python run.py resume` continues from the last completed node.

---

## The six phases

`project_state.json` always shows the current phase.

| Phase | What happens | Who acts | Gate? |
|---|---|---|---|
| `clarification` | CTO asks one question per round | CTO + you | No |
| `plan_review` | CTO writes shared plan | You | **Yes** |
| `contract_gen` | CTO generates doc1, doc2, doc3 | CTO | No |
| `contract_review` | You read all three contracts | You | **Yes** |
| `feature_selection` | You choose features; CTO builds spawn plan | You + CTO | Interactive |
| `implementation` | worker → git → gate → validator → merge | All nodes | Per PR |
| `complete` | All selected features passed and merged | — | No |

---

## Separation of concerns — who does what

This is the most important design principle. Every role has strict boundaries.

| Role | Reads | Writes | Git access |
|---|---|---|---|
| **CTO** (Claude/Gemini) | doc0, doc1–3 templates, memory.json | doc0 clarification log, doc1, doc2, doc3 | None |
| **Worker** (Claude API) | doc1, doc2 feature block, doc4 template, memory | Source files, `reports/{fid}_milestone.md` | **None** |
| **Validator** (Gemini + Python) | doc3 test suite **only** (never source code) | `validation/{fid}_test.py`, validator_result in milestone report | **None** |
| **git_node** (Python) | Source files on disk | git history, GitHub PR | **Full** |
| **merge_node** (Python) | validator_result from milestone report | git history (merge) | **Full** |
| **You** | Everything | doc0, .env, CLAUDE.md, rules | Full |

Workers cannot lie about opening a PR — the PR is opened by `git_node` reading the actual files on disk. The validator cannot be influenced by the implementation — Gemini only ever sees the doc3 spec, and the pass/fail comes from a real pytest exit code against the running app, not from reading the worker's claims. These are structural guarantees, not prompt-level instructions.

The validator does briefly run a Docker container (the application under test) — this is execution, not git, and the container is removed immediately after the test run regardless of outcome.

---

## Contract files

The three contracts start as templates in the repo. The CTO fills them in at runtime. After generation they should be committed to git.

**doc1 — security contract.** Threat model, authentication mechanism, data sensitivity, PII fields, compliance requirements, rate limiting, audit events, security checklist. Workers must read this before touching any code. The validator's deterministic checks read the checklist status from every milestone report.

**doc2 — features contract.** One block per feature with: ID (F-MM-NNN), title, milestone, priority, complexity, `depends_on` list, acceptance criteria (Given/When/Then), security constraint references into doc1, branch name. The CTO uses this to build worker contexts, the feature menu, and the DAG execution plan.

**doc3 — validation contract.** One test suite per feature. Each test case has: ID, type (`unit`/`integration`/`security`/`regression`), `blocking` flag, plain-language description, and **interface-level** given/when/expected — concrete HTTP method, path, request body, expected status and response shape. Specific enough that someone who has never seen the implementation can write a test from it. `verified_via: executable_test` for feature-specific cases — the validator compiles these into a real pytest file and runs it against the live application. The three global security tests (SEC-GLOBAL-01/02/03) keep `verified_via: milestone_report.*` and are checked by deterministic Python, not compiled into tests.

**doc4 — milestone report template.** The worker copies this to `reports/{feature_id}_milestone.md` and fills every field: what was implemented, what was left undone, every test phase run with exit code, issues discovered, security checklist status. The validator's deterministic security checks (SEC-GLOBAL-01/02/03) read this report; the feature-specific tests run against the live application instead.

---

## Human gates

Gates are deliberate pauses. The graph writes to `project_state.json` and stops. You resume with `python run.py resume`.

**Plan approval.** CTO has finished clarifying and written the shared plan into doc0. You read it and approve or reject with a note. Rejection triggers a revision.

**Contract approval.** CTO has generated doc1, doc2, doc3. You read all three. This is the highest-leverage gate — approve only when the acceptance criteria are specific enough to be testable and the security contract reflects your actual threat model.

**PR review.** The validator has already run and passed before you see this gate — it generated real tests from doc3, ran them against a live instance of the application in Docker, and got real pass/fail results. The pipeline committed the worker's code, pushed, opened the PR, ran validation — and only then pauses for your review. You review code that already passed executable tests. After approving on GitHub, run `gh-check` then `resume` to trigger the merge.

If validation fails, the pipeline routes back to the worker and you never see the PR — saving you from reviewing code that would not pass anyway.

**Security escalation.** The validator found `security_checklist_followed: false` or a security test failed. You acknowledge before the pipeline continues.

The graph is resumable indefinitely. You can stop and come back days later — `resume` continues from the exact node where it paused.

---

## Project memory

`memory.json` grows as features complete. It is append-only — nothing is ever deleted.

**architecture_decisions** — technical choices with rationale (e.g. "chose JWT over sessions — required by sec contract §2.1"). Injected into worker contexts for features in the dependency chain.

**failed_approaches** — approaches that didn't work (e.g. "passport-local conflicts with express-session v2 — downgraded to v1.17.3"). Every worker sees all failed approaches regardless of which feature they came from. This is the most valuable section — it prevents workers repeating the same mistakes.

**discovered_constraints** — real-world limits found during implementation not in the contracts (e.g. "host does not support websockets — use SSE"). Injected into contexts of affected features.

**open_risks** — unresolved high/critical issues. Always injected into every worker context.

```bash
python run.py memory              # full memory
python run.py memory F-01-002    # filtered for this feature
```

---

## Docker environment

The test image (`dev-assistant-test`) serves three purposes: the worker's `test_runner` tool (install/lint/test/audit), running the application under test, and running the validator's generated pytest files. The project directory is mounted at `/project` in every container.

The image includes: Node 20, npm, Python 3, `pip-audit`, `pytest`, `requests`, GitHub CLI.

Git commands (branch, commit, push) run on the **host machine** via `git_ops.py` — they never go through Docker.

**The shared network — `dev-assistant-net`.** When the validator runs, it creates this Docker network (idempotent — created once, reused after). The application container and the test-execution container both attach to it, so the test container can reach the app container by name (e.g. `http://app-f-01-001:3000`) via Docker's built-in DNS.

**Worker test_runner** (`network=None`, i.e. `--network host`): used for `npm install`, `npm test`, `pip-audit`, etc. — needs internet access for package registries.

**App container** (`app-{feature_id}`): started by the validator with `app_run_command` from doc0, on `dev-assistant-net`. Not `--rm` — if it crashes, `docker logs` is still readable for diagnostics. Removed explicitly after the validator run.

**Test-execution container**: runs `pytest validation/{fid}_test.py -v` on `dev-assistant-net`, reaching the app container by its container name.

**Rebuild the image** if you update `Dockerfile.test`:
```bash
python run.py docker-build
```

**Use a custom image name:**
```
TEST_IMAGE=my-project-test  # in .env
```

**Debug test commands manually** in the same environment the worker uses:
```bash
docker run --rm -it -v $(pwd):/project -w /project dev-assistant-test bash
```

**Debug a generated test against a running app manually:**
```bash
# Start the app on the shared network
docker network create dev-assistant-net 2>/dev/null
docker run -d --name app-debug --network dev-assistant-net \
  -v $(pwd):/project -w /project dev-assistant-test \
  bash -c "npm run dev"

# Run the generated test against it
docker run --rm --network dev-assistant-net \
  -v $(pwd):/project -w /project dev-assistant-test \
  python3 -m pytest validation/F-01-001_test.py -v

# Clean up
docker rm -f app-debug
```

---

## How the validator works

Three steps, in order, for every feature:

**1. Generate.** The validator extracts the doc3 test suite for this feature — `given`/`when`/`expected` written at the HTTP interface level — and sends it to Gemini with a strict instruction: write a pytest file using `requests`, one function per `test_id`, named `test_<id_with_underscores>`. Gemini never sees the implementation. If the generated code has a syntax error or is missing a required function, the validator sends a correction prompt and retries (up to 3 attempts). The generated file is saved to `validation/{feature_id}_test.py` — committed to git as part of the audit trail.

**2. Run.** The validator starts the application in a Docker container using `app_run_command`/`app_port` from doc0, on the shared `dev-assistant-net` network. It polls (`docker exec ... curl`) until the app responds — any HTTP response counts as ready, including 404s. If the app doesn't come up within 60 seconds, every test for this feature is marked failed with the container logs attached as the reason. Once ready, `pytest validation/{feature_id}_test.py -v` runs in a sibling container on the same network. The app container is removed afterward regardless of outcome.

**3. Score.** Each doc3 `test_id` maps to an expected pytest function name (`F-01-001-T01` → `test_F_01_001_T01`). The validator searches the real pytest output for `::test_F_01_001_T01 PASSED|FAILED|ERROR|SKIPPED` and records the actual result. In parallel, three deterministic checks run against the milestone report — no LLM involved:

| Check | What it verifies |
|---|---|
| SEC-GLOBAL-01 | No secrets/tokens/passwords appear in any `commands_run` summary |
| SEC-GLOBAL-02 | `security_checklist_followed: true` in the milestone report |
| SEC-GLOBAL-03 | The audit command (`npm audit`/`pip-audit`) exited 0 with no high/critical findings |

`overall: pass` requires every **blocking** `test_id` to have actually passed in pytest, AND all three SEC-GLOBAL checks to pass. A failing non-blocking test or a `SKIPPED` result doesn't block the merge but appears in the milestone report for visibility.

---

## Branch strategy

All feature branches are cut from `develop`, not `main`.

```
main        ← stable releases only (human decision after milestone)
  └── develop   ← integration branch; all PRs target this
        └── feature/F-01-001-user-login    ← created by git_ops.py
        └── feature/F-01-002-user-auth     ← created by git_ops.py
```

The pipeline creates feature branches automatically during `feature_selection` phase. Workers never touch git. After validation passes, `merge_node` squash-merges the feature branch into `develop` and deletes the branch.

The `develop` → `main` merge is always a human decision made after a full milestone completes. The pipeline never touches `main`.

---

## Model configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Claude API — CTO and worker |
| `GEMINI_API_KEY` | required | Gemini API — validator |
| `GITHUB_TOKEN` | required | GitHub CLI — PR creation and merge |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Model for CTO and workers |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model for validators |
| `CTO_MODEL` | `claude` | Provider for CTO phase (`claude` or `gemini`) |
| `VALIDATOR_MODEL` | `gemini` | Provider for validation (`claude` or `gemini`) |
| `TEST_IMAGE` | `dev-assistant-test` | Docker test image name |

**Gemini 2.5 Flash specifics.** The router always passes `thinkingBudget: 0` to disable extended thinking for structured outputs, sets `maxOutputTokens: 8192` minimum, retries on 429/503 with 15s × attempt backoff (5 attempts), and guards against truncated responses. These are not optional — Gemini 2.5 Flash silently consumes its token budget on internal reasoning before writing the response, which causes truncation without these mitigations. The same settings apply to the validator's test-code generation calls.

The validator uses a different provider than the worker for code generation. But the actual pass/fail no longer depends on either model's judgment — it comes from a real pytest exit code against a running instance of the application, plus deterministic Python checks on the milestone report. The model's only job is translating a spec into test code.

---

## Troubleshooting

**"Docker daemon is not running"**
Start Docker Desktop (Mac/Windows) or `sudo systemctl start docker` (Linux).

**"Test image not found"**
Run `python run.py docker-build` first.

**"No checkpoint found. Run start first."**
`checkpoints.db` is missing or corrupt. Run `python run.py start`.

**Worker exceeded 40 turns**
The feature was too complex for one session. Read `reports/{feature_id}_milestone.md` to see what was partially done. Split the feature in doc2 into smaller pieces, then requeue.

**"git push failed"**
The `git_node` couldn't push. Most common cause: the remote branch already exists with diverged history. Delete the remote branch manually (`git push origin --delete branch-name`) then run `resume`.

**"PR open failed"**
`GITHUB_TOKEN` is not set or lacks repo scope. Check `.env`, regenerate the token if needed. The PR can be opened manually on GitHub — the pipeline will continue when you run `gh-check`.

**`gh-check` returns "no PR found"**
The worker may not have filed the milestone report correctly, so `git_node` may not have opened the PR. Check `reports/` for the milestone file and check GitHub for a PR with the feature ID in the title. If missing, the feature can be requeued.

**"App did not become ready"**
The validator started the app with `app_run_command` but it never responded within 60 seconds. The milestone report's `validator_result.note` includes the container's last logs. Common causes: `app_run_command` is wrong for this stack (fix via plan rejection before contracts are generated, or manually correct `app_run_command`/`app_port` in doc0 and requeue), the app needs an env var that isn't set (add it to `.env` and to the `APP_`/`PORT`-prefixed allowlist in `docker/runner.py._safe_env` if needed), or the app takes longer than 60s to start (increase `APP_READY_TIMEOUT` in `docker/runner.py`).

**"Generated test function not found in pytest output"**
Gemini's generated `validation/{feature_id}_test.py` doesn't define a function named `test_<test_id_with_underscores>` matching a doc3 test_id, even after 3 correction attempts. Open the generated file — usually the spec in doc3 was too vague for a function-per-test_id mapping. Tighten the `given`/`when`/`expected` wording in doc3 to be more concrete (exact HTTP method/path/body), then requeue.

**Validator always fails**
Two possible causes. (1) The generated tests are failing for real — open `validation/{feature_id}_test.py` and the milestone report's `validator_result.note` to see which `test_id`s failed and why; this usually means the implementation doesn't match the doc3 spec, or the spec itself was ambiguous. (2) `app_run_command` doesn't actually start the app — see "App did not become ready" above. Either way, the failure reasons in `validator_result.failures` and `.results` point at specific `test_id`s, not a vague "fail".

**CTO contracts are missing a feature**
Run `python run.py resume --decision reject --note "F-01-003 missing from doc2"`. The CTO regenerates all three contracts.

**Pipeline crashed mid-feature**
Run `python run.py resume`. LangGraph resumes from the last completed node. If it crashed during `git_node`, the branch may be in a partial state — check `git status` and clean up if needed before resuming.

**Want to restart from scratch**
```bash
rm -rf project_state.json checkpoints.db memory.json validation/
git checkout doc1_security_contract.md doc2_features_contract.md doc3_validation_contract.md
python run.py start
```

---

## File ownership — what you can and cannot edit

| File | Owner | Notes |
|---|---|---|
| `doc0_project_brief.md` | You | Fill it in before starting. Clarification log and shared plan are CTO-managed. |
| `doc1_security_contract.md` | CTO | Read it. Request changes via gate rejection. |
| `doc2_features_contract.md` | CTO | Read it. Request changes via gate rejection. Manual edits possible but keep doc3 consistent. |
| `doc3_validation_contract.md` | CTO | Read it. If you edit doc2, update matching suites here too. |
| `doc4_milestone_report.md` | Template | Never edit directly — workers copy it per feature. |
| `reports/*.md` | Workers + pipeline | Workers write the report body; pipeline writes `validator_result`. Read-only for you. |
| `validation/*_test.py` | Validator | Generated pytest files. Read-only for you — useful for debugging a failed validation. Commit to git as audit trail. |
| `memory.json` | Pipeline | Never edit — append-only, managed after each milestone. |
| `project_state.json` | Pipeline | Never edit — managed by `gates/state_store.py`. |
| `checkpoints.db` | LangGraph | Never edit. |
| `CLAUDE.md` | You | Adjust worker standing instructions. Changes take effect immediately on the next worker invocation. |
| `.claude/rules/*.md` | You | Adjust implementation rules. Loaded by both Claude Code (automatic) and the API worker (injected). |
| `git_ops.py` | Pipeline | Do not edit unless you understand the execution graph. |
| `graph.py` | Pipeline | Do not edit unless you understand LangGraph. |
| `Dockerfile.test` | You | Add tools your project needs. Rebuild with `python run.py docker-build`. |
| `.env` | You | Never commit. Add to `.gitignore` if not already there. |
| `run.py` | Pipeline | Entry point. Edit only if adding new top-level commands. |
