"""
docker/runner.py

Runs shell commands inside the pipeline test container.
The project directory is mounted read-write at /project.
Environment variables from .env are forwarded (secrets excluded).

Every command returns a CommandResult with stdout, stderr, exit_code, and
a one-line summary safe to include in milestone reports (no secrets).

Usage:
    from docker.runner import DockerRunner
    runner = DockerRunner(root=Path("."))
    result = runner.run("npm test")
    print(result.exit_code, result.summary)
"""
from __future__ import annotations
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_IMAGE   = "dev-assistant-test"
TIMEOUT_SECONDS = 300   # 5 min per command — increase for slow test suites
MAX_OUTPUT_CHARS = 4000  # truncate long output before returning to the LLM


@dataclass
class CommandResult:
    command:   str
    exit_code: int
    stdout:    str
    stderr:    str
    summary:   str    # one-line, safe for milestone reports (no secrets)
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0


class DockerRunner:
    """
    Runs commands inside the test container.
    Raises DockerNotAvailableError if Docker is not running.
    Raises ImageNotBuiltError if the test image does not exist.
    """

    def __init__(
        self,
        root:         Path,
        image:        Optional[str] = None,
        env_forward:  bool = True,
    ) -> None:
        self.root        = root.resolve()
        self.image       = image or os.environ.get("TEST_IMAGE", DEFAULT_IMAGE)
        self.env_forward = env_forward
        self._verified   = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(self) -> None:
        """
        Check that Docker is running and the test image exists.
        Call once at the start of a worker session.
        Raises DockerNotAvailableError or ImageNotBuiltError on failure.
        """
        if self._verified:
            return

        # Check Docker daemon
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            raise DockerNotAvailableError(
                "Docker daemon is not running. Start Docker Desktop (or dockerd) "
                "and try again."
            )

        # Check image exists
        r = subprocess.run(
            ["docker", "image", "inspect", self.image],
            capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            raise ImageNotBuiltError(
                f"Test image '{self.image}' not found. Build it first:\n"
                f"  docker build -f Dockerfile.test -t {self.image} .\n"
                f"Or run: python run.py docker-build"
            )

        self._verified = True

    def run(self, command: str, workdir: str = "/project") -> CommandResult:
        """
        Run a shell command inside the test container.
        Project root is mounted at /project (read-write).
        Returns CommandResult — never raises on non-zero exit codes.
        """
        self.verify()

        docker_cmd = [
            "docker", "run",
            "--rm",
            "--network", "host",           # needed for npm install, pip install
            "-v", f"{self.root}:/project", # mount project read-write
            "-w", workdir,                 # working directory inside container
        ]

        # Forward safe env vars (skip secrets)
        if self.env_forward:
            for key, val in self._safe_env().items():
                docker_cmd += ["-e", f"{key}={val}"]

        # Forward GitHub token for gh CLI
        gh_token = os.environ.get("GITHUB_TOKEN", "")
        if gh_token:
            docker_cmd += ["-e", f"GH_TOKEN={gh_token}"]

        docker_cmd += [self.image, "bash", "-c", command]

        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
            stdout   = proc.stdout or ""
            stderr   = proc.stderr or ""
            combined = stdout + stderr

            return CommandResult(
                command=command,
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                summary=_make_summary(command, proc.returncode, combined),
                timed_out=False,
            )

        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command,
                exit_code=124,   # standard timeout exit code
                stdout="",
                stderr=f"Command timed out after {TIMEOUT_SECONDS}s",
                summary=f"TIMEOUT after {TIMEOUT_SECONDS}s: {command[:60]}",
                timed_out=True,
            )

    def run_sequence(self, commands: list[str]) -> list[CommandResult]:
        """
        Run a list of commands in order.
        Stops on first non-zero exit code.
        Returns all results including the failing one.
        """
        results = []
        for cmd in commands:
            r = self.run(cmd)
            results.append(r)
            if not r.success:
                break
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_env(self) -> dict[str, str]:
        """
        Return env vars safe to forward into the container.
        Excludes known secret keys to prevent leakage into logs.
        """
        secret_patterns = re.compile(
            r"(key|secret|token|password|passwd|pwd|auth|credential|private)",
            re.IGNORECASE,
        )
        safe = {}
        for k, v in os.environ.items():
            if secret_patterns.search(k):
                continue
            # Only forward relevant vars — avoid polluting container env
            if k.startswith(("NODE_", "NPM_", "PYTHON", "PATH", "HOME",
                              "CI", "TEST_", "APP_", "PORT", "HOST")):
                safe[k] = v
        return safe


def build_image(root: Path, image: str = DEFAULT_IMAGE) -> CommandResult:
    """
    Build the test image from Dockerfile.test.
    Called by `python run.py docker-build`.
    """
    dockerfile = root / "Dockerfile.test"
    if not dockerfile.exists():
        raise FileNotFoundError(f"Dockerfile.test not found at {dockerfile}")

    proc = subprocess.run(
        ["docker", "build", "-f", "Dockerfile.test", "-t", image, "."],
        cwd=root,
        capture_output=False,  # stream build output to terminal
        timeout=600,
    )
    return CommandResult(
        command=f"docker build -f Dockerfile.test -t {image} .",
        exit_code=proc.returncode,
        stdout="(streamed to terminal)",
        stderr="",
        summary=f"Image build {'succeeded' if proc.returncode == 0 else 'FAILED'}",
    )


def _make_summary(command: str, exit_code: int, output: str) -> str:
    """
    Make a one-line summary safe for milestone reports.
    - Strips ANSI codes
    - Removes lines that look like they contain secrets
    - Truncates to ~120 chars
    """
    # Strip ANSI escape codes
    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)

    # Remove lines that look like secrets
    secret_line = re.compile(
        r"(api.?key|token|password|secret|credential)\s*[:=]\s*\S+",
        re.IGNORECASE,
    )
    lines = [l for l in clean.splitlines() if not secret_line.search(l)]

    # Pick the most informative line — prefer lines with keywords
    keywords = ("error", "fail", "warn", "passed", "found", "vulnerabilit",
                "coverage", "success", "added", "removed", "updated")
    best = ""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        if any(kw in line.lower() for kw in keywords):
            best = line
            break
    if not best and lines:
        best = lines[-1].strip()

    prefix = f"exit {exit_code}: "
    summary = prefix + best
    if len(summary) > 120:
        summary = summary[:117] + "..."
    return summary


# ------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------

class DockerNotAvailableError(Exception):
    """Docker daemon is not running."""
    pass


class ImageNotBuiltError(Exception):
    """Test image has not been built yet."""
    pass
