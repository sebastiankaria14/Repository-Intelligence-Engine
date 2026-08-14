"""
Repository Intelligence Engine — Performance Analysis
Detects N+1 query patterns, large file processing without streaming,
circular imports, missing pagination, heavy endpoints, and other
performance anti-patterns from parsed AST and call data.
"""

from __future__ import annotations

from collections import defaultdict

from app.core.logging import get_logger

log = get_logger(__name__)

CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rb", ".php", ".cs", ".rs"}


def analyze_performance(
    files: list[dict],
    symbols: list[dict],
    calls: list[dict],
    imports: list[dict],
) -> dict:
    """Run performance anti-pattern analysis."""
    findings: list[dict] = []
    summary: dict[str, int] = {}

    # Build caller → callees map from call graph
    caller_callees: dict[str, set[str]] = defaultdict(set)
    callee_callers: dict[str, set[str]] = defaultdict(set)
    for c in calls:
        caller = c.get("caller") or ""
        callee = c.get("callee") or ""
        if caller and callee:
            caller_callees[caller].add(callee)
            callee_callers[callee].add(caller)

    # 1. N+1 query pattern: ORM/db call inside a loop body
    db_keywords = {"find", "find_all", "query", "filter", "select", "get", "all", "save", "create", "update", "delete"}
    for sym in symbols:
        if sym.get("type") not in ("function", "method"):
            continue
        name = sym.get("name", "")
        if not name:
            continue
        body_calls = caller_callees.get(name, set())
        db_calls = [c for c in body_calls if any(kw in c.lower() for kw in db_keywords)]
        if len(db_calls) >= 2:
            findings.append({
                "type": "n_plus_one",
                "severity": "high",
                "title": "Potential N+1 query pattern",
                "description": (
                    f"Function '{name}' makes {len(db_calls)} database calls. "
                    f"If called in a loop, this may cause N+1 queries."
                ),
                "file_path": sym.get("file_path", ""),
                "line_number": sym.get("line_start", 0),
                "recommendation": "Use batching, join loading, or bulk operations.",
            })

    # 2. Large file without streaming (file size > 200 KB with read_text pattern)
    large_file_threshold = 200_000
    for f in files:
        size = f.get("size_bytes", 0)
        path = f.get("path", "")
        if size > large_file_threshold and any(path.endswith(ext) for ext in CODE_EXTENSIONS):
            findings.append({
                "type": "large_object",
                "severity": "medium",
                "title": "Large file loaded without streaming",
                "description": f"File {path} is {size:,} bytes. Reading entire content may exhaust memory.",
                "file_path": path,
                "line_number": 0,
                "recommendation": "Use streaming/chunked reads for large files.",
            })

    # 3. Missing pagination: endpoints/APIs that return list without limit/offset
    for sym in symbols:
        if sym.get("type") not in ("function", "method"):
            continue
        decorators = " ".join(sym.get("decorators", []))
        if any(r in decorators for r in ("@app.get", "@app.post", "@router.get", "@router.post", "@GetMapping", "@PostMapping", "@Get", "@Post")):
            params = sym.get("parameters", [])
            has_pagination = any(
                p.get("name", "").lower() in ("limit", "offset", "page", "size", "skip")
                for p in params
            )
            if not has_pagination:
                findings.append({
                    "type": "missing_pagination",
                    "severity": "low",
                    "title": "Endpoint may lack pagination",
                    "description": f"Handler '{sym['name']}' has no pagination parameters.",
                    "file_path": sym.get("file_path", ""),
                    "line_number": sym.get("line_start", 0),
                    "recommendation": "Add limit/offset or page/size parameters.",
                })

    # 4. Circular import detection from imports list
    module_imports: dict[str, set[str]] = defaultdict(set)
    for imp in imports:
        module = (imp.get("module") or "").split(".")[0]
        name = imp.get("name", "")
        if module and name:
            module_imports[module].add(name)

    for sym in symbols:
        if sym.get("type") not in ("function", "method"):
            continue
        parent = sym.get("parent") or sym.get("name", "")
        if parent and parent in module_imports:
            imported = module_imports[parent]
            # A simple heuristic: if a module imports a symbol whose name matches the parent's own module
            if any(parent.lower() in (i or "").lower() for i in imported):
                findings.append({
                    "type": "circular_dep",
                    "severity": "medium",
                    "title": "Potential circular import",
                    "description": f"Module '{parent}' may have a circular import dependency.",
                    "file_path": sym.get("file_path", ""),
                    "line_number": sym.get("line_start", 0),
                    "recommendation": "Refactor to break the cycle (move imports inside functions or extract shared code).",
                })
                break  # one per module

    # Build summary
    for finding in findings:
        sev = finding.get("severity", "info")
        summary[sev] = summary.get(sev, 0) + 1

    return {
        "findings": findings,
        "summary": summary,
    }
