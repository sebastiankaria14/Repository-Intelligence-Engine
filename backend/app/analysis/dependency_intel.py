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


def _build_service_graph(imports: list[dict], files: list[dict]) -> dict:
    """Build an internal module dependency graph from imports."""
    nodes_set: set[str] = set()
    edges_list: list[dict] = []

    for imp in imports:
        if not imp.get("is_relative", False):
            continue
        source_file = imp.get("file_path", "")
        target_module = imp.get("module", "")

        src_module = _file_to_module(source_file)
        if src_module and target_module and src_module != target_module:
            nodes_set.add(src_module)
            nodes_set.add(target_module)
            edges_list.append({
                "id": f"{src_module}->{target_module}",
                "source": src_module,
                "target": target_module,
            })

    nodes = [{"id": n, "data": {"label": n}} for n in nodes_set]
    return {"nodes": nodes, "edges": edges_list}


def _detect_circular_deps(imports: list[dict], files: list[dict]) -> list[list[str]]:
    """Detect circular import dependencies."""
    graph: dict[str, set[str]] = defaultdict(set)

    for imp in imports:
        if not imp.get("is_relative", False):
            continue
        src = _file_to_module(imp.get("file_path", ""))
        tgt = imp.get("module", "")
        if src and tgt:
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

    for node in graph:
        dfs(node, [], set())

    return cycles[:20]


def _file_to_module(file_path: str) -> str:
    """Convert a file path to a module name."""
    if not file_path:
        return ""
    parts = file_path.replace("\\", "/").split("/")
    if parts:
        # Use the first directory as module
        return parts[0]
    return file_path
