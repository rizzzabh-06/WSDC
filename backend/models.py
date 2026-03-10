"""
WSDC Database Models — SQLAlchemy ORM definitions.

Security hardening applied:
- OWASP A01: Safe __repr__ that doesn't expose sensitive fields
- OWASP A03: CheckConstraint on status fields to prevent invalid state injection
"""

import uuid
from sqlalchemy import (
    Column, String, BigInteger, Integer, ForeignKey,
    DateTime, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base

# Valid status values for pull request reviews
VALID_PR_STATUSES = ("pending", "reviewed", "failed")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id = Column(BigInteger, unique=True, nullable=False)
    owner = Column(String(256), nullable=False)  # Length-limited to prevent abuse
    name = Column(String(256), nullable=False)
    installation_id = Column(BigInteger, nullable=False)
    installed_at = Column(DateTime(timezone=True), default=func.now())
    config = Column(JSONB, nullable=True)     # .wsdc/protocol.yaml contents
    metadata_ = Column("metadata", JSONB, nullable=True)  # Renamed to avoid shadowing builtin

    # Relationships
    pull_requests = relationship("PullRequest", back_populates="repository")

    def __repr__(self) -> str:
        """Safe repr — never exposes config or metadata in logs."""
        return f"<Repository(id={self.id}, owner={self.owner}, name={self.name})>"


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    pr_number = Column(Integer, nullable=False)
    head_sha = Column(String(40), nullable=False)  # Git SHA max 40 chars
    base_sha = Column(String(40), nullable=False)
    status = Column(String(20), nullable=True)
    attack_surface_delta = Column(JSONB, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    repository = relationship("Repository", back_populates="pull_requests")

    __table_args__ = (
        UniqueConstraint("repo_id", "pr_number", name="uix_repo_pr"),
        # OWASP A03 — Constrain status to valid enum values only
        CheckConstraint(
            f"status IS NULL OR status IN {VALID_PR_STATUSES}",
            name="ck_pr_status_valid",
        ),
    )

    def __repr__(self) -> str:
        """Safe repr — shows identifiers only, no SHAs."""
        return f"<PullRequest(id={self.id}, repo_id={self.repo_id}, pr_number={self.pr_number})>"
