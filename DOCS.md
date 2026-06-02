# Development assistant — documentation

A pipeline that helps you build software projects. You describe the idea, the system plans it, implements features, and validates them. You stay in control at every key decision point.

---

## Table of contents

1. [How it works](#how-it-works)
2. [Repository structure](#repository-structure)
3. [Setup](#setup)
4. [First run — step by step](#first-run)
5. [Commands reference](#commands-reference)
6. [The five phases](#the-five-phases)
7. [Contract files](#contract-files)
8. [Human gates — what requires your input](#human-gates)
9. [Project memory](#project-memory)
10. [Docker environment](#docker-environment)
11. [Model configuration](#model-configuration)
12. [Troubleshooting](#troubleshooting)
13. [File ownership — what you can and cannot edit](#file-ownership)

---

## How it works

The pipeline has three roles and three principles.

**Roles:**
- **CTO orchestrator** — plans the project, generates contracts, decides which features to run and in what order. Uses Claude (or Gemini).
- **Worker agents** — implement one feature each via the Claude API with tool use (bash + file read/write). Run inside Docker.
- **Validator agents** — validate each feature against the validation contract using Gemini. Never read source code — only the milestone report.

**Three principles:**
- Planning is slow and careful. The CTO asks clarifying questions before producing anything.
- Implementation is code-focused. Workers receive precise contracts and filtered project memory.
- Validation is independent. A different model validates against a spec written before implementation began.

**You interact with the system at four points only:**
1. Filling in `doc0_project_brief.md` (your project description)
2. Answering CTO clarifying questions in the terminal
3. Approving or rejecting gates (plan, contracts, PRs)
4. Selecting which features to implement

Everything else — contract generation, worker spawning, validation, memory extraction, DAG scheduling — is automatic.

---

## Repository structure

```
your-project/
│
│  ── Entry points ──────────────────────────────────────────────
├── run.py                     The only command you type
├── graph.py                   LangGraph StateGraph (nodes + edges)
├── feature_menu.py            CLI feature selector (used inside graph)
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
│   ├── worker.py              Worker: Claude API with bash/file tools
│   └── validator.py           Validator: Gemini against doc3 test suite
│
│  ── Infrastructure ─────────────────────────────────────────────
├── memory/
│   └── store.py               Append-only project memory (memory.json)
├── gates/
│   └── state_store.py         Atomic read/write of project_state.json
├── docker/
│   └── runner.py              Runs bash commands inside the test container
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
│   ├── git.md                 Git and PR discipline
│   └── milestone-report.md   How to fill doc4 correctly
│
│  ── Runtime files (auto-generated, do not edit) ────────────────
├── project_state.json         Persistent execution state
├── memory.json                Accumulated project memory
├── checkpoints.db             LangGraph checkpoints (SQLite)
├── reports/                   Milestone reports filed by workers
│   └── F-01-001_milestone.md
│
│  ── Docker ─────────────────────────────────────────────────────
├── Dockerfile.test            Test runner image definition
│
│  ── Config ─────────────────────────────────────────────────────
├── requirements.txt           Python dependencies
├── .env.example               Copy to .env and fill in keys
└── .gitignore
```

---

## Setup

**Prerequisites:** Python 3.11+, Docker Desktop (or Docker Engine), `git`, `gh` CLI.

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Set up environment variables
cp .env.example .env
# Open .env and fill in:
#   ANTHROPIC_API_KEY   — from console.anthropic.com
#   GEMINI_API_KEY      — from aistudio.google.com
#   GITHUB_TOKEN        — from github.com/settings/tokens (needs repo scope)

# 3. Build the Docker test image (once per machine)
python run.py docker-build
```

The Docker build takes 2-4 minutes the first time. It installs Node 20, Python 3, pip-audit, and the GitHub CLI inside the image.

---

## First run

### Step 1 — fill in doc0

Open `doc0_project_brief.md` and fill in every section. You don't need to be exhaustive — the CTO will ask follow-up questions. But the more specific you are, the fewer rounds it takes.

The important fields are:
- **What we are building** — 3-10 sentences describing the product, who uses it, and the core problem it solves
- **Tech stack** — list what you know; leave rows blank if undecided
- **Hard constraints** — things that cannot change (compliance, deadlines, existing systems)
- **Non-goals** — what this project explicitly will not do

Do not touch the `Clarification log` or `Shared plan` sections — the CTO manages those.

### Step 2 — start the pipeline

```bash
python run.py start
```

The CTO reads your brief and begins asking clarifying questions. One question per round. Answer directly in the terminal.

```
CTO (round 1):
What authentication mechanism do you want to use — JWT, session-based, or a
third-party provider like Auth0?

Your answer (Enter to skip): JWT with 15 minute expiry and refresh tokens
```

Type `skip` if you want to move past a question. The CTO will flag it as an open assumption.

### Step 3 — approve the plan

When the CTO has enough information it writes a shared plan to `doc0_project_brief.md` and pauses:

```
── Gate: plan_approval ────────────────────────────────

Plan ready.

Summary: A REST API for task management using Node/Express with JWT auth,
PostgreSQL for storage, and Docker for deployment. Security posture: PII
limited to email and name, GDPR-compliant, no financial data.

First milestone: users can register, log in, and create tasks.

Review doc0_project_brief.md then run:
  python run.py resume --decision approve
```

Read the plan. If it looks right:
```bash
python run.py resume --decision approve
```

If something needs changing:
```bash
python run.py resume --decision reject --note "auth should use sessions not JWT"
```

The CTO revises and presents the plan again.

### Step 4 — approve the contracts

After plan approval the CTO generates three contract files automatically and pauses again:

```
── Gate: contract_approval ────────────────────────────

Contracts generated: 8 features across 2 milestones.

Review doc1, doc2, and doc3 before approving.
Ready features: ['F-01-001', 'F-01-002']
```

Open and read the three files:
- `doc1_security_contract.md` — threat model, auth spec, security checklist
- `doc2_features_contract.md` — feature blocks with acceptance criteria
- `doc3_validation_contract.md` — test suites, one per feature

Then approve or reject:
```bash
python run.py resume --decision approve
# or
python run.py resume --decision reject --note "F-01-003 acceptance criteria are too vague"
```

If rejected the CTO regenerates all three contracts addressing your note.

### Step 5 — select features

After contract approval the feature menu appears:

```
── Feature selection ──────────────────────────

  M-01
    [F-01-001] User registration    high
    [F-01-002] User login           high
    [F-01-003] Password reset       medium  → needs F-01-001

  M-02
    [F-02-001] User profile         medium  → needs F-01-002

  Commands:
    all              run all features
    M-01             run all features in a milestone
    F-01-001         run a specific feature
    F-01-001,F-01-002  comma-separated list
    skip F-01-003 all  all except specified

  Your selection:
```

Type your selection. The CTO builds a spawn plan — deciding which features run in parallel and which wait for dependencies.

### Step 6 — workers run

For each selected feature the worker agent:
1. Reads `doc1_security_contract.md` and the feature block from `doc2`
2. Creates a git branch (`feature/F-01-001-user-registration`)
3. Implements the feature using bash and file tools inside Docker
4. Runs install → lint → test → audit
5. Files `reports/F-01-001_milestone.md`
6. Opens a PR

You do not need to do anything during this step. Watch the terminal for progress.

### Step 7 — validator runs

After each worker completes, the validator reads the feature's test suite from `doc3` and the milestone report, then calls Gemini. It never reads source code.

If it passes:
- Memory is updated with anything the worker discovered
- The next blocked features become ready
- The pipeline continues

If it fails you see the specific test cases that failed and the pipeline stops for that feature. You can inspect the milestone report and requeue the feature.

### Step 8 — done

When all selected features pass validation the pipeline prints a completion summary. You can then select the next batch or call the project complete.

---

## Commands reference

```bash
# One-time setup
python run.py docker-build

# Start a new project (requires doc0 to be filled in)
python run.py start

# Continue after any gate or interruption
python run.py resume
python run.py resume --decision approve
python run.py resume --decision reject --note "your note here"

# Check where the project is at any time
python run.py status

# Inspect project memory (what workers have learned)
python run.py memory
python run.py memory F-01-002
```

`resume` with no `--decision` flag just continues the pipeline if no gate is pending. Safe to run any time.

---

## The five phases

The pipeline moves through these phases in order. `project_state.json` always shows the current phase.

| Phase | What happens | Gate? |
|---|---|---|
| `clarification` | CTO asks questions, you answer. Repeats until CTO has enough. | No |
| `plan_review` | CTO writes the shared plan. You approve or reject. | **Yes** |
| `contract_gen` | CTO generates doc1, doc2, doc3 automatically. | No |
| `contract_review` | You read the three contracts and approve or reject. | **Yes** |
| `feature_selection` | You choose which features to implement. | Interactive |
| `implementation` | Workers implement, validators validate, memory grows. | Per PR |
| `complete` | All selected features passed. | No |

---

## Contract files

The three contracts are templates in the repo that the CTO fills in at runtime. After the CTO runs, they contain real content for your project and should be committed to git.

**doc1 — security contract.** Defines the threat model, authentication mechanism, data sensitivity level, PII fields, compliance requirements, rate limiting rules, audit events, and a security checklist. Workers must read this before touching any code. Validators check the checklist compliance in every milestone report.

**doc2 — features contract.** One block per feature. Each block has: a unique feature ID (F-MM-NNN), title, milestone, priority, complexity, dependency list, acceptance criteria in Given/When/Then format, security constraint references into doc1, branch name, and done definition. This is what the CTO uses to build worker contexts and the feature menu.

**doc3 — validation contract.** One test suite per feature. Each test case has: ID, type (unit/integration/security/regression), whether it blocks a merge, a plain-language description, given/when/expected conditions, and a `verified_via` field pointing to a specific field in the milestone report. The validator reads this against the milestone report — never against code.

**doc4 — milestone report template.** The worker copies this to `reports/{feature_id}_milestone.md` and fills it in. Contains: what was implemented, what was left undone, every command run with exit code, issues discovered, and the security checklist. The validator's entire judgment is based on this document.

---

## Human gates

Gates are deliberate pauses where the pipeline waits for your input. There are three types.

**Plan approval.** The CTO has finished clarifying and written the shared plan. You read `doc0_project_brief.md` and either approve (pipeline moves to contract generation) or reject with a note (CTO revises).

**Contract approval.** The CTO has generated doc1, doc2, doc3. You read all three and either approve (pipeline moves to feature selection) or reject with a note (CTO regenerates all three). Take this seriously — everything downstream depends on contract quality.

**Security escalation.** A validator found that `security_checklist_followed` was false or a security test failed. You acknowledge the issue before the pipeline continues. The feature is marked failed and you decide whether to requeue it.

All gates write to `project_state.json` and pause the graph. The graph is resumable indefinitely — you can `Ctrl+C`, come back tomorrow, and run `python run.py resume` to continue from exactly where you left off.

---

## Project memory

`memory.json` grows as features complete. It has four sections:

**architecture_decisions** — key technical choices made during implementation (e.g. "chose JWT over sessions because the security contract requires stateless auth"). The CTO injects relevant decisions into the context of features that depend on earlier ones.

**failed_approaches** — things a worker tried that didn't work (e.g. "passport-local conflicts with express-session v2"). Every worker sees all failed approaches regardless of which feature they came from. This prevents workers from repeating mistakes.

**discovered_constraints** — real-world limitations found during implementation that weren't in the contracts (e.g. "hosting provider does not support websockets — use SSE instead"). Injected into worker contexts for features that are affected.

**open_risks** — unresolved high/critical issues. Always injected into every worker context until resolved.

Memory is append-only. Nothing is ever deleted. You can inspect it with:
```bash
python run.py memory               # full memory
python run.py memory F-01-002     # filtered for a specific feature
```

---

## Docker environment

Workers run bash commands inside the `dev-assistant-test` container. The project directory is mounted at `/project` read-write.

The image includes: Node 20, npm, Python 3, pip-audit, git, GitHub CLI.

**Rebuild the image** if you update `Dockerfile.test`:
```bash
python run.py docker-build
```

**Use a custom image name** by setting `TEST_IMAGE` in `.env`:
```
TEST_IMAGE=my-project-test
```

**Debug a worker command manually** by running a shell in the container:
```bash
docker run --rm -it -v $(pwd):/project -w /project dev-assistant-test bash
```

This is the exact environment the worker uses — useful for reproducing issues the worker reported in its milestone report.

---

## Model configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | Claude API key |
| `GEMINI_API_KEY` | required | Gemini API key |
| `GITHUB_TOKEN` | required | For `gh pr create` inside Docker |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Model for CTO and workers |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model for validators |
| `CTO_MODEL` | `claude` | Provider for CTO phase (`claude` or `gemini`) |
| `VALIDATOR_MODEL` | `gemini` | Provider for validation (`claude` or `gemini`) |
| `TEST_IMAGE` | `dev-assistant-test` | Docker image name |

The validator intentionally uses a different provider from the worker. This prevents the same model from both writing and validating its own work.

---

## Troubleshooting

**"Docker daemon is not running"**
Start Docker Desktop (Mac/Windows) or run `sudo systemctl start docker` (Linux).

**"Test image not found"**
Run `python run.py docker-build` first.

**"No checkpoint found. Run start first."**
`project_state.json` or `checkpoints.db` is missing. Run `python run.py start`.

**"Worker exceeded maximum turns"**
The feature was too complex to complete in 40 API turns. Check `reports/{feature_id}_milestone.md` for what was partially done, then requeue the feature. Consider splitting it into smaller features in doc2.

**Worker filed a failing milestone report**
Read `reports/{feature_id}_milestone.md` — specifically `left_undone` and `issues_discovered`. The validator will fail specific test cases and tell you which ones. You can edit the feature block in doc2 to clarify requirements, then requeue.

**CTO generated contracts but a feature is missing from doc2**
The contract consistency check should have caught this. Run `python run.py resume --decision reject --note "F-01-003 missing from doc2"` to trigger regeneration.

**Pipeline crashed mid-feature**
Run `python run.py resume`. The LangGraph checkpoint means the pipeline resumes from the last completed node — the worker will restart from its beginning, which is safe because it creates a fresh branch.

**Want to restart from scratch**
```bash
rm project_state.json checkpoints.db memory.json
# Optionally reset contracts to templates:
git checkout doc1_security_contract.md doc2_features_contract.md doc3_validation_contract.md
python run.py start
```

---

## File ownership — what you can and cannot edit

| File | Owner | Can you edit it? |
|---|---|---|
| `doc0_project_brief.md` | You | Yes — fill it in before starting |
| `doc1_security_contract.md` | CTO (generated) | Read it. Request changes via gate rejection. |
| `doc2_features_contract.md` | CTO (generated) | Read it. Request changes via gate rejection. |
| `doc3_validation_contract.md` | CTO (generated) | Read it. Request changes via gate rejection. |
| `doc4_milestone_report.md` | Template | Never edit — workers copy it |
| `reports/*.md` | Workers | Read-only for you — the validator writes the result section |
| `memory.json` | System | Never edit — append-only, managed by the pipeline |
| `project_state.json` | System | Never edit — managed by gates/state_store.py |
| `checkpoints.db` | LangGraph | Never edit |
| `CLAUDE.md` | You | Yes — adjust worker standing instructions |
| `.claude/rules/*.md` | You | Yes — adjust implementation rules |
| `Dockerfile.test` | You | Yes — add tools your project needs |
| `run.py`, `graph.py`, etc. | Pipeline | Do not edit unless you know what you're doing |
| `.env` | You | Yes — keep it out of git |

The three contracts (doc1, doc2, doc3) are owned by the CTO after the first generation but you have indirect control: reject the gate with a specific note and the CTO regenerates them. If you need a surgical change to a single feature block, you can edit doc2 manually and requeue just that feature — but be careful to keep doc2 and doc3 consistent (every feature in doc2 needs a test suite in doc3).
