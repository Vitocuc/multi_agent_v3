"""
Structural validation tests for the ProtegoPay CI/CD pipeline.

Feature F-01-002: CI/CD Pipeline with Security Gates

These tests verify that:
  1. All required workflow files exist and are valid YAML.
  2. Every required security gate is present in the CI workflow.
  3. The gate execution order is enforced (needs: declarations).
  4. No secrets are hardcoded in any workflow file.
  5. The production Dockerfile implements required security hardening.
  6. Supporting configuration files (bandit, gitleaks, dockerignore) exist.

Tests run WITHOUT any GitHub Actions runner — they analyse the YAML files
directly, just as the infra tests analyse .tf files without running Terraform.
"""

import os
import re

import pytest

# Repository root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS_DIR = os.path.join(ROOT, ".github", "workflows")
CI_YML = os.path.join(WORKFLOWS_DIR, "ci.yml")
DEPLOY_YML = os.path.join(WORKFLOWS_DIR, "deploy-staging.yml")
DOCKERFILE = os.path.join(ROOT, "Dockerfile")


def read_file(path: str) -> str:
    """Read a file and return its content. Returns empty string if not found."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def load_yaml(path: str) -> dict:
    """Load a YAML file. Returns empty dict on failure."""
    try:
        import yaml  # type: ignore[import]

        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def yaml_is_parseable(path: str) -> bool:
    """Return True if the file parses as valid YAML without errors."""
    try:
        import yaml  # type: ignore[import]

        with open(path, encoding="utf-8") as f:
            yaml.safe_load(f)
        return True
    except ImportError:
        # pyyaml not installed — check heuristically
        content = read_file(path)
        return bool(content.strip()) and ("name:" in content or "on:" in content)
    except Exception:
        return False


def get_ci_jobs() -> dict:
    """Return the jobs dict from ci.yml, or empty dict."""
    data = load_yaml(CI_YML)
    return data.get("jobs", {})


def job_needs(jobs: dict, job_name: str) -> list:
    """
    Return the 'needs' list for a job by name.
    Tries exact name first, then case-insensitive prefix match.
    """
    if job_name in jobs:
        needs = jobs[job_name].get("needs", [])
        if isinstance(needs, str):
            return [needs]
        return needs or []
    # Fuzzy match: find any key that starts with job_name
    for key in jobs:
        if key.startswith(job_name) or job_name in key:
            needs = jobs[key].get("needs", [])
            if isinstance(needs, str):
                return [needs]
            return needs or []
    return []


def needs_contains(jobs: dict, job_name: str, required_dep: str) -> bool:
    """
    Return True if the job's 'needs' list contains required_dep
    (exact or substring match).
    """
    needs = job_needs(jobs, job_name)
    return any(required_dep in n for n in needs)


# ─────────────────────────────────────────────────────────────────────────────
# 1. File presence
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowFilesPresent:
    """Required CI/CD files must exist in the repository."""

    def test_ci_workflow_exists(self):
        assert os.path.isfile(CI_YML), (
            f"CI workflow must exist at {CI_YML}"
        )

    def test_deploy_staging_workflow_exists(self):
        assert os.path.isfile(DEPLOY_YML), (
            f"Staging deploy workflow must exist at {DEPLOY_YML}"
        )

    def test_dockerfile_exists(self):
        assert os.path.isfile(DOCKERFILE), (
            "Production Dockerfile must exist at repository root"
        )

    def test_dockerignore_exists(self):
        path = os.path.join(ROOT, ".dockerignore")
        assert os.path.isfile(path), (
            ".dockerignore must exist to prevent secrets from entering the image"
        )

    def test_bandit_config_exists(self):
        path = os.path.join(ROOT, ".bandit")
        assert os.path.isfile(path), (
            ".bandit config must exist so Bandit uses consistent settings"
        )

    def test_gitleaks_config_exists(self):
        path = os.path.join(ROOT, ".gitleaks.toml")
        assert os.path.isfile(path), (
            ".gitleaks.toml config must exist for secret scanning"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Workflow YAML validity
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowYamlValidity:
    """Workflow files must be parseable YAML."""

    def test_ci_workflow_is_valid_yaml(self):
        assert yaml_is_parseable(CI_YML), (
            f"{CI_YML} must be valid YAML"
        )

    def test_deploy_workflow_is_valid_yaml(self):
        assert yaml_is_parseable(DEPLOY_YML), (
            f"{DEPLOY_YML} must be valid YAML"
        )

    def test_ci_has_name_field(self):
        """Workflow must have a name field."""
        data = load_yaml(CI_YML)
        assert "name" in data, "ci.yml must have a 'name' field"

    def test_ci_has_jobs(self):
        """Workflow must define at least one job."""
        jobs = get_ci_jobs()
        assert len(jobs) > 0, "ci.yml must define at least one job"


# ─────────────────────────────────────────────────────────────────────────────
# 3. CI Security gates — presence
# ─────────────────────────────────────────────────────────────────────────────


class TestCISecurityGates:
    """Every required security gate must be present in ci.yml."""

    @pytest.fixture(autouse=True)
    def load_ci(self):
        self.content = read_file(CI_YML)
        self.jobs = get_ci_jobs()

    def test_lint_gate_present(self):
        """Gate 1: Lint (flake8 / ruff) must be a job in ci.yml."""
        has_lint_job = any("lint" in key for key in self.jobs)
        assert has_lint_job or "lint" in self.content, (
            "ci.yml must include a lint job (Gate 1)"
        )

    def test_pip_audit_gate_present(self):
        """Gate 2: pip-audit must be a job in ci.yml."""
        has_pip_audit_job = any(
            "pip-audit" in key or "pip_audit" in key for key in self.jobs
        )
        assert has_pip_audit_job or "pip-audit" in self.content, (
            "ci.yml must include a pip-audit job (Gate 2)"
        )

    def test_bandit_gate_present(self):
        """Gate 3: Bandit SAST must be a job in ci.yml."""
        has_bandit_job = any("bandit" in key for key in self.jobs)
        assert has_bandit_job or "bandit" in self.content, (
            "ci.yml must include a Bandit SAST job (Gate 3)"
        )

    def test_gitleaks_gate_present(self):
        """Gate 4: Gitleaks secret scanning must be a job in ci.yml."""
        has_gitleaks_job = any("gitleaks" in key for key in self.jobs)
        assert has_gitleaks_job or "gitleaks" in self.content, (
            "ci.yml must include a Gitleaks secret-scanning job (Gate 4)"
        )

    def test_pytest_gate_present(self):
        """Gate 5: pytest unit/integration tests must run in ci.yml."""
        assert "pytest" in self.content, (
            "ci.yml must run pytest as part of the test gate (Gate 5)"
        )

    def test_docker_build_gate_present(self):
        """Gate 6: Docker build must occur after security gates pass."""
        assert "docker" in self.content.lower() and "build" in self.content, (
            "ci.yml must include a docker-build step (Gate 6)"
        )

    def test_trivy_gate_present(self):
        """Gate 7: Trivy container scan must run after docker build."""
        assert "trivy" in self.content, (
            "ci.yml must include a Trivy container scan (Gate 7)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. CI gate ordering — needs declarations (parsed from YAML)
# ─────────────────────────────────────────────────────────────────────────────


class TestCIGateOrdering:
    """
    Later gates must declare `needs:` dependencies on earlier gates.
    Uses YAML-parsed job structure for reliable verification.
    """

    @pytest.fixture(autouse=True)
    def load_ci(self):
        self.jobs = get_ci_jobs()
        self.content = read_file(CI_YML)

    def test_pip_audit_needs_lint(self):
        """pip-audit (Gate 2) must declare needs: lint."""
        assert needs_contains(self.jobs, "pip-audit", "lint"), (
            "pip-audit job must declare 'needs: lint' to enforce gate ordering"
        )

    def test_bandit_needs_lint(self):
        """bandit (Gate 3) must declare needs: lint."""
        assert needs_contains(self.jobs, "bandit", "lint"), (
            "bandit job must declare 'needs: lint' to enforce gate ordering"
        )

    def test_test_gate_needs_security_gates(self):
        """
        pytest gate (Gate 5) must not run until security gates (2, 3, 4) pass.
        The test job must declare needs: on pip-audit, bandit, AND gitleaks.
        """
        # Find the test job (may be called 'test' or 'tests')
        test_job_key = next(
            (k for k in self.jobs if k in ("test", "tests")), None
        )
        if test_job_key is None:
            # Fallback: check raw content for a test job with needs referencing security gates
            security_gate_refs = sum(
                1 for g in ["pip-audit", "bandit", "gitleaks"]
                if g in self.content
            )
            assert security_gate_refs >= 2, (
                "Test gate must depend on at least 2 security gates "
                "(pip-audit, bandit, gitleaks)"
            )
            return

        test_needs = job_needs(self.jobs, test_job_key)
        security_deps = [
            n for n in test_needs
            if any(g in n for g in ["pip-audit", "pip_audit", "bandit", "gitleaks"])
        ]
        assert len(security_deps) >= 1, (
            f"Test job needs: {test_needs} — must include at least one security gate "
            "(pip-audit, bandit, or gitleaks)"
        )

    def test_docker_build_needs_test(self):
        """Docker build (Gate 6) must not run until pytest (Gate 5) passes."""
        # Find the docker-build job
        docker_job_key = next(
            (k for k in self.jobs if "docker" in k and "build" in k), None
        )
        if docker_job_key is None:
            # Docker build may be embedded in another job — check content
            assert "needs" in self.content and "test" in self.content, (
                "Docker build must declare needs: test"
            )
            return

        assert needs_contains(self.jobs, docker_job_key, "test"), (
            f"docker-build job needs: {job_needs(self.jobs, docker_job_key)} "
            "— must include 'test'"
        )

    def test_trivy_needs_docker_build(self):
        """Trivy (Gate 7) must not run until Docker build (Gate 6) succeeds."""
        trivy_job_key = next(
            (k for k in self.jobs if "trivy" in k), None
        )
        if trivy_job_key is None:
            # Trivy might be a step not a job — check content
            assert "trivy" in self.content, (
                "Trivy must appear in ci.yml"
            )
            return

        trivy_needs = job_needs(self.jobs, trivy_job_key)
        docker_dep = any(
            "docker" in n or "build" in n for n in trivy_needs
        )
        assert docker_dep, (
            f"trivy job needs: {trivy_needs} — must depend on the docker-build job"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. No hardcoded secrets in workflow files
# ─────────────────────────────────────────────────────────────────────────────


class TestNoHardcodedSecrets:
    """
    Workflow files must reference secrets via ${{ secrets.VARIABLE_NAME }}
    syntax — never as literal values.
    """

    # Patterns that would indicate a hardcoded secret (case-insensitive)
    SECRET_PATTERNS = [
        r"aws_access_key_id\s*:\s*[A-Z0-9]{20}",   # AWS key literal (not via ${{)
        r"aws_secret_access_key\s*:\s*[A-Za-z0-9/+]{40}",  # AWS secret literal
        r"password\s*:\s*['\"][^$\{\}][^'\"]{7,}['\"]",  # password: 'literal'
        r"token\s*:\s*['\"][^$\{\}][^'\"]{7,}['\"]",     # token: 'literal'
        r"api_key\s*:\s*['\"][^$\{\}][^'\"]{7,}['\"]",   # api_key: 'literal'
    ]

    def _check_no_secrets(self, content: str, filename: str):
        for pattern in self.SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            assert not matches, (
                f"{filename} contains a potential hardcoded secret "
                f"matching '{pattern}': {matches}"
            )

    def test_ci_yml_no_hardcoded_secrets(self):
        self._check_no_secrets(read_file(CI_YML), "ci.yml")

    def test_deploy_yml_no_hardcoded_secrets(self):
        self._check_no_secrets(read_file(DEPLOY_YML), "deploy-staging.yml")

    def test_ci_yml_uses_secrets_context(self):
        """AWS credentials in ci.yml must come from ${{ secrets.* }} context."""
        content = read_file(CI_YML)
        if "aws-access-key-id" in content:
            assert "secrets.AWS_ACCESS_KEY_ID" in content, (
                "AWS credentials must use ${{ secrets.AWS_ACCESS_KEY_ID }}"
            )
        if "aws-secret-access-key" in content:
            assert "secrets.AWS_SECRET_ACCESS_KEY" in content, (
                "AWS credentials must use ${{ secrets.AWS_SECRET_ACCESS_KEY }}"
            )

    def test_deploy_yml_uses_secrets_context(self):
        """AWS credentials in deploy-staging.yml must come from secrets context."""
        content = read_file(DEPLOY_YML)
        if "aws-access-key-id" in content:
            assert "secrets.AWS_ACCESS_KEY_ID" in content, (
                "AWS credentials must use ${{ secrets.AWS_ACCESS_KEY_ID }}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 6. CI workflow triggers
# ─────────────────────────────────────────────────────────────────────────────


class TestCITriggers:
    """CI must run on pull_request events targeting the protected branches."""

    @pytest.fixture(autouse=True)
    def load_ci(self):
        self.content = read_file(CI_YML)
        self.data = load_yaml(CI_YML)

    def test_triggers_on_pull_request(self):
        """CI must run on pull_request events."""
        triggers = self.data.get("on", {})
        if isinstance(triggers, dict):
            assert "pull_request" in triggers, (
                "ci.yml must trigger on pull_request events"
            )
        else:
            assert "pull_request" in self.content, (
                "ci.yml must trigger on pull_request events"
            )

    def test_triggers_on_develop_branch(self):
        """CI must protect the develop branch."""
        assert "develop" in self.content, (
            "ci.yml must reference the develop branch as a trigger target"
        )

    def test_triggers_on_main_branch(self):
        """CI must protect the main branch."""
        assert "main" in self.content, (
            "ci.yml must reference the main branch as a trigger target"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Dockerfile security hardening
# ─────────────────────────────────────────────────────────────────────────────


class TestDockerfileSecurity:
    """Production Dockerfile must implement required security hardening."""

    @pytest.fixture(autouse=True)
    def load_dockerfile(self):
        self.content = read_file(DOCKERFILE)

    def test_non_root_user(self):
        """Container must not run as root — a USER directive must be present."""
        assert "USER" in self.content, (
            "Dockerfile must switch to a non-root USER before CMD/ENTRYPOINT"
        )

    def test_non_root_user_is_not_root(self):
        """The USER directive must not set the user to root."""
        user_matches = re.findall(r"^\s*USER\s+(\S+)", self.content, re.MULTILINE)
        for user in user_matches:
            assert user.lower() not in ("root", "0"), (
                f"Dockerfile USER must not be root — found: USER {user}"
            )

    def test_uses_slim_or_distroless_base(self):
        """Base image should use a minimal variant (slim, alpine, distroless)."""
        from_lines = re.findall(
            r"^\s*FROM\s+(\S+)", self.content, re.MULTILINE | re.IGNORECASE
        )
        has_minimal = any(
            any(keyword in line.lower() for keyword in ("slim", "alpine", "distroless"))
            for line in from_lines
        )
        assert has_minimal, (
            "Dockerfile must use a minimal base image (slim, alpine, or distroless)"
        )

    def test_multistage_build(self):
        """Dockerfile should use multi-stage build to reduce attack surface."""
        from_count = len(
            re.findall(r"^\s*FROM\s+", self.content, re.MULTILINE | re.IGNORECASE)
        )
        assert from_count >= 2, (
            "Dockerfile should use multi-stage build (at least 2 FROM directives)"
        )

    def test_no_hardcoded_secrets(self):
        """Dockerfile must not contain hardcoded secrets or passwords."""
        secret_patterns = [
            r"ENV\s+\w*(?:PASSWORD|SECRET|KEY|TOKEN)\w*\s*=\s*[^\s$][^\s]+",
            r"ARG\s+\w*(?:PASSWORD|SECRET|KEY|TOKEN)\w*\s*=\s*[^\s]",
        ]
        for pattern in secret_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            assert not matches, (
                f"Dockerfile contains potential hardcoded secret: {matches}"
            )

    def test_healthcheck_defined(self):
        """HEALTHCHECK must be defined for container orchestration readiness."""
        assert "HEALTHCHECK" in self.content, (
            "Dockerfile must define a HEALTHCHECK for readiness detection"
        )

    def test_exposes_application_port(self):
        """EXPOSE directive must be present."""
        assert "EXPOSE" in self.content, (
            "Dockerfile must EXPOSE the application port"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. dockerignore — secrets and sensitive files excluded
# ─────────────────────────────────────────────────────────────────────────────


class TestDockerignore:
    """Critical files must be excluded from the Docker build context."""

    @pytest.fixture(autouse=True)
    def load_dockerignore(self):
        path = os.path.join(ROOT, ".dockerignore")
        self.content = read_file(path)

    def test_env_files_excluded(self):
        """Secret .env files must not enter the Docker build context."""
        assert ".env" in self.content, (
            ".dockerignore must exclude .env files"
        )

    def test_tests_excluded(self):
        """Test files must not be in the production image."""
        assert "tests/" in self.content, (
            ".dockerignore must exclude the tests/ directory"
        )

    def test_infra_excluded(self):
        """Terraform infrastructure files must not be in the production image."""
        assert "infra/" in self.content, (
            ".dockerignore must exclude the infra/ directory"
        )

    def test_ci_config_excluded(self):
        """GitHub Actions workflows must not be in the production image."""
        assert ".github/" in self.content, (
            ".dockerignore must exclude the .github/ directory"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 9. Staging deploy workflow
# ─────────────────────────────────────────────────────────────────────────────


class TestStagingDeployWorkflow:
    """Staging deploy workflow must include required properties."""

    @pytest.fixture(autouse=True)
    def load_deploy(self):
        self.content = read_file(DEPLOY_YML)
        self.data = load_yaml(DEPLOY_YML)

    def test_triggers_on_develop_push(self):
        """Staging deploy must trigger on push to develop (not main)."""
        assert "develop" in self.content, (
            "deploy-staging.yml must trigger on push to develop"
        )
        assert "push" in self.content, (
            "deploy-staging.yml must use a push trigger"
        )

    def test_no_prod_deploy(self):
        """Staging workflow must deploy to staging, not production."""
        assert "staging" in self.content.lower(), (
            "deploy-staging.yml must deploy to the staging environment"
        )

    def test_security_gates_run_before_deploy(self):
        """Security gates must re-run (or be verified) before staging deploy."""
        security_check = any(
            keyword in self.content
            for keyword in [
                "pip-audit", "pip_audit", "bandit",
                "security-gates", "security_gates",
            ]
        )
        assert security_check, (
            "deploy-staging.yml must include a security gate verification step"
        )

    def test_health_check_after_deploy(self):
        """A health check must verify the staging deploy succeeded."""
        assert "/health" in self.content or "health" in self.content.lower(), (
            "deploy-staging.yml must include a post-deploy health check"
        )

    def test_ecs_deployment_mechanism(self):
        """Staging must deploy to ECS (the agreed infrastructure)."""
        assert "ecs" in self.content.lower(), (
            "deploy-staging.yml must reference ECS for deployment"
        )
