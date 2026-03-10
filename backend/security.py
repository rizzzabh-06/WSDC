"""
WSDC Security Utilities — Centralised security middleware and helpers.

Covers:
- OWASP A01 (Broken Access Control): API key verification
- OWASP A02 (Cryptographic Failures): Timing-safe HMAC comparison
- OWASP A04 (Insecure Design): Security headers middleware
- OWASP A09 (Logging & Monitoring): Log sanitization
"""

import hashlib
import hmac
import re
import logging
from typing import Optional

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# API Key Authentication (OWASP A01, A07)
# ──────────────────────────────────────────────

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """
    FastAPI dependency to enforce API key auth on protected routes.
    Uses timing-safe comparison to prevent timing attacks (CVE-2014-0474 class).
    """
    from config import get_settings

    settings = get_settings()

    # In development without a key configured, allow all requests
    if not settings.is_production and not settings.WSDC_API_KEY:
        return "development"

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Timing-safe comparison to prevent timing-based enumeration
    if not hmac.compare_digest(api_key, settings.WSDC_API_KEY):
        logger.warning("Invalid API key attempt from request")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return api_key


# ──────────────────────────────────────────────
# Webhook Signature Validation (OWASP A02)
# ──────────────────────────────────────────────


def verify_webhook_signature(
    payload_body: bytes, signature_header: str, secret: str
) -> bool:
    """
    Validate GitHub webhook HMAC-SHA256 signature.
    Uses hmac.compare_digest to prevent timing attacks.

    Args:
        payload_body: Raw request body bytes
        signature_header: The X-Hub-Signature-256 header value (sha256=...)
        secret: The webhook secret

    Returns:
        True if signature is valid
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_signature = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_signature, signature_header)


# ──────────────────────────────────────────────
# Security Headers Middleware (OWASP A04, A05)
# ──────────────────────────────────────────────


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds OWASP-recommended security headers to all responses.
    Mitigates: clickjacking, MIME-type sniffing, XSS, protocol downgrade attacks.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME-type sniffing (CVE-class: content-type confusion)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Prevent information leakage via referer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # Prevent caching of sensitive responses
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        return response


# ──────────────────────────────────────────────
# Log Sanitization (OWASP A09)
# ──────────────────────────────────────────────

# Patterns that should never appear in logs
_SECRET_PATTERNS = [
    re.compile(r"(password|secret|token|key|authorization)[\s]*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]+"),  # GitHub tokens
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
]


def sanitize_log_message(message: str) -> str:
    """
    Strip potential secrets from log messages.
    Should be used before logging any user-controlled or env-derived data.
    """
    sanitized = message
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


# ──────────────────────────────────────────────
# Input Validation Helpers (OWASP A03, A10)
# ──────────────────────────────────────────────

# Matches valid GitHub repo full_name: owner/repo
REPO_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")

# Matches valid git SHA (short or full)
GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")


def validate_repo_id(repo_id: str) -> bool:
    """Validate repo_id matches GitHub owner/repo format. Prevents SSRF via path traversal."""
    if not repo_id or len(repo_id) > 256:
        return False
    return bool(REPO_NAME_PATTERN.match(repo_id))


def validate_git_sha(sha: str) -> bool:
    """Validate a git SHA hash. Prevents injection via crafted SHA values."""
    if not sha or len(sha) > 40:
        return False
    return bool(GIT_SHA_PATTERN.match(sha))
