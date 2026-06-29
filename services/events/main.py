"""
Protego Life Simulator — FastAPI Event Ingestion Microservice

Receives behavioral events from the Next.js frontend and persists them
to TimescaleDB (PostgreSQL). All secrets are injected via environment
variables — never hardcoded.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging — never log env var values
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — startup and shutdown."""
    logger.info("Protego events service starting up")
    # Database connection is lazy — service binds to port before connecting
    # to allow Railway health checks to succeed while DB initializes
    yield
    logger.info("Protego events service shutting down")


app = FastAPI(
    title="Protego Event Ingestion Service",
    description="Behavioral event ingestion microservice for Protego Life Simulator",
    version="0.1.0",
    # Disable docs in production to reduce attack surface
    docs_url="/docs" if os.getenv("NODE_ENV") != "production" else None,
    redoc_url="/redoc" if os.getenv("NODE_ENV") != "production" else None,
    lifespan=lifespan,
)

# CORS — restrict to known origins only
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", summary="Health check")
async def health_check() -> dict[str, str]:
    """
    Returns service health status.
    Never echoes environment variable values in the response body.
    """
    return {"status": "ok"}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Any, exc: Exception) -> JSONResponse:
    """
    Global exception handler — never exposes internal details to clients.
    Full error details are logged server-side only.
    """
    logger.error("Unhandled exception: %s", type(exc).__name__, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )
