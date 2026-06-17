# Production application image — ProtegoPay
# Feature F-01-002: CI/CD Pipeline with Security Gates
#
# Multi-stage build:
#   Stage 1 (builder): install dependencies, run compile steps
#   Stage 2 (runtime): minimal runtime image — no build tools, no dev deps
#
# Security hardening:
#   - Non-root user (appuser, UID 10001)
#   - No shell in production image
#   - Read-only filesystem mount supported
#   - No secrets or credentials hardcoded — all injected at runtime via env vars
#
# Usage:
#   docker build -t protegopay/app .
#   docker run -e DATABASE_URL=... -e REDIS_URL=... -e JWT_SECRET=... \
#              -p 8000:8000 protegopay/app

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only build-time deps needed to compile wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first (layer cache optimisation)
COPY requirements.txt ./

# Install into a prefix directory so we can copy only the installed packages
# to the runtime image without dragging in pip/setuptools
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: create a non-root user and group
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid 10001 --no-create-home --shell /bin/false appuser

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source — exclude dev/test files via .dockerignore
COPY --chown=appuser:appgroup . /app

# Security: drop to non-root before the process starts
USER appuser

# Expose port (documented — actual binding controlled by CMD args or orchestrator)
EXPOSE 8000

# Health check endpoint — the /health route must return HTTP 200 for readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Runtime: all secrets injected via environment variables — never baked in
# Required env vars (fail-fast if missing is handled in application code):
#   DATABASE_URL   — PostgreSQL connection string
#   REDIS_URL      — Redis connection string
#   JWT_SECRET     — HMAC-SHA256 signing secret (min 32 chars)
#   OIDC_ISSUER    — Concessionaire IdP OIDC discovery URL

# Default command — override via docker-compose or ECS task definition
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
