"""
Repository Intelligence Engine — Repository Router
CRUD + analysis endpoints for repositories.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
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

        # Kick off Local in-process async pipeline
        from app.tasks.local_runner import run_pipeline_async

        asyncio.create_task(
            run_pipeline_async(str(repo.id), str(scan_job.id), payload.github_url)
        )
        log.info("local_pipeline_dispatched", repo_id=str(repo.id))

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
    arch_data = None
    if job and job.results_summary and "architecture" in job.results_summary:
        arch_data = job.results_summary["architecture"]

    diagram = arch_data.get("diagram", {}) if isinstance(arch_data, dict) else {}
    nodes = diagram.get("nodes", [])
    is_legacy = len(nodes) <= 3 or any(n.get("type") != "componentNode" for n in nodes)

    if (not arch_data or is_legacy) and repo.clone_path and Path(repo.clone_path).exists():
        try:
            from app.tasks.clone import enumerate_files
            from app.parsing.registry import parser_registry
            from app.analysis.architecture import analyze_architecture

            repo_path = Path(repo.clone_path)
            files = enumerate_files(repo_path)
            all_symbols = []
            all_imports = []

            for f_info in files[:200]:
                rel_path = f_info["path"]
                if not parser_registry.get_parser(rel_path):
                    continue
                try:
                    src = (repo_path / rel_path).read_text(encoding="utf-8", errors="replace")
                    res = parser_registry.parse_file(rel_path, src)
                    if res:
                        all_symbols.extend([{"name": s.name, "type": s.type, "file_path": s.file_path, "line_start": s.line_start, "line_end": s.line_end, "signature": s.signature, "parent": s.parent, "visibility": s.visibility} for s in res.symbols])
                        all_imports.extend([{"module": imp.module, "name": imp.name, "file_path": res.file_path} for imp in res.imports])
                except Exception:
                    pass

            new_arch = analyze_architecture(files, all_symbols, all_imports, repo.languages or [])
            if job:
                new_summary = dict(job.results_summary or {})
                new_summary["architecture"] = new_arch
                job.results_summary = new_summary
                await db.commit()
            arch_data = new_arch
        except Exception as e:
            log.warning("architecture_rebuild_failed", error=str(e))

    if arch_data:
        res_dict = dict(arch_data) if isinstance(arch_data, dict) else {}
        res_dict.setdefault("repository_id", str(repo_id))
        return res_dict

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
    db_data = job.results_summary.get("database") if (job and job.results_summary) else None

    # On-the-fly regeneration if missing or tables empty and clone path exists
    has_tables = bool(db_data and db_data.get("tables"))
    if not has_tables and repo.clone_path and Path(repo.clone_path).exists():
        try:
            from app.analysis.database_intel import analyze_database
            from app.parsing.registry import parser_registry
            from app.tasks.clone import enumerate_files

            repo_path = Path(repo.clone_path)
            files = enumerate_files(repo_path)
            all_symbols = []
            all_imports = []

            for file_info in files:
                rel_path = file_info["path"]
                if not parser_registry.get_parser(rel_path) or file_info.get("size_bytes", 0) > 1_000_000:
                    continue
                abs_path = repo_path / rel_path
                try:
                    source = abs_path.read_text(encoding="utf-8", errors="replace")
                    res = parser_registry.parse_file(rel_path, source)
                    if res:
                        all_symbols.extend([
                            {"name": s.name, "type": s.type, "file_path": s.file_path, "signature": s.signature, "parent": s.parent}
                            for s in res.symbols
                        ])
                        all_imports.extend([
                            {"module": imp.module, "name": imp.name, "file_path": res.file_path}
                            for imp in res.imports
                        ])
                except Exception:
                    pass

            new_db = analyze_database(files, all_symbols, all_imports)
            if job:
                new_summary = dict(job.results_summary or {})
                new_summary["database"] = new_db
                job.results_summary = new_summary
                await db.commit()
            db_data = new_db
        except Exception as e:
            log.warning("database_intel_rebuild_failed", error=str(e))

    if db_data:
        res = dict(db_data)
        res.setdefault("repository_id", str(repo_id))
        tables = res.get("tables") or []
        tables_by_name = {t["name"]: t for t in tables}

        er_diag = dict(res.get("er_diagram") or {})
        nodes = list(er_diag.get("nodes") or [])

        # If diagram nodes are missing but tables exist, build nodes
        if not nodes and tables:
            from app.analysis.database_intel import _build_er_diagram
            er_diag = _build_er_diagram(tables, res.get("relationships") or [])
            nodes = list(er_diag.get("nodes") or [])

        for node in nodes:
            node["type"] = "entityNode"
            node_id = node.get("id")
            if node_id in tables_by_name:
                node.setdefault("data", {})
                node["data"]["table"] = tables_by_name[node_id]
        res["er_diagram"] = er_diag
        return res

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
    dep_data = job.results_summary.get("dependencies") if (job and job.results_summary) else None

    # On-the-fly regeneration if missing or service_graph is empty and clone path exists
    service_nodes = (dep_data.get("service_graph") or {}).get("nodes", []) if dep_data else []
    if (not dep_data or not service_nodes) and repo.clone_path and Path(repo.clone_path).exists():
        try:
            from app.analysis.dependency_intel import analyze_dependencies
            from app.parsing.registry import parser_registry
            from app.tasks.clone import enumerate_files

            repo_path = Path(repo.clone_path)
            files = enumerate_files(repo_path)
            all_imports = []

            for file_info in files:
                rel_path = file_info["path"]
                if not parser_registry.get_parser(rel_path) or file_info.get("size_bytes", 0) > 1_000_000:
                    continue
                abs_path = repo_path / rel_path
                try:
                    source = abs_path.read_text(encoding="utf-8", errors="replace")
                    res = parser_registry.parse_file(rel_path, source)
                    if res:
                        all_imports.extend([
                            {
                                "module": imp.module,
                                "name": imp.name,
                                "file_path": res.file_path,
                                "is_relative": getattr(imp, "is_relative", False),
                            }
                            for imp in res.imports
                        ])
                except Exception:
                    pass

            new_deps = analyze_dependencies(str(repo_path), files, all_imports)
            if job:
                new_summary = dict(job.results_summary or {})
                new_summary["dependencies"] = new_deps
                job.results_summary = new_summary
                await db.commit()
            dep_data = new_deps
        except Exception as e:
            log.warning("dependencies_rebuild_failed", error=str(e))

    if dep_data:
        res = dict(dep_data)
        res.setdefault("repository_id", str(repo_id))
        return res

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
        from app.graph import get_graph_repository
        graph_repo = await get_graph_repository()
        subgraph = await graph_repo.get_subgraph(str(repo_id), [node_type] if node_type else None, limit)

        # Reconstruct on demand if in-memory graph was lost (e.g. server restart)
        if len(subgraph.nodes) == 0 and repo.clone_path and Path(repo.clone_path).exists():
            log.info("reconstructing_graph_on_demand", repo_id=str(repo_id))
            from app.tasks.local_runner import build_in_memory_graph
            from app.tasks.clone import enumerate_files
            from app.parsing.registry import parser_registry

            repo_path = Path(repo.clone_path)
            files = enumerate_files(repo_path)
            all_symbols = []
            all_imports = []
            all_calls = []

            for f_info in files[:120]:
                rel_path = f_info["path"]
                if not parser_registry.get_parser(rel_path):
                    continue
                try:
                    src = (repo_path / rel_path).read_text(encoding="utf-8", errors="replace")
                    res = parser_registry.parse_file(rel_path, src)
                    if res:
                        all_symbols.extend([{"name": s.name, "type": s.type, "file_path": s.file_path, "line_start": s.line_start, "line_end": s.line_end, "signature": s.signature, "parent": s.parent, "visibility": s.visibility} for s in res.symbols])
                        all_imports.extend([{"module": imp.module, "name": imp.name, "file_path": res.file_path} for imp in res.imports])
                        all_calls.extend([{"caller": c.caller, "callee": c.callee, "file_path": c.file_path, "line_number": c.line_number} for c in res.calls])
                except Exception:
                    pass

            await build_in_memory_graph(str(repo_id), files, all_symbols, all_imports, all_calls)
            subgraph = await graph_repo.get_subgraph(str(repo_id), [node_type] if node_type else None, limit)
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
    """Local offline AI chat grounded in the knowledge graph and AST analysis."""
    repo = await _get_repo_or_404(repo_id, db)
    job = await _get_latest_scan_job(repo_id, db)
    summary = job.results_summary if job else {}

    repo_info = {
        "name": repo.name,
        "clone_path": repo.clone_path,
        "languages": repo.languages or [],
        "frameworks": repo.frameworks or [],
        "package_managers": repo.package_managers or [],
        "total_files": repo.total_files,
        "total_lines": repo.total_lines,
        "health_score": repo.health_score,
        "default_branch": repo.default_branch,
        "github_url": repo.github_url,
    }

    from app.ai.local_engine import local_reasoning_engine

    try:
        return await local_reasoning_engine.answer(
            query=payload.message,
            history=payload.history or [],
            repo_id=str(repo_id),
            results_summary=summary,
            repo_info=repo_info,
        )
    except Exception as exc:
        log.exception("local_chat_failed", repo_id=str(repo_id), error=str(exc))
        return ChatResponse(
            answer=f"Could not process inquiry: {exc}",
            citations=[],
            model_used="RIE Local Intelligence Engine (Offline / Deterministic)",
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
