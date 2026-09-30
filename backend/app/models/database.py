"""
Repository Intelligence Engine — SQLAlchemy Models
All PostgreSQL table definitions.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

# DB-agnostic column types supporting both PostgreSQL and SQLite
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")
UUID_TYPE = PG_UUID(as_uuid=True).with_variant(Uuid(as_uuid=True), "sqlite")
from sqlalchemy.orm import relationship

from app.core.database import Base


# ── Enums ──────────────────────────────────────────────────


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    BUILDING_GRAPH = "building_graph"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingType(str, enum.Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    TECHNICAL_DEBT = "technical_debt"
    DOCUMENTATION = "documentation"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ── Models ─────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    api_key = Column(String(255), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="projects")
    repositories = relationship("Repository", back_populates="project")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID_TYPE, ForeignKey("projects.id"), nullable=True)
    github_url = Column(String(512), nullable=False)
    name = Column(String(255), nullable=False)
    default_branch = Column(String(255), default="main")
    clone_path = Column(String(1024), nullable=True)
    languages = Column(JSON_TYPE, default=list)
    frameworks = Column(JSON_TYPE, default=list)
    package_managers = Column(JSON_TYPE, default=list)
    is_monorepo = Column(Boolean, default=False)
    total_files = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    health_score = Column(Float, nullable=True)
    metadata_ = Column("metadata", JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="repositories")
    scan_jobs = relationship("ScanJob", back_populates="repository", order_by="ScanJob.created_at.desc()")
    findings = relationship("Finding", back_populates="repository")


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID_TYPE, ForeignKey("repositories.id"), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)
    current_phase = Column(String(100), nullable=True)
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    celery_task_id = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    results_summary = Column(JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    repository = relationship("Repository", back_populates="scan_jobs")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    repository_id = Column(UUID_TYPE, ForeignKey("repositories.id"), nullable=False)
    scan_job_id = Column(UUID_TYPE, ForeignKey("scan_jobs.id"), nullable=True)
    finding_type = Column(Enum(FindingType), nullable=False)
    severity = Column(Enum(Severity), default=Severity.INFO)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(1024), nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    rule_id = Column(String(255), nullable=True)
    tool = Column(String(100), nullable=True)  # semgrep, codeql, joern, custom
    recommendation = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON_TYPE, default=dict)
    graph_node_id = Column(String(255), nullable=True)  # links to Neo4j node
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    repository = relationship("Repository", back_populates="findings")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON_TYPE, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
