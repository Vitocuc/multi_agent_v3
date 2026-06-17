"""
git_ops.py

All git and GitHub CLI operations.
This module is called by the pipeline (graph.py) only.
Workers and validators have zero git access — they write files and reports,
the pipeline handles everything version-control related.

Operations:
  setup_branch(feature_id, branch_name, root)  — fetch, checkout develop, create branch
  commit_and_push(feature_id, branch_name, root) — stage all, commit, push
  open_pr(feature_id, title, report_path, root)  — gh pr create targeting develop
  merge_pr(feature_id, root)                     — gh pr merge after human approval
  pr_status(feature_id, root)                    — poll review decision + merge state
"""

from __future__ import annotations
import subprocess
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GitResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    command: str

    @property
    def output(self) -> str:
        return (self.stdout + self.stderr).strip()


@dataclass
class PRStatus:
    number: int
    state: str  # OPEN | MERGED | CLOSED
    review_decision: str  # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | ""
    merged: bool
    url: str


def _run(cmd: list[str], cwd: Path, timeout: int = 60) -> GitResult:
    """Run a shell command and return GitResult. Never raises on non-zero exit."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return GitResult(
            success=proc.returncode == 0,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            exit_code=proc.returncode,
            command=" ".join(cmd),
        )
    except subprocess.TimeoutExpired:
        return GitResult(
            success=False,
            stdout="",
            stderr=f"Timeout after {timeout}s",
            exit_code=124,
            command=" ".join(cmd),
        )
    except FileNotFoundError as e:
        return GitResult(
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=127,
            command=" ".join(cmd),
        )


# ---------------------------------------------------------------------------
# Branch setup
# ---------------------------------------------------------------------------


def setup_branch(feature_id: str, branch_name: str, root: Path) -> GitResult:
    """
    Fetch origin, ensure develop exists, create feature branch from develop.
    Called by the pipeline before handing off to the worker.
    """
    # Fetch
    r = _run(["git", "fetch", "origin"], root)
    if not r.success:
        return r

    # Checkout or create develop
    r = _run(["git", "checkout", "develop"], root)
    if not r.success:
        # develop doesn't exist locally — try tracking remote
        r = _run(["git", "checkout", "-b", "develop", "origin/develop"], root)
        if not r.success:
            # No remote develop either — create fresh
            r = _run(["git", "checkout", "-b", "develop"], root)
            if not r.success:
                return r

    # Pull latest develop
    _run(["git", "pull", "origin", "develop"], root)

    # Create feature branch (delete if it already exists to start clean)
    _run(["git", "branch", "-D", branch_name], root)  # ok if doesn't exist
    r = _run(["git", "checkout", "-b", branch_name], root)
    return r


def checkout_branch(branch_name: str, root: Path) -> GitResult:
    """
    Checkout an existing feature branch WITHOUT creating or deleting it.
    Used by `retry` — the branch and its commit/PR already exist from the
    previous attempt; we just need to make sure it's checked out before the
    worker runs again. Falls back to tracking the remote branch if it only
    exists on origin.
    """
    r = _run(["git", "checkout", branch_name], root)
    if r.success:
        return r

    _run(["git", "fetch", "origin"], root)
    return _run(["git", "checkout", "-b", branch_name, f"origin/{branch_name}"], root)


# ---------------------------------------------------------------------------
# Commit and push
# ---------------------------------------------------------------------------


def commit_and_push(feature_id: str, branch_name: str, root: Path) -> GitResult:
    """
    Stage all changes, commit with standard message, push to origin.
    Called by the pipeline after the worker completes successfully.
    """
    # Stage everything the worker wrote
    r = _run(["git", "add", "."], root)
    if not r.success:
        return r

    # Check if there's anything to commit
    status = _run(["git", "status", "--porcelain"], root)
    if not status.stdout.strip():
        return GitResult(
            success=True,
            stdout="Nothing to commit",
            stderr="",
            exit_code=0,
            command="git status",
        )

    # Commit
    msg = f"[{feature_id}] Implement feature"
    r = _run(["git", "commit", "-m", msg], root)
    if not r.success:
        return r

    # Push
    r = _run(["git", "push", "-u", "origin", branch_name], root, timeout=120)
    return r


# ---------------------------------------------------------------------------
# Open PR
# ---------------------------------------------------------------------------


def open_pr(
    feature_id: str,
    title: str,
    report_path: Path,
    root: Path,
) -> GitResult:
    """
    Open a GitHub PR targeting develop.
    PR body is the milestone report content.
    Requires: gh CLI installed and GH_TOKEN / GITHUB_TOKEN in environment.

    Idempotent: if a PR for this feature already exists (e.g. a previous
    attempt opened it, and this is a retry), returns success with the
    existing PR's URL instead of erroring on "already exists".
    """
    existing = pr_status(feature_id, root)
    if existing is not None:
        if existing.merged:
            return GitResult(
                success=True,
                stdout=existing.url,
                stderr="PR already merged",
                exit_code=0,
                command="gh pr create (already merged)",
            )
        if existing.state == "OPEN":
            return GitResult(
                success=True,
                stdout=existing.url,
                stderr="PR already exists — push updates it automatically",
                exit_code=0,
                command="gh pr create (existing)",
            )

    if not report_path.exists():
        return GitResult(
            success=False,
            stdout="",
            stderr=f"Milestone report not found: {report_path}",
            exit_code=1,
            command="gh pr create",
        )

    body = report_path.read_text()
    pr_title = f"[{feature_id}] {title}"

    r = _run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "develop",
            "--title",
            pr_title,
            "--body",
            body,
        ],
        root,
        timeout=60,
    )
    return r


# ---------------------------------------------------------------------------
# PR status
# ---------------------------------------------------------------------------


def pr_status(feature_id: str, root: Path) -> Optional[PRStatus]:
    """
    Poll GitHub for the PR associated with this feature.
    Returns PRStatus or None if no PR found.
    """
    r = _run(
        [
            "gh",
            "pr",
            "list",
            "--search",
            f"[{feature_id}] in:title",
            "--json",
            "number,title,state,reviewDecision,mergedAt,url",
        ],
        root,
        timeout=30,
    )

    if not r.success:
        return None

    try:
        prs = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return None

    if not prs:
        return None

    pr = prs[0]
    return PRStatus(
        number=pr.get("number", 0),
        state=pr.get("state", ""),
        review_decision=pr.get("reviewDecision", ""),
        merged=bool(pr.get("mergedAt")),
        url=pr.get("url", ""),
    )


# ---------------------------------------------------------------------------
# Merge PR
# ---------------------------------------------------------------------------


def merge_pr(feature_id: str, root: Path) -> GitResult:
    """
    Merge the feature PR into develop via squash merge.
    Called by the pipeline after human_gate = approved and validator passes.
    """
    status = pr_status(feature_id, root)
    if status is None:
        return GitResult(
            success=False,
            stdout="",
            stderr=f"No PR found for {feature_id}",
            exit_code=1,
            command="gh pr merge",
        )

    if status.merged:
        return GitResult(
            success=True,
            stdout="PR already merged",
            stderr="",
            exit_code=0,
            command="gh pr merge",
        )

    r = _run(
        [
            "gh",
            "pr",
            "merge",
            str(status.number),
            "--squash",
            "--delete-branch",
            "--auto",  # merge as soon as checks pass
        ],
        root,
        timeout=60,
    )
    return r
