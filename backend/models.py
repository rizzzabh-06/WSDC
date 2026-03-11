"""
WSDC Database Models — SQLAlchemy ORM definitions.

Security hardening applied:
- OWASP A01: Safe __repr__ that doesn't expose sensitive fields
- OWASP A03: CheckConstraint on status fields to prevent invalid state injection
"""

import uuid
from sqlalchemy import (
    Column, String, BigInteger, Integer, ForeignKey,
    DateTime, UniqueConstraint, CheckConstraint, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base

# ── Enum Constants ──

VALID_PR_STATUSES = ("pending", "reviewed", "failed")
VALID_FINDING_SEVERITIES = ("critical", "high", "medium", "low", "informational")
VALID_FINDING_STATUSES = ("open", "fixed", "accepted_risk", "false_positive")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id = Column(BigInteger, unique=True, nullable=False)
    owner = Column(String(256), nullable=False)
    name = Column(String(256), nullable=False)
    installation_id = Column(BigInteger, nullable=False)
    installed_at = Column(DateTime(timezone=True), default=func.now())
    config = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)

    # Relationships
    pull_requests = relationship("PullRequest", back_populates="repository")
    protocol_models = relationship("ProtocolModel", back_populates="repository")
    security_history = relationship("SecurityHistory", back_populates="repository")

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, owner={self.owner}, name={self.name})>"


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    pr_number = Column(Integer, nullable=False)
    head_sha = Column(String(40), nullable=False)
    base_sha = Column(String(40), nullable=False)
    status = Column(String(20), nullable=True)
    attack_surface_delta = Column(JSONB, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    repository = relationship("Repository", back_populates="pull_requests")
    findings = relationship("Finding", back_populates="pull_request")

    __table_args__ = (
        UniqueConstraint("repo_id", "pr_number", name="uix_repo_pr"),
        CheckConstraint(
            f"status IS NULL OR status IN {VALID_PR_STATUSES}",
            name="ck_pr_status_valid",
        ),
    )

    def __repr__(self) -> str:
        return f"<PullRequest(id={self.id}, repo_id={self.repo_id}, pr_number={self.pr_number})>"


class Finding(Base):
    """Every security issue detected — maps to PRD Section 7.1 findings table."""
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pr_id = Column(UUID(as_uuid=True), ForeignKey("pull_requests.id"), nullable=False)
    category = Column(String(100), nullable=False)  # 'reentrancy', 'access_control', etc.
    severity = Column(String(20), nullable=False)    # 'critical', 'high', 'medium', 'low'
    file_path = Column(Text, nullable=False)
    line_number = Column(Integer, nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    exploit_scenario = Column(Text, nullable=True)
    fix_suggestions = Column(JSONB, nullable=True)   # [{option, code, tradeoff}]
    owasp_mapping = Column(ARRAY(String), nullable=True)  # ['SC-05', 'A01']
    status = Column(String(20), nullable=True, default="open")
    resolution_comment = Column(Text, nullable=True)
    github_comment_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    pull_request = relationship("PullRequest", back_populates="findings")

    __table_args__ = (
        CheckConstraint(
            f"severity IN {VALID_FINDING_SEVERITIES}",
            name="ck_finding_severity_valid",
        ),
        CheckConstraint(
            f"status IS NULL OR status IN {VALID_FINDING_STATUSES}",
            name="ck_finding_status_valid",
        ),
    )

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, category={self.category}, severity={self.severity})>"


class ProtocolModel(Base):
    """Trust boundaries + architecture per repo — maps to PRD Section 7.1 protocol_models table."""
    __tablename__ = "protocol_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    contracts = Column(JSONB, nullable=False)          # [{name, path, roles: []}]
    trust_edges = Column(JSONB, nullable=True)          # [{from, to, trust_level, reason}]
    invariants = Column(ARRAY(Text), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    repository = relationship("Repository", back_populates="protocol_models")

    def __repr__(self) -> str:
        return f"<ProtocolModel(id={self.id}, repo_id={self.repo_id})>"


class SecurityHistory(Base):
    """Aggregated vulnerability patterns per repo — maps to PRD Section 7.1 security_history table."""
    __tablename__ = "security_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    category = Column(String(100), nullable=False)
    occurrences = Column(Integer, default=1)
    last_seen_pr_id = Column(UUID(as_uuid=True), ForeignKey("pull_requests.id"), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=func.now())
    last_seen_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    repository = relationship("Repository", back_populates="security_history")
    last_seen_pr = relationship("PullRequest")

    def __repr__(self) -> str:
        return f"<SecurityHistory(id={self.id}, repo_id={self.repo_id}, category={self.category})>"
