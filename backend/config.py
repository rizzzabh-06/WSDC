"""
WSDC Configuration — Fail-fast environment validation.

OWASP A05 (Security Misconfiguration): Validates all required secrets at startup.
OWASP A02 (Cryptographic Failures): Enforces TLS on database and Redis connections.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, SecretStr


class Settings(BaseSettings):
    """Validated application settings. App will fail to start if required secrets are missing."""

    # --- Environment ---
    ENVIRONMENT: str = "development"

    # --- Database (Neon Postgres) ---
    DATABASE_URL: str

    # --- Redis (Upstash) ---
    REDIS_URL: str

    # GitHub App config
    APP_ID: Optional[str] = None
    PRIVATE_KEY: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None

    # AI & Analysis config
    GEMINI_API_KEY: Optional[SecretStr] = None
    SLITHER_CMD: str = "slither"

    # --- WSDC API Key (protects internal endpoints) ---
    WSDC_API_KEY: str = ""

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Enforce TLS and asyncpg driver for Postgres connections."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        # In production, enforce SSL
        if "neon.tech" in v and "sslmode=require" not in v:
            raise ValueError(
                "DATABASE_URL must include sslmode=require for Neon connections"
            )
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Enforce TLS for Upstash Redis connections."""
        if not v:
            raise ValueError("REDIS_URL is required")
        # In production, enforce TLS (rediss://)
        if "upstash.io" in v and not v.startswith("rediss://"):
            raise ValueError(
                "REDIS_URL must use rediss:// (TLS) for Upstash connections"
            )
        return v

    @field_validator("WSDC_API_KEY")
    @classmethod
    def validate_api_key_in_production(cls, v: str, info) -> str:
        """Require API key in production."""
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and not v:
            raise ValueError("WSDC_API_KEY is required in production")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


def get_settings() -> Settings:
    """Load and validate settings. Raises ValidationError on missing/invalid config."""
    return Settings()
