"""
Tests for the FastAPI event ingestion service health endpoint.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_health_returns_ok():
    """GET /health should return {"status": "ok"} with HTTP 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_does_not_expose_env_vars():
    """Health endpoint must never return environment variable values."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    response_text = response.text
    # Ensure no common env var patterns are leaked
    assert "DATABASE_URL" not in response_text
    assert "REDIS_URL" not in response_text
    assert "SECRET" not in response_text
    assert "PASSWORD" not in response_text
    assert "postgresql://" not in response_text
