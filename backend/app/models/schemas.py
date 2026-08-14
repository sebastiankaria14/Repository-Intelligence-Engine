"""
Repository Intelligence Engine — Pydantic Schemas
Request/response models for the API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# ── Repository ─────────────────────────────────────────────


class RepositoryCreate(BaseModel):
    github_url: str = Field(..., description="GitHub repository URL to analyze")
    project_name: Optional[str] = Field(None, description="Optional project name")


class RepositoryResponse(BaseModel):
    id: UUID
    github_url: str
    name: str
    default_branch: str | None = None
    languages: list[str] | None = None
    frameworks: list[str] | None = None
    package_managers: list[str] | None = None
    is_monorepo: bool | None = None
    total_files: int | None = None
    total_lines: int | None = None
    health_score: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RepositoryListResponse(BaseModel):
    repositories: List[RepositoryResponse]
    total: int


# ── Scan Job ───────────────────────────────────────────────


class ScanJobResponse(BaseModel):
    id: UUID
    repository_id: UUID
    status: str
    current_phase: Optional[str]
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    results_summary: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Architecture ───────────────────────────────────────────


class ArchitectureLayer(BaseModel):
    name: str
    description: str
    components: List[str]
    file_count: int


class ArchitectureResponse(BaseModel):
    pattern: str  # MVC, layered, hexagonal, microservices, etc.
    confidence: float
    layers: List[ArchitectureLayer]
    diagram: Dict[str, Any]  # React Flow compatible nodes/edges


# ── API Discovery ──────────────────────────────────────────


class APIEndpoint(BaseModel):
    method: str  # GET, POST, PUT, DELETE, etc.
    path: str
    handler: str
    file_path: str
    line_number: int
    parameters: List[Dict[str, str]]
    auth_required: bool
    middleware: List[str]
    description: Optional[str] = None


class APIDiscoveryResponse(BaseModel):
    endpoints: List[APIEndpoint]
    total: int
    frameworks_detected: List[str]


# ── Database Intelligence ──────────────────────────────────


class DatabaseTable(BaseModel):
    name: str
    columns: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, str]]
    indexes: List[str]
    source_file: str
    orm_model: Optional[str] = None


class DatabaseResponse(BaseModel):
    tables: List[DatabaseTable]
    relationships: List[Dict[str, Any]]
    migrations: List[Dict[str, str]]
    er_diagram: Dict[str, Any]


# ── Dependencies ───────────────────────────────────────────


class DependencyNode(BaseModel):
    name: str
    version: Optional[str]
    type: str  # runtime, dev, peer
    source: str  # package.json, requirements.txt, pom.xml


class DependencyResponse(BaseModel):
    packages: List[DependencyNode]
    service_graph: Dict[str, Any]  # Internal service dependencies
    circular_dependencies: List[List[str]]
    total: int


# ── Git Intelligence ───────────────────────────────────────


class ContributorStats(BaseModel):
    name: str
    email: str
    commits: int
    lines_added: int
    lines_deleted: int
    first_commit: datetime
    last_commit: datetime
    owned_files: List[str]


class GitInsightsResponse(BaseModel):
    total_commits: int
    total_contributors: int
    contributors: List[ContributorStats]
    hotspot_files: List[Dict[str, Any]]
    change_coupling: List[Dict[str, Any]]
    commit_frequency: Dict[str, int]  # date → count


# ── Security ───────────────────────────────────────────────


class SecurityFinding(BaseModel):
    id: UUID
    severity: str
    title: str
    description: str
    file_path: str
    line_start: int
    line_end: Optional[int]
    rule_id: str
    tool: str
    recommendation: Optional[str]
    affected_services: List[str]


class SecurityResponse(BaseModel):
    findings: List[SecurityFinding]
    summary: Dict[str, int]  # severity → count
    risk_score: float


# ── Performance ────────────────────────────────────────────


class PerformanceFinding(BaseModel):
    type: str  # n_plus_one, large_object, circular_dep, heavy_endpoint
    severity: str
    title: str
    description: str
    file_path: str
    line_number: Optional[int]
    recommendation: str


class PerformanceResponse(BaseModel):
    findings: List[PerformanceFinding]
    summary: Dict[str, int]


# ── Technical Debt ─────────────────────────────────────────


class DebtItem(BaseModel):
    type: str  # dead_code, duplication, god_class, long_method, legacy
    severity: str
    title: str
    description: str
    file_path: str
    effort_hours: float
    priority: int
    risk: str


class TechnicalDebtResponse(BaseModel):
    items: List[DebtItem]
    total_effort_hours: float
    debt_score: float
    summary: Dict[str, int]


# ── Knowledge Graph ────────────────────────────────────────


class GraphNode(BaseModel):
    id: str
    label: str  # Node type
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # Relationship type
    properties: Dict[str, Any] = {}


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int


# ── AI Chat ────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    model: Optional[str] = None  # Override model selection


class Citation(BaseModel):
    type: str  # file, graph_node, commit, doc
    reference: str
    snippet: Optional[str] = None
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    model_used: str
    reasoning_type: str  # code, architecture, security, general


# ── Health ─────────────────────────────────────────────────


class ServiceHealth(BaseModel):
    name: str
    status: str  # healthy, unhealthy, unavailable
    latency_ms: Optional[float] = None
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: List[ServiceHealth]
