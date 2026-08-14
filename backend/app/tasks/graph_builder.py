"""
Repository Intelligence Engine — Knowledge Graph Builder
Populates Neo4j with nodes and relationships from parsed AST data.
Runs synchronously inside Celery tasks.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from neo4j import GraphDatabase

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _node_id(prefix: str, *parts: str) -> str:
    """Generate a deterministic node ID from parts."""
    raw = ":".join([prefix] + list(parts))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_graph(
    repo_id: str,
    files: list[dict],
    symbols: list[dict],
    imports: list[dict],
    calls: list[dict],
) -> dict:
    """
    Build the full knowledge graph in Neo4j.

    Creates nodes for: Repository, File, Class, Function, Method, Interface, Module
    Creates relationships for: CONTAINS, DEFINES, IMPORTS, CALLS, INHERITS
    """
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    total_nodes = 0
    total_edges = 0

    try:
        with driver.session() as session:
            # Create constraints (idempotent)
            _create_constraints(session)

            # Clear previous data for this repo
            session.run(
                "MATCH (n {repo_id: $repo_id}) DETACH DELETE n",
                repo_id=repo_id,
            )

            # 1. Create Repository node
            session.run(
                "MERGE (r:Repository {id: $id}) "
                "SET r.repo_id = $repo_id, r.name = $repo_id",
                id=repo_id, repo_id=repo_id,
            )
            total_nodes += 1

            # 2. Create File nodes
            file_nodes = []
            for f in files:
                if not f.get("language"):
                    continue
                fid = _node_id("file", repo_id, f["path"])
                file_nodes.append({
                    "id": fid,
                    "path": f["path"],
                    "language": f["language"],
                    "lines": f.get("lines", 0),
                    "size_bytes": f.get("size_bytes", 0),
                })

            if file_nodes:
                session.run(
                    "UNWIND $nodes AS n "
                    "MERGE (f:File {id: n.id}) "
                    "SET f.repo_id = $repo_id, f.path = n.path, "
                    "    f.language = n.language, f.lines = n.lines, "
                    "    f.size_bytes = n.size_bytes, f.name = n.path",
                    nodes=file_nodes, repo_id=repo_id,
                )
                total_nodes += len(file_nodes)

                # Repository -[:CONTAINS]-> File
                session.run(
                    "UNWIND $nodes AS n "
                    "MATCH (r:Repository {id: $repo_id}), (f:File {id: n.id}) "
                    "MERGE (r)-[:CONTAINS]->(f)",
                    nodes=file_nodes, repo_id=repo_id,
                )
                total_edges += len(file_nodes)

            # 3. Create Symbol nodes (Class, Function, Method, Interface, etc.)
            symbol_nodes = []
            for s in symbols:
                sid = _node_id("sym", repo_id, s["file_path"], s["name"], str(s.get("line_start", 0)))
                label = _symbol_label(s["type"])
                symbol_nodes.append({
                    "id": sid,
                    "name": s["name"],
                    "type": s["type"],
                    "label": label,
                    "file_path": s["file_path"],
                    "line_start": s.get("line_start", 0),
                    "line_end": s.get("line_end", 0),
                    "signature": s.get("signature") or "",
                    "docstring": (s.get("docstring") or "")[:500],
                    "parent": s.get("parent") or "",
                    "visibility": s.get("visibility", "public"),
                    "return_type": s.get("return_type") or "",
                })

            if symbol_nodes:
                # Create with dynamic labels using APOC-free approach
                for label in ("Class", "Function", "Method", "Interface", "Variable", "TypeAlias"):
                    batch = [n for n in symbol_nodes if n["label"] == label]
                    if batch:
                        session.run(
                            f"UNWIND $nodes AS n "
                            f"MERGE (s:{label} {{id: n.id}}) "
                            f"SET s.repo_id = $repo_id, s.name = n.name, "
                            f"    s.type = n.type, s.file_path = n.file_path, "
                            f"    s.line_start = n.line_start, s.line_end = n.line_end, "
                            f"    s.signature = n.signature, s.docstring = n.docstring, "
                            f"    s.parent = n.parent, s.visibility = n.visibility, "
                            f"    s.return_type = n.return_type",
                            nodes=batch, repo_id=repo_id,
                        )
                total_nodes += len(symbol_nodes)

            # 4. File -[:DEFINES]-> Symbol
            for s in symbol_nodes:
                fid = _node_id("file", repo_id, s["file_path"])
                session.run(
                    f"MATCH (f:File {{id: $fid}}), (s:{s['label']} {{id: $sid}}) "
                    f"MERGE (f)-[:DEFINES]->(s)",
                    fid=fid, sid=s["id"],
                )
                total_edges += 1

            # 5. Class -[:HAS_METHOD]-> Method (parent relationships)
            parent_edges = []
            for s in symbol_nodes:
                if s["parent"] and s["type"] == "method":
                    parent_id = _find_parent_id(symbol_nodes, s["parent"], s["file_path"], repo_id)
                    if parent_id:
                        parent_edges.append({"parent_id": parent_id, "child_id": s["id"], "label": s["label"]})

            for edge in parent_edges:
                session.run(
                    f"MATCH (p {{id: $pid}}), (c:{edge['label']} {{id: $cid}}) "
                    f"MERGE (p)-[:HAS_METHOD]->(c)",
                    pid=edge["parent_id"], cid=edge["child_id"],
                )
                total_edges += 1

            # 6. Import relationships: File -[:IMPORTS]-> Module
            import_edges = []
            for imp in imports:
                file_id = _node_id("file", repo_id, imp.get("file_path", ""))
                module_id = _node_id("module", repo_id, imp["module"])
                import_edges.append({
                    "file_id": file_id,
                    "module_id": module_id,
                    "module_name": imp["module"],
                    "imported_name": imp.get("name") or imp["module"],
                })

            # Create Module nodes
            unique_modules = {e["module_id"]: e["module_name"] for e in import_edges}
            if unique_modules:
                module_nodes = [{"id": mid, "name": mname} for mid, mname in unique_modules.items()]
                session.run(
                    "UNWIND $nodes AS n "
                    "MERGE (m:Module {id: n.id}) "
                    "SET m.repo_id = $repo_id, m.name = n.name",
                    nodes=module_nodes, repo_id=repo_id,
                )
                total_nodes += len(module_nodes)

            # Create IMPORTS edges
            if import_edges:
                session.run(
                    "UNWIND $edges AS e "
                    "MATCH (f:File {id: e.file_id}), (m:Module {id: e.module_id}) "
                    "MERGE (f)-[:IMPORTS {name: e.imported_name}]->(m)",
                    edges=import_edges,
                )
                total_edges += len(import_edges)

            # 7. Call relationships: Caller -[:CALLS]-> Callee
            call_count = 0
            for c in calls[:500]:  # Cap at 500 to avoid huge graphs
                caller_id = _find_symbol_id(symbol_nodes, c["caller"], c.get("file_path", ""), repo_id)
                callee_id = _find_symbol_id(symbol_nodes, c["callee"], "", repo_id)
                if caller_id and callee_id and caller_id != callee_id:
                    caller_label = _find_symbol_label(symbol_nodes, caller_id)
                    callee_label = _find_symbol_label(symbol_nodes, callee_id)
                    if caller_label and callee_label:
                        try:
                            session.run(
                                f"MATCH (a:{caller_label} {{id: $aid}}), (b:{callee_label} {{id: $bid}}) "
                                f"MERGE (a)-[:CALLS {{line: $line}}]->(b)",
                                aid=caller_id, bid=callee_id, line=c.get("line_number", 0),
                            )
                            call_count += 1
                        except Exception:
                            pass
            total_edges += call_count

    finally:
        driver.close()

    log.info("graph_built", repo_id=repo_id, total_nodes=total_nodes, total_edges=total_edges)
    return {"total_nodes": total_nodes, "total_edges": total_edges}


def _create_constraints(session):
    """Create uniqueness constraints and indexes."""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Repository) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:File) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Class) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Function) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Method) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Interface) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Module) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Variable) REQUIRE n.id IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (n:File) ON (n.repo_id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Class) ON (n.repo_id)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Function) ON (n.repo_id)",
    ]
    for c in constraints:
        try:
            session.run(c)
        except Exception:
            pass


def _symbol_label(sym_type: str) -> str:
    """Map symbol type to Neo4j label."""
    mapping = {
        "class": "Class",
        "function": "Function",
        "method": "Method",
        "interface": "Interface",
        "variable": "Variable",
        "type_alias": "TypeAlias",
    }
    return mapping.get(sym_type, "Function")


def _find_parent_id(symbol_nodes: list[dict], parent_name: str, file_path: str, repo_id: str) -> str | None:
    """Find the node ID of a parent class."""
    for s in symbol_nodes:
        if s["name"] == parent_name and s["file_path"] == file_path and s["type"] == "class":
            return s["id"]
    return None


def _find_symbol_id(symbol_nodes: list[dict], name: str, file_path: str, repo_id: str) -> str | None:
    """Find the node ID of a symbol by name (and optionally file)."""
    # First try exact match (same file)
    if file_path:
        for s in symbol_nodes:
            if s["name"] == name and s["file_path"] == file_path:
                return s["id"]
    # Fallback: any file
    for s in symbol_nodes:
        if s["name"] == name:
            return s["id"]
    return None


def _find_symbol_label(symbol_nodes: list[dict], node_id: str) -> str | None:
    """Find the Neo4j label for a symbol by its ID."""
    for s in symbol_nodes:
        if s["id"] == node_id:
            return s["label"]
    return None
