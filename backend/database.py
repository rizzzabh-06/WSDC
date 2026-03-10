"""
WSDC Database — Async SQLAlchemy engine for Neon Postgres.

Security hardening applied:
- OWASP A02: No insecure localhost fallback; TLS enforced via config.py
- OWASP A03: Connection pool limits to prevent connection exhaustion DoS
- OWASP A05: Query echo disabled in production
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_settings

settings = get_settings()

# Convert standard postgres:// URL to asyncpg format if needed
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not db_url.startswith("postgresql+asyncpg://"):
    db_url = "postgresql+asyncpg://" + db_url.split("://", 1)[-1]

engine = create_async_engine(
    db_url,
    # Only echo SQL in development (OWASP A05 — don't leak queries in production)
    echo=not settings.is_production,
    # Connection pool safety (OWASP A04 — prevent DoS via connection exhaustion)
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Health-check connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    """Dependency that yields a database session and ensures cleanup."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
