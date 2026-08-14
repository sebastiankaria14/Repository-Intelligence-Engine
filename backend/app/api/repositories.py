"""
Repository Intelligence Engine — Repository Router
CRUD + analysis endpoints for repositories.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.database import Repository, ScanJob, ScanStatus
from app.models.schemas import (
    APIDiscoveryResponse,
    ArchitectureResponse,
    ChatRequest,
    ChatResponse,
    DatabaseResponse,
    DependencyResponse,
    GitInsightsResponse,
    GraphResponse,
    PerformanceResponse,
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    ScanJobResponse,
    SecurityResponse,
    TechnicalDebtResponse,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])
log = get_logger(__name__)


# ── Repository CRUD ────────────────────────────────────────


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    payload: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a GitHub repository URL for analysis.
    Kicks off the full Celery analysis pipeline.
    """
    try:
        # Extract repo name from URL
        url = payload.github_url.rstrip("/")
        name = url.split("/")[-1].replace(".git", "")

        # Create repository record
        repo = Repository(
            github_url=payload.github_url,
            name=name,
        )
        db.add(repo)
        await db.flush()

        # Create initial scan job
        scan_job = ScanJob(
            repository_id=repo.id,
            status=ScanStatus.PENDING,
            current_phase="queued",
            progress=0.0,
        )
        db.add(scan_job)
        await db.flush()

        # Kick off Celery pipeline
        try:
            from app.tasks.pipeline import run_analysis_pipeline

            task = run_analysis_pipeline.delay(str(repo.id), str(scan_job.id))
            scan_job.celery_task_id = task.id
            log.info("pipeline_started", repo_id=str(repo.id), task_id=task.id)
        except Exception as e:
            log.error("pipeline_start_failed", error=str(e))
            scan_job.status = ScanStatus.FAILED
            scan_job.error_message = f"Failed to start pipeline: {e}"

        await db.commit()
        await db.refresh(repo)

        # Manual serialization to bypass Pydantic validation issues
        return {
            "id": repo.id,
            "github_url": repo.github_url,
            "name": repo.name,
            "default_branch": getattr(repo, "default_branch", None),
            "languages": getattr(repo, "languages", None),
            "frameworks": getattr(repo, "frameworks", None),
            "package_managers": getattr(repo, "package_managers", None),
            "is_monorepo": getattr(repo, "is_monorepo", None),
            "total_files": getattr(repo, "total_files", None),
            "total_lines": getattr(repo, "total_lines", None),
            "health_score": getattr(repo, "health_score", None),
            "created_at": getattr(repo, "created_at", None),
            "updated_at": getattr(repo, "updated_at", None),
        }
    except Exception as e:
        log.error("create_repo_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all analyzed repositories."""
    result = await db.execute(
        select(Repository).offset(skip).limit(limit).order_by(Repository.created_at.desc())
    )
    repos = result.scalars().all()

    count_result = await db.execute(select(Repository))
    total = len(count_result.scalars().all())

    return RepositoryListResponse(
        repositories=[RepositoryResponse.model_validate(r) for r in repos],
        total=total,
    )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single repository by ID."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositoryResponse.model_validate(repo)


# ── Scan Status ────────────────────────────────────────────


@router.get("/{repo_id}/status", response_model=ScanJobResponse)
async def get_scan_status(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get the latest scan job status for a repository."""
    result = await db.execute(
        select(ScanJob)
        .where(ScanJob.repository_id == repo_id)
        .order_by(ScanJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="No scan jobs found for this repository")
    return ScanJobResponse.model_validate(job)


# ── Analysis Endpoints ─────────────────────────────────────
# These return actual analysis results stored during the pipeline.
# Each will be fully implemented in later phases.


@router.get("/{repo_id}/architecture")
async def get_architecture(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "architecture" in job.results_summary:
        return job.results_summary["architecture"]
    return {
        "repository_id": str(repo_id),
        "pattern": "pending_analysis",
        "confidence": 0.0,
        "layers": [],
        "diagram": {"nodes": [], "edges": []},
    }


@router.get("/{repo_id}/apis")
async def get_apis(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "apis" in job.results_summary:
        return job.results_summary["apis"]
    return {
        "repository_id": str(repo_id),
        "endpoints": [],
        "total": 0,
        "frameworks_detected": [],
    }


@router.get("/{repo_id}/database")
async def get_database(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "database" in job.results_summary:
        return job.results_summary["database"]
    return {
        "repository_id": str(repo_id),
        "tables": [],
        "relationships": [],
        "migrations": [],
        "er_diagram": {"nodes": [], "edges": []},
    }


@router.get("/{repo_id}/dependencies")
async def get_dependencies(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "dependencies" in job.results_summary:
        return job.results_summary["dependencies"]
    return {
        "repository_id": str(repo_id),
        "packages": [],
        "service_graph": {"nodes": [], "edges": []},
        "circular_dependencies": [],
        "total": 0,
    }


@router.get("/{repo_id}/git-insights")
async def get_git_insights(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "git" in job.results_summary:
        return job.results_summary["git"]
    return {
        "repository_id": str(repo_id),
        "total_commits": 0,
        "total_contributors": 0,
        "contributors": [],
        "hotspot_files": [],
        "change_coupling": [],
        "commit_frequency": {},
    }


@router.get("/{repo_id}/security")
async def get_security(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "security" in job.results_summary:
        return job.results_summary["security"]
    return {
        "repository_id": str(repo_id),
        "findings": [],
        "summary": {},
        "risk_score": 0.0,
    }


@router.get("/{repo_id}/performance")
async def get_performance(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "performance" in job.results_summary:
        return job.results_summary["performance"]
    return {
        "repository_id": str(repo_id),
        "findings": [],
        "summary": {},
    }


@router.get("/{repo_id}/technical-debt")
async def get_technical_debt(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    if job and job.results_summary and "tech_debt" in job.results_summary:
        return job.results_summary["tech_debt"]
    return {
        "repository_id": str(repo_id),
        "items": [],
        "total_effort_hours": 0.0,
        "debt_score": 0.0,
        "summary": {},
    }


@router.get("/{repo_id}/graph")
async def get_graph(
    repo_id: UUID,
    node_type: Optional[str] = Query(None, description="Filter by node label"),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Knowledge graph — Cytoscape.js-compatible nodes and edges."""
    repo = await _get_repo_or_404(repo_id, db)
    try:
        from app.graph.neo4j_repository import get_graph_repository
        graph_repo = await get_graph_repository()
        subgraph = await graph_repo.get_subgraph(str(repo_id), node_type, limit)
        nodes = [
            {
                "id": n.id,
                "label": n.labels[0] if n.labels else "unknown",
                "properties": n.properties,
            }
            for n in subgraph.nodes
        ]
        edges = [
            {
                "source": r.source_id,
                "target": r.target_id,
                "type": r.type,
                "properties": r.properties,
            }
            for r in subgraph.relationships
        ]
        return {
            "repository_id": str(repo_id),
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }
    except Exception as exc:  # noqa: BLE001
        log.error("graph_query_failed", repo_id=str(repo_id), error=str(exc))
        return {
            "repository_id": str(repo_id),
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
        }


@router.post("/{repo_id}/chat", response_model=ChatResponse)
async def chat(
    repo_id: UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """AI chat grounded in the knowledge graph, vector search, and Meilisearch."""
    repo = await _get_repo_or_404(repo_id, db)

    from app.ai.rag import RAGOrchestrator

    orchestrator = RAGOrchestrator()
    try:
        result = await orchestrator.answer(
            payload.message,
            payload.history or [],
            str(repo_id),
            payload.model,
        )
        return ChatResponse(
            answer=result.answer,
            citations=result.citations,
            model_used=result.model_used,
            reasoning_type=result.reasoning_type,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("chat_endpoint_failed", repo_id=str(repo_id), error=str(exc))
        return ChatResponse(
            answer=(
                "Sorry, I couldn't process that request. The AI backend may not "
                "be available. Please ensure the analysis pipeline has completed "
                "and the supporting services are running."
            ),
            citations=[],
            model_used="none",
            reasoning_type="general",
        )


# ── Helpers ────────────────────────────────────────────────


async def _get_repo_or_404(repo_id: UUID, db: AsyncSession) -> Repository:
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


async def _get_latest_scan_job(repo_id: UUID, db: AsyncSession) -> ScanJob | None:
    result = await db.execute(
        select(ScanJob)
        .where(ScanJob.repository_id == repo_id)
        .order_by(ScanJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
