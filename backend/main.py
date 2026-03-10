"""
WSDC Backend — FastAPI entrypoint.

Security hardening applied:
- OWASP A01: API key auth on protected endpoints
- OWASP A03: Strict Pydantic input validation with regex constraints
- OWASP A04: CORS policy, rate limiting, request size limits
- OWASP A05: Docs disabled in production, no stack traces in errors
- OWASP A09: Structured logging, no secret leakage
"""

import os
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import get_settings
from security import (
    verify_api_key,
    SecurityHeadersMiddleware,
    validate_repo_id,
    validate_git_sha,
    sanitize_log_message,
)

# ──────────────────────────────────────────────
# Logging (OWASP A09)
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wsdc.api")

# ──────────────────────────────────────────────
# Rate Limiter (OWASP A04)
# ──────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

# ──────────────────────────────────────────────
# App Lifecycle
# ──────────────────────────────────────────────

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("WSDC Backend starting (env=%s)", settings.ENVIRONMENT)
    yield
    logger.info("WSDC Backend shutting down")


# ──────────────────────────────────────────────
# App Initialization (OWASP A05)
# ──────────────────────────────────────────────

app = FastAPI(
    title="WSDC Backend",
    description="Web3 Security Development Co-Pilot API",
    version="1.0.0",
    # Disable interactive docs in production to reduce attack surface
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ──────────────────────────────────────────────
# Middleware Stack
# ──────────────────────────────────────────────

# Security headers (OWASP A04/A05)
app.add_middleware(SecurityHeadersMiddleware)

# CORS — explicit origins only (OWASP A01/A05)
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else [],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# ──────────────────────────────────────────────
# Global Exception Handler (OWASP A05, A09)
# ──────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler that prevents stack traces from leaking to clients.
    Logs the real error server-side for debugging.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception [request_id=%s]: %s",
        request_id,
        sanitize_log_message(str(exc)),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# ──────────────────────────────────────────────
# Request ID Middleware (OWASP A09)
# ──────────────────────────────────────────────


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Assign a unique request ID for tracing."""
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# ──────────────────────────────────────────────
# Health Check (unauthenticated)
# ──────────────────────────────────────────────


@app.get("/health")
@limiter.limit("30/minute")
async def health_check(request: Request):
    """Public health endpoint — intentionally minimal to avoid information leakage."""
    return {"status": "ok"}


# ──────────────────────────────────────────────
# Request Models (OWASP A03 — strict validation)
# ──────────────────────────────────────────────


class ReviewTrigger(BaseModel):
    """Validated review request. Prevents injection and SSRF via strict format checks."""

    repo_id: str = Field(
        ...,
        min_length=3,
        max_length=256,
        description="GitHub repo full_name (owner/repo)",
        examples=["owner/repo-name"],
    )
    pr_number: int = Field(
        ...,
        gt=0,
        le=999999,
        description="PR number (positive integer)",
    )
    head_sha: str = Field(
        ...,
        min_length=7,
        max_length=40,
        description="Head commit SHA (7-40 hex chars)",
    )
    base_sha: str = Field(
        ...,
        min_length=7,
        max_length=40,
        description="Base commit SHA (7-40 hex chars)",
    )

    @field_validator("repo_id")
    @classmethod
    def check_repo_id_format(cls, v: str) -> str:
        if not validate_repo_id(v):
            raise ValueError(
                "repo_id must match GitHub owner/repo format (alphanumeric, hyphens, dots, underscores)"
            )
        return v

    @field_validator("head_sha", "base_sha")
    @classmethod
    def check_sha_format(cls, v: str) -> str:
        if not validate_git_sha(v):
            raise ValueError("SHA must be 7-40 lowercase hex characters")
        return v


# ──────────────────────────────────────────────
# Protected Endpoints (OWASP A01)
# ──────────────────────────────────────────────


@app.post("/api/reviews/trigger")
@limiter.limit("60/minute")
async def trigger_review(
    request: Request,
    payload: ReviewTrigger,
    api_key: str = Depends(verify_api_key),
):
    """
    Start a security review for a PR.
    Protected by API key authentication.

    In the final architecture:
    GitHub App -> Redis -> Celery Worker -> triggers review pipeline.
    """
    logger.info(
        "Review triggered [request_id=%s] PR #%d in %s",
        request.state.request_id,
        payload.pr_number,
        payload.repo_id,
    )

    # TODO: Enqueue actual AST Diffing and Slither tasks here

    return {
        "status": "accepted",
        "job_id": str(uuid.uuid4()),
        "request_id": request.state.request_id,
    }


# ──────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.is_production,
        # Don't show access logs with sensitive headers
        access_log=not settings.is_production,
    )
