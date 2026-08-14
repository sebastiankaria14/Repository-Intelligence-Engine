"""
Repository Intelligence Engine — Analysis Pipeline
Orchestrates the full scan pipeline as a Celery chain.
Each task performs real work: clone, parse, graph, analyze, embed, index.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import redis
from celery import chain

from app.core.config import settings
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

log = get_logger(__name__)


def _compute_health_score(analysis_results: dict) -> float:
    """Compute a 0-100 health score from analysis results."""
    score = 100.0

    security = analysis_results.get("security") or {}
    if isinstance(security, dict):
        risk = security.get("risk_score", 0.0)
        score -= min(risk, 50.0)

    tech_debt = analysis_results.get("tech_debt") or {}
    if isinstance(tech_debt, dict):
        debt_score = tech_debt.get("debt_score", 0.0)
        score -= min(debt_score, 30.0)

    performance = analysis_results.get("performance") or {}
    if isinstance(performance, dict):
        perf_findings = performance.get("findings", [])
        score -= min(len(perf_findings) * 2, 20.0)

    return max(0.0, min(100.0, round(score, 1)))


def _publish_progress(repo_id: str, scan_job_id: str, status: str, phase: str, progress: float, message: str = ""):
    """Publish scan progress to Redis pub/sub for WebSocket broadcast."""
    try:
        r = redis.Redis.from_url(settings.redis_url)
        payload = {
            "repo_id": repo_id,
            "scan_job_id": scan_job_id,
            "status": status,
            "phase": phase,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.publish(f"scan:{repo_id}", json.dumps(payload))
        r.close()
    except Exception as e:
        log.warning("progress_publish_failed", error=str(e))


def _update_scan_job_sync(scan_job_id: str, **kwargs):
    """Update a scan job record (sync, for use inside Celery tasks)."""
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import Session

    from app.models.database import ScanJob

    sync_url = settings.effective_database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)
    with Session(engine) as session:
        session.execute(
            update(ScanJob).where(ScanJob.id == scan_job_id).values(**kwargs)
        )
        session.commit()
    engine.dispose()


def _update_repository_sync(repo_id: str, **kwargs):
    """Update a repository record (sync, for use inside Celery tasks)."""
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import Session

    from app.models.database import Repository

    sync_url = settings.effective_database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)
    with Session(engine) as session:
        session.execute(
            update(Repository).where(Repository.id == repo_id).values(**kwargs)
        )
        session.commit()
    engine.dispose()


def _get_github_url_sync(repo_id: str) -> str:
    """Get the GitHub URL for a repository (sync)."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.models.database import Repository

    sync_url = settings.effective_database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)
    with Session(engine) as session:
        result = session.execute(
            select(Repository.github_url).where(Repository.id == repo_id)
        )
        row = result.scalar_one()
    engine.dispose()
    return row


@celery_app.task(bind=True, name="tasks.run_analysis_pipeline")
def run_analysis_pipeline(self, repo_id: str, scan_job_id: str):
    """
    Main pipeline orchestrator.
    Chains: clone → parse → build_graph → analyze → embed → index
    """
    log.info("pipeline_starting", repo_id=repo_id, scan_job_id=scan_job_id)

    _update_scan_job_sync(
        scan_job_id,
        status="cloning",
        current_phase="cloning",
        progress=0.0,
        started_at=datetime.now(timezone.utc),
        celery_task_id=self.request.id,
    )

    _publish_progress(repo_id, scan_job_id, "cloning", "clone", 0.0, "Starting pipeline...")

    pipeline = chain(
        clone_repository.s(repo_id, scan_job_id),
        parse_repository.s(repo_id, scan_job_id),
        build_knowledge_graph.s(repo_id, scan_job_id),
        run_analysis_modules.s(repo_id, scan_job_id),
        embed_repository.s(repo_id, scan_job_id),
        index_repository.s(repo_id, scan_job_id),
        finalize_pipeline.s(repo_id, scan_job_id),
    )

    pipeline.apply_async()
    return {"repo_id": repo_id, "scan_job_id": scan_job_id, "status": "pipeline_dispatched"}


@celery_app.task(bind=True, name="tasks.clone_repository")
def clone_repository(self, repo_id: str, scan_job_id: str):
    """Clone the repository and detect metadata."""
    _publish_progress(repo_id, scan_job_id, "cloning", "clone", 5.0, "Cloning repository...")
    _update_scan_job_sync(scan_job_id, status="cloning", current_phase="clone", progress=5.0)

    from app.tasks.clone import analyze_clone

    github_url = _get_github_url_sync(repo_id)
    result = analyze_clone(github_url, repo_id)

    # Update repository record with detected metadata
    _update_repository_sync(
        repo_id,
        name=result["name"],
        default_branch=result["default_branch"],
        languages=result["languages"],
        frameworks=result["frameworks"],
        package_managers=result["package_managers"],
        is_monorepo=result["is_monorepo"],
        total_files=result["total_files"],
        total_lines=result["total_lines"],
    )

    _publish_progress(repo_id, scan_job_id, "cloning", "clone", 15.0,
                      f"Cloned: {result['total_files']} files, {result['total_lines']} lines")

    log.info("clone_complete", repo_id=repo_id, total_files=result["total_files"])

    return {
        "stage": "clone",
        "repo_id": repo_id,
        "repo_path": result["repo_path"],
        "files": result["files"],
        "languages": result["languages"],
    }


@celery_app.task(bind=True, name="tasks.parse_repository")
def parse_repository(self, previous_result, repo_id: str, scan_job_id: str):
    """Parse all source files using tree-sitter parsers."""
    _publish_progress(repo_id, scan_job_id, "parsing", "parse", 20.0, "Parsing source code...")
    _update_scan_job_sync(scan_job_id, status="parsing", current_phase="parse", progress=20.0)

    from app.parsing.registry import parser_registry

    repo_path = previous_result.get("repo_path", "")
    files = previous_result.get("files", [])

    all_symbols = []
    all_imports = []
    all_calls = []
    parse_results = []
    errors = []
    parsed_count = 0

    for i, file_info in enumerate(files):
        rel_path = file_info["path"]

        # Check if we have a parser for this file
        if not parser_registry.get_parser(rel_path):
            continue

        abs_path = Path(repo_path) / rel_path

        # Skip large files
        if file_info.get("size_bytes", 0) > 1_000_000:
            continue

        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        result = parser_registry.parse_file(rel_path, source)
        if result:
            parse_results.append({
                "file_path": result.file_path,
                "language": result.language,
                "symbols_count": len(result.symbols),
                "imports_count": len(result.imports),
                "calls_count": len(result.calls),
                "lines_of_code": result.lines_of_code,
            })
            all_symbols.extend([{
                "name": s.name,
                "type": s.type,
                "file_path": s.file_path,
                "line_start": s.line_start,
                "line_end": s.line_end,
                "signature": s.signature,
                "docstring": s.docstring,
                "parent": s.parent,
                "decorators": s.decorators,
                "parameters": s.parameters,
                "return_type": s.return_type,
                "visibility": s.visibility,
            } for s in result.symbols])

            all_imports.extend([{
                "module": imp.module,
                "name": imp.name,
                "alias": imp.alias,
                "is_relative": imp.is_relative,
                "line_number": imp.line_number,
                "file_path": result.file_path,
            } for imp in result.imports])

            all_calls.extend([{
                "caller": c.caller,
                "callee": c.callee,
                "line_number": c.line_number,
                "file_path": c.file_path,
            } for c in result.calls])

            if result.errors:
                errors.extend(result.errors)

            parsed_count += 1

        # Update progress every 50 files
        if i % 50 == 0 and len(files) > 0:
            pct = 20.0 + (i / len(files)) * 15.0
            _publish_progress(repo_id, scan_job_id, "parsing", "parse", pct,
                              f"Parsed {parsed_count} files...")

    _publish_progress(repo_id, scan_job_id, "parsing", "parse", 35.0,
                      f"Parsing complete: {parsed_count} files, {len(all_symbols)} symbols")

    log.info("parse_complete", repo_id=repo_id, parsed_files=parsed_count,
             symbols=len(all_symbols), imports=len(all_imports), calls=len(all_calls))

    return {
        "stage": "parse",
        "repo_id": repo_id,
        "repo_path": repo_path,
        "files": files,
        "symbols": all_symbols,
        "imports": all_imports,
        "calls": all_calls,
        "parse_results": parse_results,
        "languages": previous_result.get("languages", []),
    }


@celery_app.task(bind=True, name="tasks.build_knowledge_graph")
def build_knowledge_graph(self, previous_result, repo_id: str, scan_job_id: str):
    """Build Neo4j knowledge graph from parsed AST data."""
    _publish_progress(repo_id, scan_job_id, "building_graph", "graph", 40.0, "Building knowledge graph...")
    _update_scan_job_sync(scan_job_id, status="building_graph", current_phase="graph", progress=40.0)

    from app.tasks.graph_builder import build_graph

    symbols = previous_result.get("symbols", [])
    imports = previous_result.get("imports", [])
    calls = previous_result.get("calls", [])
    files = previous_result.get("files", [])

    try:
        stats = build_graph(repo_id, files, symbols, imports, calls)
        _publish_progress(repo_id, scan_job_id, "building_graph", "graph", 55.0,
                          f"Graph built: {stats.get('total_nodes', 0)} nodes, {stats.get('total_edges', 0)} edges")
    except Exception as e:
        log.error("graph_build_failed", repo_id=repo_id, error=str(e))
        _publish_progress(repo_id, scan_job_id, "building_graph", "graph", 55.0,
                          f"Graph build failed: {str(e)[:100]}")
        stats = {"total_nodes": 0, "total_edges": 0, "error": str(e)}

    return {
        "stage": "graph",
        "repo_id": repo_id,
        "repo_path": previous_result.get("repo_path", ""),
        "files": files,
        "symbols": symbols,
        "imports": imports,
        "calls": calls,
        "languages": previous_result.get("languages", []),
        "graph_stats": stats,
    }


@celery_app.task(bind=True, name="tasks.run_analysis_modules")
def run_analysis_modules(self, previous_result, repo_id: str, scan_job_id: str):
    """Run all analysis modules (architecture, API, DB, deps, git, security, perf, debt)."""
    _publish_progress(repo_id, scan_job_id, "analyzing", "analysis", 60.0, "Running analysis modules...")
    _update_scan_job_sync(scan_job_id, status="analyzing", current_phase="analysis", progress=60.0)

    from app.analysis.runner import run_all_analyses

    try:
        analysis_results = run_all_analyses(
            repo_id=repo_id,
            repo_path=previous_result.get("repo_path", ""),
            files=previous_result.get("files", []),
            symbols=previous_result.get("symbols", []),
            imports=previous_result.get("imports", []),
            calls=previous_result.get("calls", []),
            languages=previous_result.get("languages", []),
        )
        _publish_progress(repo_id, scan_job_id, "analyzing", "analysis", 75.0, "Analysis complete")
    except Exception as e:
        log.error("analysis_failed", repo_id=repo_id, error=str(e))
        analysis_results = {"error": str(e)}
        _publish_progress(repo_id, scan_job_id, "analyzing", "analysis", 75.0,
                          f"Analysis partially failed: {str(e)[:100]}")

    # Store results in the scan job
    _update_scan_job_sync(scan_job_id, results_summary=analysis_results)

    return {
        "stage": "analysis",
        "repo_id": repo_id,
        "repo_path": previous_result.get("repo_path", ""),
        "files": previous_result.get("files", []),
        "symbols": previous_result.get("symbols", []),
        "analysis_results": analysis_results,
    }


@celery_app.task(bind=True, name="tasks.embed_repository")
def embed_repository(self, previous_result, repo_id: str, scan_job_id: str):
    """Generate embeddings for Qdrant vector search."""
    _publish_progress(repo_id, scan_job_id, "embedding", "embed", 80.0, "Generating embeddings...")
    _update_scan_job_sync(scan_job_id, status="embedding", current_phase="embed", progress=80.0)

    from app.tasks.embedder import embed_codebase

    symbols = previous_result.get("symbols", [])
    files = previous_result.get("files", [])
    repo_path = previous_result.get("repo_path", "")

    try:
        embed_stats = embed_codebase(repo_id, repo_path, files, symbols)
        _publish_progress(repo_id, scan_job_id, "embedding", "embed", 90.0,
                          f"Embeddings: {embed_stats.get('total_embedded', 0)} chunks")
    except Exception as e:
        log.error("embedding_failed", repo_id=repo_id, error=str(e))
        embed_stats = {"error": str(e)}
        _publish_progress(repo_id, scan_job_id, "embedding", "embed", 90.0,
                          f"Embedding partially failed: {str(e)[:100]}")

    return {
        "stage": "embed",
        "repo_id": repo_id,
        "repo_path": repo_path,
        "files": files,
        "symbols": symbols,
        "embed_stats": embed_stats,
    }


@celery_app.task(bind=True, name="tasks.index_repository")
def index_repository(self, previous_result, repo_id: str, scan_job_id: str):
    """Index files and symbols in Meilisearch for full-text search."""
    _publish_progress(repo_id, scan_job_id, "indexing", "index", 92.0, "Indexing for search...")
    _update_scan_job_sync(scan_job_id, status="indexing", current_phase="index", progress=92.0)

    from app.tasks.indexer import index_codebase

    files = previous_result.get("files", [])
    symbols = previous_result.get("symbols", [])

    try:
        index_stats = index_codebase(repo_id, files, symbols)
        _publish_progress(repo_id, scan_job_id, "indexing", "index", 97.0,
                          f"Indexed: {index_stats.get('total_files', 0)} files, {index_stats.get('total_symbols', 0)} symbols")
    except Exception as e:
        log.error("indexing_failed", repo_id=repo_id, error=str(e))
        _publish_progress(repo_id, scan_job_id, "indexing", "index", 97.0,
                          f"Indexing partially failed: {str(e)[:100]}")

    return {"stage": "index", "repo_id": repo_id}


@celery_app.task(bind=True, name="tasks.finalize_pipeline")
def finalize_pipeline(self, previous_result, repo_id: str, scan_job_id: str):
    """Mark pipeline as complete and compute health score."""
    _publish_progress(repo_id, scan_job_id, "completed", "done", 100.0, "Analysis complete!")
    _update_scan_job_sync(
        scan_job_id,
        status="completed",
        current_phase="done",
        progress=100.0,
        completed_at=datetime.now(timezone.utc),
    )

    analysis_results = previous_result.get("analysis_results", {})
    health_score = _compute_health_score(analysis_results)
    _update_repository_sync(repo_id, health_score=health_score)

    log.info(
        "pipeline_complete",
        repo_id=repo_id,
        scan_job_id=scan_job_id,
        health_score=health_score,
    )
    return {"stage": "complete", "repo_id": repo_id}
