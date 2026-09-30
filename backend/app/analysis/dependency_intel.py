"""
Repository Intelligence Engine — Dependency Intelligence
Extracts package dependencies from manifest files and detects internal
service dependencies and circular dependencies.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)


def analyze_dependencies(
    repo_path: str,
    files: list[dict],
    imports: list[dict],
) -> dict:
    """Analyze external and internal dependencies."""
    packages: list[dict] = []

    # Extract from package.json
    packages.extend(_parse_package_json(repo_path))

    # Extract from requirements.txt
    packages.extend(_parse_requirements_txt(repo_path))

    # Extract from pyproject.toml
    packages.extend(_parse_pyproject_toml(repo_path))

    # Extract from pom.xml (basic)
    packages.extend(_parse_pom_xml(repo_path))

    # Build internal service graph from imports
    service_graph = _build_service_graph(imports, files)

    # Detect circular dependencies
    circular = _detect_circular_deps(imports, files)

    return {
        "packages": packages,
        "service_graph": service_graph,
        "circular_dependencies": circular,
        "total": len(packages),
    }


def _parse_package_json(repo_path: str) -> list[dict]:
    """Parse npm/yarn/pnpm package.json."""
    pkg_file = Path(repo_path) / "package.json"
    if not pkg_file.exists():
        return []

    try:
        with open(pkg_file) as f:
            pkg = json.load(f)
    except Exception:
        return []

    packages = []
    for name, version in pkg.get("dependencies", {}).items():
        packages.append({
            "name": name,
            "version": version.lstrip("^~>="),
            "type": "runtime",
            "source": "package.json",
        })
    for name, version in pkg.get("devDependencies", {}).items():
        packages.append({
            "name": name,
            "version": version.lstrip("^~>="),
            "type": "dev",
            "source": "package.json",
        })
    for name, version in pkg.get("peerDependencies", {}).items():
        packages.append({
            "name": name,
            "version": version.lstrip("^~>="),
            "type": "peer",
            "source": "package.json",
        })

    return packages


def _parse_requirements_txt(repo_path: str) -> list[dict]:
    """Parse pip requirements.txt."""
    req_file = Path(repo_path) / "requirements.txt"
    if not req_file.exists():
        return []

    packages = []
    try:
        content = req_file.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Parse name==version, name>=version, name~=version, bare name
            for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
                if sep in line:
                    name, version = line.split(sep, 1)
                    packages.append({
                        "name": name.strip(),
                        "version": version.strip().split(",")[0],
                        "type": "runtime",
                        "source": "requirements.txt",
                    })
                    break
            else:
                packages.append({
                    "name": line.split("[")[0].strip(),
                    "version": None,
                    "type": "runtime",
                    "source": "requirements.txt",
                })
    except Exception:
        pass

    return packages


def _parse_pyproject_toml(repo_path: str) -> list[dict]:
    """Parse pyproject.toml for dependencies."""
    pyproject = Path(repo_path) / "pyproject.toml"
    if not pyproject.exists():
        return []

    packages = []
    try:
        content = pyproject.read_text(encoding="utf-8", errors="replace")
        in_deps = False
        in_dev = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("[project.dependencies]") or stripped.startswith("dependencies = ["):
                in_deps = True
                in_dev = False
                continue
            if "dev" in stripped.lower() and stripped.startswith("["):
                in_dev = True
                in_deps = False
                continue
            if stripped.startswith("[") and not stripped.startswith("[["):
                in_deps = False
                in_dev = False
                continue

            if in_deps or in_dev:
                # Parse "package>=version" or "package"
                cleaned = stripped.strip('",[] ')
                if cleaned and not cleaned.startswith("#"):
                    for sep in (">=", "==", "~=", "<=", ">", "<"):
                        if sep in cleaned:
                            name, version = cleaned.split(sep, 1)
                            packages.append({
                                "name": name.strip(),
                                "version": version.strip().rstrip('",'),
                                "type": "dev" if in_dev else "runtime",
                                "source": "pyproject.toml",
                            })
                            break
                    else:
                        name = cleaned.split("[")[0].strip()
                        if name and not name.startswith("{"):
                            packages.append({
                                "name": name,
                                "version": None,
                                "type": "dev" if in_dev else "runtime",
                                "source": "pyproject.toml",
                            })
    except Exception:
        pass

    return packages


def _parse_pom_xml(repo_path: str) -> list[dict]:
    """Basic pom.xml dependency extraction (regex-based, no XML parser)."""
    pom_file = Path(repo_path) / "pom.xml"
    if not pom_file.exists():
        return []

    packages = []
    try:
        import re
        content = pom_file.read_text(encoding="utf-8", errors="replace")
        # Simple regex: find <dependency> blocks
        deps = re.findall(
            r"<dependency>\s*"
            r"<groupId>([^<]+)</groupId>\s*"
            r"<artifactId>([^<]+)</artifactId>\s*"
            r"(?:<version>([^<]+)</version>)?",
            content,
        )
        for group_id, artifact_id, version in deps:
            packages.append({
                "name": f"{group_id}:{artifact_id}",
                "version": version or None,
                "type": "runtime",
                "source": "pom.xml",
            })
    except Exception:
        pass

    return packages


def _clean_target_module(target_module: str) -> str:
    """Clean and normalize import module names."""
    if not target_module:
        return ""
    mod = target_module.replace("\\", "/").lstrip("./")
    parts = mod.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    if "." in mod and "/" not in mod:
        dot_parts = [p for p in mod.split(".") if p]
        if len(dot_parts) >= 2 and dot_parts[0] in ("app", "src", "backend", "frontend"):
            return f"{dot_parts[0]}/{dot_parts[1]}"
        if dot_parts:
            return dot_parts[0]
    return parts[0] if parts else mod


def _file_to_module(file_path: str) -> str:
    """Convert a file path to a logical module/subsystem name."""
    if not file_path:
        return ""
    clean = file_path.replace("\\", "/").strip("/")
    parts = clean.split("/")
    if len(parts) >= 3 and parts[0] in ("backend", "frontend", "src", "packages"):
        return f"{parts[0]}/{parts[1]}"
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}" if parts[0] in ("app", "lib", "components") else parts[0]
    return parts[0] if parts else clean


def _build_service_graph(imports: list[dict], files: list[dict]) -> dict:
    """Build an internal module dependency graph from imports with blast-radius metadata."""
    nodes_set: set[str] = set()
    edges_map: dict[tuple[str, str], int] = defaultdict(int)
    incoming_counts: dict[str, int] = defaultdict(int)
    outgoing_counts: dict[str, int] = defaultdict(int)

    for imp in imports:
        source_file = imp.get("file_path", "")
        target_raw = imp.get("module", "")
        is_rel = imp.get("is_relative", False) or target_raw.startswith((".", "app.", "src."))

        if not is_rel:
            continue

        src_module = _file_to_module(source_file)
        tgt_module = _clean_target_module(target_raw)

        if src_module and tgt_module and src_module != tgt_module:
            nodes_set.add(src_module)
            nodes_set.add(tgt_module)
            edges_map[(src_module, tgt_module)] += 1
            outgoing_counts[src_module] += 1
            incoming_counts[tgt_module] += 1

    # Detect cycles to tag circular nodes/edges
    circular_cycles = _detect_circular_deps(imports, files)
    circular_nodes: set[str] = set()
    circular_edges: set[tuple[str, str]] = set()
    for cycle in circular_cycles:
        for node in cycle:
            circular_nodes.add(node)
        for i in range(len(cycle) - 1):
            circular_edges.add((cycle[i], cycle[i + 1]))
        if len(cycle) >= 2:
            circular_edges.add((cycle[-1], cycle[0]))

    sorted_nodes = sorted(nodes_set)
    cols = 3
    nodes = []
    for i, n in enumerate(sorted_nodes):
        nodes.append({
            "id": n,
            "type": "dependencyNode",
            "position": {"x": (i % cols) * 360 + 50, "y": (i // cols) * 280 + 50},
            "data": {
                "label": n,
                "name": n,
                "incoming_count": incoming_counts[n],
                "outgoing_count": outgoing_counts[n],
                "is_circular": n in circular_nodes,
                "blast_radius": incoming_counts[n],
            },
        })

    edges_list = []
    for (src, tgt), count in edges_map.items():
        is_cycle = (src, tgt) in circular_edges
        edges_list.append({
            "id": f"{src}->{tgt}",
            "source": src,
            "target": tgt,
            "label": f"{count} calls" if count > 1 else "",
            "animated": is_cycle,
            "style": {
                "stroke": "#f43f5e" if is_cycle else "#06b6d4",
                "strokeWidth": 2.5 if is_cycle else 1.5,
            },
            "data": {
                "is_circular": is_cycle,
                "call_count": count,
            },
        })

    return {"nodes": nodes, "edges": edges_list}


def _detect_circular_deps(imports: list[dict], files: list[dict]) -> list[list[str]]:
    """Detect circular import dependencies."""
    graph: dict[str, set[str]] = defaultdict(set)

    for imp in imports:
        target_raw = imp.get("module", "")
        is_rel = imp.get("is_relative", False) or target_raw.startswith((".", "app.", "src."))
        if not is_rel:
            continue
        src = _file_to_module(imp.get("file_path", ""))
        tgt = _clean_target_module(target_raw)
        if src and tgt and src != tgt:
            graph[src].add(tgt)

    cycles: list[list[str]] = []
    visited: set[str] = set()

    def dfs(node: str, path: list[str], on_stack: set[str]):
        if node in on_stack:
            idx = path.index(node)
            cycle = path[idx:] + [node]
            if len(cycle) <= 10:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visited.add(node)
        on_stack.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor, path, on_stack)
        path.pop()
        on_stack.discard(node)

    for node in list(graph.keys()):
        dfs(node, [], set())

    # Deduplicate cycles
    unique_cycles = []
    seen = set()
    for c in cycles:
        key = tuple(sorted(set(c)))
        if key not in seen and len(c) > 1:
            seen.add(key)
            unique_cycles.append(c)

    return unique_cycles[:20]
