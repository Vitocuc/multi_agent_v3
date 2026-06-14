"""
docker/runner.py

Runs commands inside the pipeline test container, and manages the lifecycle
of the application-under-test for the validator.

Two responsibilities:
  1. run() — one-off commands for the worker's test_runner tool
     (install, lint, test, audit). Uses --network host for internet access.
  2. App lifecycle for the validator:
     - ensure_network() / start_app() / wait_for_app() / get_app_logs() / stop_app()
     - run(..., network=NETWORK_NAME) — runs generated tests against the live app

The project directory is mounted at /project in every container.
"""
from __future__ import annotations
import os
import re
import time
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_IMAGE     = "dev-assistant-test"
NETWORK_NAME      = "dev-assistant-net"
TIMEOUT_SECONDS   = 300    # one-off command timeout
APP_READY_TIMEOUT = 60     # seconds to wait for app to start responding
MAX_OUTPUT_CHARS  = 4000


@dataclass
class CommandResult:
    command:   str
    exit_code: int
    stdout:    str
    stderr:    str
    summary:   str
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

    def __init__(self, root: Path, image: Optional[str] = None, env_forward: bool = True) -> None:
        self.root        = root.resolve()
        self.image       = image or os.environ.get("TEST_IMAGE", DEFAULT_IMAGE)
        self.network     = NETWORK_NAME
        self.env_forward = env_forward
        self._verified   = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def verify(self) -> None:
        """Check Docker is running and the test image exists. Raises on failure."""
        if self._verified:
            return

        r = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        if r.returncode != 0:
            raise DockerNotAvailableError(
                "Docker daemon is not running. Start Docker Desktop (or dockerd) "
                "and try again."
            )

        r = subprocess.run(["docker", "image", "inspect", self.image], capture_output=True, timeout=10)
        if r.returncode != 0:
            raise ImageNotBuiltError(
                f"Test image '{self.image}' not found. Build it first:\n"
                f"  docker build -f Dockerfile.test -t {self.image} .\n"
                f"Or run: python run.py docker-build"
            )

        self._verified = True

    def ensure_network(self) -> None:
        """Create the shared docker network if it doesn't exist. Idempotent."""
        subprocess.run(
            ["docker", "network", "create", self.network],
            capture_output=True, timeout=15,
        )
        # Non-zero exit if it already exists — that's fine, ignore.

    # ------------------------------------------------------------------
    # One-off commands (worker test_runner tool, generated test execution)
    # ------------------------------------------------------------------

    def run(self, command: str, workdir: str = "/project", network: Optional[str] = None) -> CommandResult:
        """
        Run a one-off command inside the test container.
        network=None         -> --network host (internet access, for installs/lint/test/audit)
        network=NETWORK_NAME -> attached to the app network, so generated tests can
                                 reach the running app container by name
        Never raises on non-zero exit codes.
        """
        self.verify()

        docker_cmd = ["docker", "run", "--rm"]
        if network:
            self.ensure_network()
            docker_cmd += ["--network", network]
        else:
            docker_cmd += ["--network", "host"]
        docker_cmd += ["-v", f"{self.root}:/project", "-w", workdir]

        if self.env_forward:
            for key, val in self._safe_env().items():
                docker_cmd += ["-e", f"{key}={val}"]

        gh_token = os.environ.get("GITHUB_TOKEN", "")
        if gh_token:
            docker_cmd += ["-e", f"GH_TOKEN={gh_token}"]

        docker_cmd += [self.image, "bash", "-c", command]

        try:
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
            stdout, stderr = proc.stdout or "", proc.stderr or ""
            return CommandResult(
                command=command, exit_code=proc.returncode,
                stdout=stdout, stderr=stderr,
                summary=_make_summary(command, proc.returncode, stdout + stderr),
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=command, exit_code=124, stdout="",
                stderr=f"Command timed out after {TIMEOUT_SECONDS}s",
                summary=f"TIMEOUT after {TIMEOUT_SECONDS}s: {command[:60]}",
                timed_out=True,
            )

    def run_sequence(self, commands: list[str]) -> list[CommandResult]:
        """Run commands in order. Stops on first non-zero exit code."""
        results = []
        for cmd in commands:
            r = self.run(cmd)
            results.append(r)
            if not r.success:
                break
        return results

    # ------------------------------------------------------------------
    # Application lifecycle (validator)
    # ------------------------------------------------------------------

    def start_app(self, run_command: str, port: int, container_name: str) -> CommandResult:
        """
        Start the application in the background, attached to the shared network.
        Removes any existing container with the same name first.
        Not --rm: the container persists so logs survive if it crashes —
        stop_app() removes it explicitly.
        """
        self.verify()
        self.ensure_network()
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=15)

        docker_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "--network", self.network,
            "-v", f"{self.root}:/project",
            "-w", "/project",
        ]
        if self.env_forward:
            for key, val in self._safe_env().items():
                docker_cmd += ["-e", f"{key}={val}"]
        docker_cmd += ["-e", f"PORT={port}"]
        docker_cmd += [self.image, "bash", "-c", run_command]

        try:
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)
            return CommandResult(
                command=run_command, exit_code=proc.returncode,
                stdout=proc.stdout, stderr=proc.stderr,
                summary=f"start_app: {'started' if proc.returncode == 0 else 'failed'}",
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=run_command, exit_code=124, stdout="", stderr="docker run timed out",
                summary="start_app: timed out", timed_out=True,
            )

    def wait_for_app(self, container_name: str, port: int, timeout: int = APP_READY_TIMEOUT) -> bool:
        """
        Poll the app container until it responds on `port`, or timeout.
        Checks from inside the container against localhost — any HTTP
        response (including 404/500) counts as "ready". Returns False
        immediately if the container has already exited (crashed on startup).
        """
        for _ in range(timeout):
            ps = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True, text=True, timeout=10,
            )
            if ps.returncode != 0 or ps.stdout.strip() != "true":
                return False  # container exited — crashed on startup

            check = subprocess.run(
                ["docker", "exec", container_name, "bash", "-c",
                 f"curl -s -o /dev/null --max-time 2 http://localhost:{port}/"],
                capture_output=True, timeout=10,
            )
            if check.returncode == 0:
                return True
            time.sleep(1)
        return False

    def get_app_logs(self, container_name: str, tail: int = 60) -> str:
        r = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_name],
            capture_output=True, text=True, timeout=15,
        )
        return (r.stdout + r.stderr).strip()

    def stop_app(self, container_name: str) -> None:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=30)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_env(self) -> dict[str, str]:
        """Env vars safe to forward — excludes anything matching a secret pattern."""
        secret_patterns = re.compile(
            r"(key|secret|token|password|passwd|pwd|auth|credential|private)",
            re.IGNORECASE,
        )
        safe = {}
        for k, v in os.environ.items():
            if secret_patterns.search(k):
                continue
            if k.startswith(("NODE_", "NPM_", "PYTHON", "PATH", "HOME",
                              "CI", "TEST_", "APP_", "PORT", "HOST")):
                safe[k] = v
        return safe


def build_image(root: Path, image: str = DEFAULT_IMAGE) -> CommandResult:
    """Build the test image from Dockerfile.test. Called by `python run.py docker-build`."""
    dockerfile = root / "Dockerfile.test"
    if not dockerfile.exists():
        raise FileNotFoundError(f"Dockerfile.test not found at {dockerfile}")

    proc = subprocess.run(
        ["docker", "build", "-f", "Dockerfile.test", "-t", image, "."],
        cwd=root, capture_output=False, timeout=600,
    )
    return CommandResult(
        command=f"docker build -f Dockerfile.test -t {image} .",
        exit_code=proc.returncode, stdout="(streamed to terminal)", stderr="",
        summary=f"Image build {'succeeded' if proc.returncode == 0 else 'FAILED'}",
    )


def _make_summary(command: str, exit_code: int, output: str) -> str:
    """One-line summary safe for milestone reports — strips ANSI codes and secret-looking lines."""
    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
    secret_line = re.compile(
        r"(api.?key|token|password|secret|credential)\s*[:=]\s*\S+", re.IGNORECASE,
    )
    lines = [l for l in clean.splitlines() if not secret_line.search(l)]
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
    summary = f"exit {exit_code}: {best}"
    if len(summary) > 120:
        summary = summary[:117] + "..."
    return summary


class DockerNotAvailableError(Exception):
    """Docker daemon is not running."""
    pass


class ImageNotBuiltError(Exception):
    """Test image has not been built yet."""
    pass
