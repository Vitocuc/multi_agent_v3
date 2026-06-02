---
paths:
  - "**/*"
---
# Git rules

## Branch strategy

All feature branches are cut from `develop`. Never from `main`.

```bash
# Step 1 — ensure develop is up to date
git fetch origin
git checkout develop 2>/dev/null \
  || git checkout -b develop origin/develop 2>/dev/null \
  || git checkout -b develop

# Step 2 — create your feature branch
git checkout -b feature/{feature_id}-{slug}
```

PRs target `develop`. The merge from `develop` → `main` is a human milestone decision, not an automated step.

## Commit messages

Every commit must reference the feature ID:

```
[F-01-002] Add user login endpoint
[F-01-002] Fix input sanitisation on email field
```

Subject line under 72 characters. Body explains why, not what — the diff shows what.

## What to commit

Only files that belong to this feature. Never commit:
- `.env` or any file with real secrets
- Unrelated refactors or fixes
- Debug print statements
- Lock files unless you added or changed a dependency

## Before pushing

All commands must pass: install → lint → test → audit.
If a test was already failing before you started and is unrelated to your feature: document it in issues_discovered, do not fix it silently.

## PR checklist

- [ ] Branch cut from `develop` (not `main`)
- [ ] Branch name matches `feature/{feature_id}-{slug}`
- [ ] PR targets `develop` (--base develop in gh pr create)
- [ ] All acceptance criteria addressed or documented as undone
- [ ] `reports/{feature_id}_milestone.md` exists and is complete
- [ ] Security checklist ticked or exceptions explained
- [ ] No secrets in any committed file
- [ ] All commands exit 0 (or failures explained in milestone report)
- [ ] PR title: `[{feature_id}] {feature title}`
- [ ] PR body: full milestone report content

After opening the PR: stop. Do not merge. Do not push more commits unless the reviewer requests changes.
The pipeline polls GitHub with `python run.py gh-check {feature_id}` to detect approval.
