"""
Repository Intelligence Engine — Local Pipeline Runner
Asynchronous, in-process analysis pipeline replacing Celery and Redis.
Supports direct local filesystem scanning (zero cloning needed) and Git repository URLs.
100% offline, storing results in embedded SQLite and in-memory NetworkX knowledge graph.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import select, update

from app.analysis.runner import run_all_analyses
from app.api.websocket import manager
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.graph import get_graph_repository
from app.graph.interface import GraphRelationship
from app.models.database import Finding, FindingType, Repository, ScanJob, ScanStatus, Severity
from app.parsing.registry import parser_registry
from app.tasks.clone import (
    clone_repo,
    detect_default_branch,
    detect_frameworks,
    detect_languages,
    detect_monorepo,
    detect_package_managers,
    enumerate_files,
    extract_repo_name,
)

log = get_logger(__name__)

FORBIDDEN_ROOTS = [
    Path("C:\\").resolve(),
    Path("/").resolve(),
    Path("/etc").resolve(),
    Path("/root").resolve(),
    (Path.home() / ".ssh").resolve(),
    (Path.home() / ".aws").resolve(),
]
_sys_root = os.environ.get("SystemRoot")
if _sys_root:
    FORBIDDEN_ROOTS.append(Path(_sys_root).resolve())


def validate_safe_local_directory(target_path: Path) -> Path:
    """Validate that local directory is safe to scan and does not target protected OS or credential roots."""
    resolved = target_path.resolve()
    for forbidden in FORBIDDEN_ROOTS:
        if resolved == forbidden:
            raise ValueError(f"Access to protected system directory '{resolved}' is prohibited")
    return resolved


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


def _node_id(prefix: str, *parts: str) -> str:
    raw = ":".join([prefix] + list(parts))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _symbol_label(sym_type: str) -> str:
    mapping = {
        "class": "Class",
        "function": "Function",
        "method": "Method",
        "interface": "Interface",
        "variable": "Variable",
        "type_alias": "TypeAlias",
    }
    return mapping.get(sym_type, "Function")


async def build_in_memory_graph(
    repo_id: str,
    files: List[dict],
    symbols: List[dict],
    imports: List[dict],
    calls: List[dict],
) -> Dict[str, Any]:
    """Populate the in-memory NetworkX knowledge graph with AST relationships."""
    graph_repo = await get_graph_repository()
    await graph_repo.clear_repository(repo_id)

    total_nodes = 0
    total_edges = 0

    # 1. Repository Root Node
    await graph_repo.create_node(
        labels=["Repository"],
        properties={"id": repo_id, "name": repo_id, "repo_id": repo_id},
    )
    total_nodes += 1

    # 2. File Nodes
    file_nodes_to_create = []
    file_edges_to_create = []
    for f in files:
        if not f.get("language"):
            continue
        fid = _node_id("file", repo_id, f["path"])
        file_nodes_to_create.append((
            ["File"],
            {
                "id": fid,
                "repo_id": repo_id,
                "path": f["path"],
                "name": f["path"],
                "language": f["language"],
                "lines": f.get("lines", 0),
                "size_bytes": f.get("size_bytes", 0),
            },
        ))
        file_edges_to_create.append(
            GraphRelationship(
                source_id=repo_id,
                target_id=fid,
                type="CONTAINS",
            )
        )

    if file_nodes_to_create:
        await graph_repo.batch_create_nodes(file_nodes_to_create)
        await graph_repo.batch_create_relationships(file_edges_to_create)
        total_nodes += len(file_nodes_to_create)
        total_edges += len(file_edges_to_create)

    # 3. Symbol Nodes
    symbol_nodes_to_create = []
    symbol_define_edges = []
    symbol_cache = {}

    for s in symbols:
        sid = _node_id("sym", repo_id, s["file_path"], s["name"], str(s.get("line_start", 0)))
        label = _symbol_label(s["type"])
        props = {
            "id": sid,
            "repo_id": repo_id,
            "name": s["name"],
            "type": s["type"],
            "file_path": s["file_path"],
            "line_start": s.get("line_start", 0),
            "line_end": s.get("line_end", 0),
            "signature": s.get("signature") or "",
            "visibility": s.get("visibility", "public"),
            "parent": s.get("parent") or "",
        }
        symbol_nodes_to_create.append(([label], props))
        symbol_cache[(s["file_path"], s["name"])] = sid

        # File -[:DEFINES]-> Symbol
        fid = _node_id("file", repo_id, s["file_path"])
        symbol_define_edges.append(
            GraphRelationship(
                source_id=fid,
                target_id=sid,
                type="DEFINES",
            )
        )

    if symbol_nodes_to_create:
        await graph_repo.batch_create_nodes(symbol_nodes_to_create)
        await graph_repo.batch_create_relationships(symbol_define_edges)
        total_nodes += len(symbol_nodes_to_create)
        total_edges += len(symbol_define_edges)

    # 4. Import Nodes & Edges
    import_nodes_to_create = []
    import_edges_to_create = []
    seen_modules = set()

    for imp in imports:
        mod_name = imp["module"]
        mod_id = _node_id("module", repo_id, mod_name)
        if mod_id not in seen_modules:
            seen_modules.add(mod_id)
            import_nodes_to_create.append((
                ["Module"],
                {"id": mod_id, "repo_id": repo_id, "name": mod_name},
            ))

        file_id = _node_id("file", repo_id, imp.get("file_path", ""))
        import_edges_to_create.append(
            GraphRelationship(
                source_id=file_id,
                target_id=mod_id,
                type="IMPORTS",
                properties={"name": imp.get("name") or mod_name},
            )
        )

    if import_nodes_to_create:
        await graph_repo.batch_create_nodes(import_nodes_to_create)
        total_nodes += len(import_nodes_to_create)
    if import_edges_to_create:
        await graph_repo.batch_create_relationships(import_edges_to_create)
        total_edges += len(import_edges_to_create)

    # 5. Call Edges (capped for performance)
    call_edges_to_create = []
    for c in calls[:1000]:
        caller_id = symbol_cache.get((c.get("file_path", ""), c["caller"]))
        # Match callee in same file first, or anywhere
        callee_id = None
        for (fp, name), sid in symbol_cache.items():
            if name == c["callee"]:
                callee_id = sid
                if fp == c.get("file_path"):
                    break
        if caller_id and callee_id and caller_id != callee_id:
            call_edges_to_create.append(
                GraphRelationship(
                    source_id=caller_id,
                    target_id=callee_id,
                    type="CALLS",
                    properties={"line": c.get("line_number", 0)},
                )
            )

    if call_edges_to_create:
        await graph_repo.batch_create_relationships(call_edges_to_create)
        total_edges += len(call_edges_to_create)

    # Centrality & Hubs
    hubs = graph_repo.get_architectural_hubs(repo_id, top_n=10)
    cycles = graph_repo.detect_cycles(repo_id)

    # Save to disk for persistence across server restarts
    graph_repo.save_to_disk(repo_id)

    log.info(
        "in_memory_graph_built",
        repo_id=repo_id,
        total_nodes=total_nodes,
        total_edges=total_edges,
        hubs_count=len(hubs),
        cycles_count=len(cycles),
    )

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "hubs": hubs,
        "cycles": cycles,
    }


async def _publish_progress(
    repo_id: str,
    scan_job_id: str,
    status: str,
    phase: str,
    progress: float,
    message: str = "",
):
    """Publish real-time scan progress to WebSocket clients."""
    payload = {
        "repo_id": repo_id,
        "scan_job_id": scan_job_id,
        "status": status,
        "phase": phase,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await manager.broadcast(repo_id, payload)
    except Exception as e:
        log.warning("ws_broadcast_failed", error=str(e))


async def run_pipeline_async(repo_id: str, scan_job_id: str, target: str):
    """
    Asynchronous in-process scan pipeline.
    Executes directly in the desktop backend without external workers.
    """
    log.info("local_pipeline_started", repo_id=repo_id, target=target)
    job_uuid = uuid.UUID(str(scan_job_id)) if isinstance(scan_job_id, (str, uuid.UUID)) else scan_job_id
    repo_uuid = uuid.UUID(str(repo_id)) if isinstance(repo_id, (str, uuid.UUID)) else repo_id

    async with async_session_factory() as session:
        # Update ScanJob started
        await session.execute(
            update(ScanJob)
            .where(ScanJob.id == job_uuid)
            .values(
                status=ScanStatus.CLONING,
                current_phase="clone",
                progress=5.0,
                started_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    await _publish_progress(repo_id, scan_job_id, "cloning", "clone", 5.0, "Preparing codebase access...")

    try:
        target_str = str(target).strip()
        if target_str.startswith("-"):
            raise ValueError("Invalid repository target: leading hyphens are prohibited")
        if "\x00" in target_str:
            raise ValueError("Invalid repository target: null bytes are prohibited")

        target_path = Path(target_str)
        is_local_dir = False
        try:
            is_local_dir = target_path.exists() and target_path.is_dir()
        except Exception:
            is_local_dir = False

        if is_local_dir:
            resolved = validate_safe_local_directory(target_path)
            repo_path = resolved
            name = resolved.name
            files = enumerate_files(repo_path)
            default_branch = detect_default_branch(repo_path)
            await _publish_progress(repo_id, scan_job_id, "cloning", "clone", 15.0, f"Opened local folder: {len(files)} files found")
        else:
            await _publish_progress(repo_id, scan_job_id, "cloning", "clone", 10.0, "Cloning remote repository...")
            repo_path = clone_repo(target_str, repo_id)
            name = extract_repo_name(target_str)
            files = enumerate_files(repo_path)
            default_branch = detect_default_branch(repo_path)
            await _publish_progress(repo_id, scan_job_id, "cloning", "clone", 15.0, f"Cloned repository: {len(files)} files")

        basenames = {Path(f["path"]).name for f in files}
        languages = detect_languages(files)
        frameworks = detect_frameworks(repo_path, files)
        package_managers = detect_package_managers(basenames)
        is_monorepo = detect_monorepo(repo_path, basenames)
        total_files = len(files)
        total_lines = sum(f["lines"] for f in files)

        # Update Repository metadata in SQLite
        async with async_session_factory() as session:
            await session.execute(
                update(Repository)
                .where(Repository.id == repo_uuid)
                .values(
                    name=name,
                    clone_path=str(repo_path),
                    default_branch=default_branch,
                    languages=languages,
                    frameworks=frameworks,
                    package_managers=package_managers,
                    is_monorepo=is_monorepo,
                    total_files=total_files,
                    total_lines=total_lines,
                )
            )
            await session.commit()

        # Stage 2: AST Parsing
        await _publish_progress(repo_id, scan_job_id, "parsing", "parse", 20.0, "Parsing source code with Tree-sitter...")
        async with async_session_factory() as session:
            await session.execute(
                update(ScanJob)
                .where(ScanJob.id == job_uuid)
                .values(status=ScanStatus.PARSING, current_phase="parse", progress=20.0)
            )
            await session.commit()

        all_symbols = []
        all_imports = []
        all_calls = []
        parsed_count = 0

        for i, file_info in enumerate(files):
            rel_path = file_info["path"]
            if not parser_registry.get_parser(rel_path):
                continue
            if file_info.get("size_bytes", 0) > 1_000_000:
                continue

            abs_path = repo_path / rel_path
            try:
                source = abs_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            res = parser_registry.parse_file(rel_path, source)
            if res:
                all_symbols.extend([{
                    "name": s.name,
                    "type": s.type,
                    "file_path": s.file_path,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "signature": s.signature,
                    "docstring": s.docstring,
                    "parent": s.parent,
                    "visibility": s.visibility,
                } for s in res.symbols])

                all_imports.extend([{
                    "module": imp.module,
                    "name": imp.name,
                    "alias": imp.alias,
                    "file_path": res.file_path,
                } for imp in res.imports])

                all_calls.extend([{
                    "caller": c.caller,
                    "callee": c.callee,
                    "line_number": c.line_number,
                    "file_path": c.file_path,
                } for c in res.calls])

                parsed_count += 1

            if i % 40 == 0 and len(files) > 0:
                pct = 20.0 + (i / len(files)) * 15.0
                await _publish_progress(repo_id, scan_job_id, "parsing", "parse", pct, f"Parsed {parsed_count} source files...")
                await asyncio.sleep(0)  # Yield to event loop

        await _publish_progress(repo_id, scan_job_id, "parsing", "parse", 35.0, f"Parsed {parsed_count} files ({len(all_symbols)} symbols)")

        # Stage 3: In-Memory Knowledge Graph Construction
        await _publish_progress(repo_id, scan_job_id, "building_graph", "graph", 40.0, "Constructing in-memory knowledge graph...")
        async with async_session_factory() as session:
            await session.execute(
                update(ScanJob)
                .where(ScanJob.id == job_uuid)
                .values(status=ScanStatus.BUILDING_GRAPH, current_phase="graph", progress=40.0)
            )
            await session.commit()

        graph_stats = await build_in_memory_graph(repo_id, files, all_symbols, all_imports, all_calls)
        await _publish_progress(repo_id, scan_job_id, "building_graph", "graph", 55.0, f"Graph built: {graph_stats['total_nodes']} nodes, {graph_stats['total_edges']} edges")

        # Stage 4: Run Analysis Modules
        await _publish_progress(repo_id, scan_job_id, "analyzing", "analysis", 60.0, "Executing algorithmic code analysis...")
        async with async_session_factory() as session:
            await session.execute(
                update(ScanJob)
                .where(ScanJob.id == job_uuid)
                .values(status=ScanStatus.ANALYZING, current_phase="analysis", progress=60.0)
            )
            await session.commit()

        analysis_results = run_all_analyses(
            repo_id=repo_id,
            repo_path=str(repo_path),
            files=files,
            symbols=all_symbols,
            imports=all_imports,
            calls=all_calls,
            languages=languages,
        )
        analysis_results["graph"] = graph_stats

        # Compute health score
        health_score = _compute_health_score(analysis_results)

        # Stage 5: Store Findings and Complete
        await _publish_progress(repo_id, scan_job_id, "analyzing", "analysis", 85.0, "Saving findings and health score to local database...")
        async with async_session_factory() as session:
            # Store Findings
            security_findings = (analysis_results.get("security") or {}).get("findings", [])
            for f in security_findings:
                severity_val = getattr(Severity, f.get("severity", "info").upper(), Severity.INFO)
                db_finding = Finding(
                    repository_id=repo_uuid,
                    scan_job_id=job_uuid,
                    finding_type=FindingType.SECURITY,
                    severity=severity_val,
                    title=f.get("title", "Security Finding"),
                    description=f.get("description", ""),
                    file_path=f.get("file_path", ""),
                    line_start=f.get("line_start"),
                    line_end=f.get("line_end"),
                    rule_id=f.get("rule_id", "sec-heuristic"),
                    recommendation=f.get("recommendation", ""),
                )
                session.add(db_finding)

            # Store Performance Findings
            perf_findings = (analysis_results.get("performance") or {}).get("findings", [])
            for f in perf_findings:
                db_finding = Finding(
                    repository_id=repo_uuid,
                    scan_job_id=job_uuid,
                    finding_type=FindingType.PERFORMANCE,
                    severity=Severity.MEDIUM,
                    title=f.get("title", "Performance Finding"),
                    description=f.get("description", ""),
                    file_path=f.get("file_path", ""),
                    line_start=f.get("line_number"),
                    rule_id=f.get("pattern", "perf-heuristic"),
                )
                session.add(db_finding)

            # Update ScanJob results
            await session.execute(
                update(ScanJob)
                .where(ScanJob.id == job_uuid)
                .values(
                    status=ScanStatus.COMPLETED,
                    current_phase="done",
                    progress=100.0,
                    completed_at=datetime.now(timezone.utc),
                    results_summary=analysis_results,
                )
            )

            # Update Repository health score
            await session.execute(
                update(Repository)
                .where(Repository.id == repo_uuid)
                .values(health_score=health_score)
            )
            await session.commit()

        await _publish_progress(repo_id, scan_job_id, "completed", "done", 100.0, "Analysis complete! Knowledge graph and insights ready.")
        log.info("local_pipeline_completed", repo_id=repo_id, health_score=health_score)

    except Exception as exc:
        log.error("local_pipeline_failed", repo_id=repo_id, error=str(exc), exc_info=True)
        async with async_session_factory() as session:
            await session.execute(
                update(ScanJob)
                .where(ScanJob.id == job_uuid)
                .values(
                    status=ScanStatus.FAILED,
                    current_phase="failed",
                    error_message=f"Analysis failed: {exc}",
                )
            )
            await session.commit()
        await _publish_progress(repo_id, scan_job_id, "failed", "failed", 0.0, f"Error: {exc}")
