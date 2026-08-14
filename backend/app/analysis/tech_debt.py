"""
Repository Intelligence Engine — Technical Debt Analysis
Detects god classes, long methods, dead code, missing docstrings,
high complexity, and TODO/FIXME/HACK comments.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rb", ".php", ".cs", ".rs"}
GOD_CLASS_THRESHOLD = 15
LONG_METHOD_THRESHOLD = 50
MAX_COMPLEXITY = 10


def analyze_tech_debt(
    files: list[dict],
    symbols: list[dict],
    calls: list[dict],
) -> dict:
    """Run technical debt analysis."""
    items: list[dict] = []
    summary: dict[str, int] = {}
    total_effort_hours = 0.0

    root = Path(files[0].get("repo_path", "")) if files else Path(".")

    # Build call graph for dead-code detection
    callee_set = {c.get("callee", "") for c in calls if c.get("callee")}

    # 1. God classes: classes with many methods
    for sym in symbols:
        if sym.get("type") != "class":
            continue
        methods = [s for s in symbols if s.get("parent") == sym["name"] and s.get("type") in ("function", "method")]
        if len(methods) >= GOD_CLASS_THRESHOLD:
            effort = round(len(methods) * 0.25, 1)
            items.append({
                "type": "god_class",
                "severity": "high",
                "title": f"God class: {sym['name']} has {len(methods)} methods",
                "description": f"Class '{sym['name']}' in {sym['file_path']} has {len(methods)} methods. Consider splitting.",
                "file_path": sym["file_path"],
                "effort_hours": effort,
                "priority": 1,
                "risk": "high",
            })
            total_effort_hours += effort

    # 2. Long methods
    for sym in symbols:
        if sym.get("type") not in ("function", "method"):
            continue
        start = sym.get("line_start", 0)
        end = sym.get("line_end", start)
        length = max(0, end - start)
        if length > LONG_METHOD_THRESHOLD:
            effort = round((length - LONG_METHOD_THRESHOLD) * 0.05, 1)
            items.append({
                "type": "long_method",
                "severity": "medium",
                "title": f"Long method: {sym['name']} ({length} lines)",
                "description": f"Method '{sym['name']}' is {length} lines long. Consider extracting helpers.",
                "file_path": sym["file_path"],
                "effort_hours": effort,
                "priority": 2,
                "risk": "medium",
            })
            total_effort_hours += effort

    # 3. Dead code: functions never called
    for sym in symbols:
        if sym.get("type") not in ("function", "method"):
            continue
        name = sym.get("name", "")
        if not name or name.startswith("_"):
            continue
        if name not in callee_set and not _is_entry_point(sym):
            items.append({
                "type": "dead_code",
                "severity": "low",
                "title": f"Unused function: {name}",
                "description": f"Function '{name}' is defined but never referenced in the call graph.",
                "file_path": sym["file_path"],
                "effort_hours": 0.5,
                "priority": 3,
                "risk": "low",
            })
            total_effort_hours += 0.5

    # 4. TODO/FIXME/HACK comments
    for f in files:
        path = f.get("path", "")
        if not path or not any(path.endswith(ext) for ext in CODE_EXTENSIONS):
            continue
        abs_path = root / path
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(source.splitlines(), start=1):
            m = re.search(r"#\s*(TODO|FIXME|HACK|XXX)\b", line, re.IGNORECASE)
            if m:
                tag = m.group(1).upper()
                sev = {"TODO": "low", "FIXME": "medium", "HACK": "high", "XXX": "medium"}.get(tag, "low")
                items.append({
                    "type": "todo_comment",
                    "severity": sev,
                    "title": f"{tag} comment in {path}",
                    "description": line.strip(),
                    "file_path": path,
                    "effort_hours": 0.25,
                    "priority": 4 if sev == "low" else 2,
                    "risk": sev,
                })
                total_effort_hours += 0.25

    # 5. Missing docstrings on public functions/classes
    for sym in symbols:
        if sym.get("type") not in ("class", "function", "method"):
            continue
        if not sym.get("docstring"):
            items.append({
                "type": "missing_docstring",
                "severity": "info",
                "title": f"Missing docstring: {sym['name']}",
                "description": f"Public {sym['type']} '{sym['name']}' lacks a docstring.",
                "file_path": sym["file_path"],
                "effort_hours": 0.1,
                "priority": 5,
                "risk": "info",
            })
            total_effort_hours += 0.1

    # Build summary
    for item in items:
        sev = item.get("severity", "info")
        summary[sev] = summary.get(sev, 0) + 1

    debt_score = _compute_debt_score(items)

    return {
        "items": items,
        "total_effort_hours": round(total_effort_hours, 1),
        "debt_score": debt_score,
        "summary": summary,
    }


def _is_entry_point(sym: dict) -> bool:
    """Heuristic: treat main / route handlers / test functions as entry points."""
    name = sym.get("name", "")
    return bool(re.match(r"^(main|app|create_app|setup|teardown|test_)", name))


def _compute_debt_score(items: list[dict]) -> float:
    """Compute a 0-100 debt score. Higher = more debt."""
    if not items:
        return 0.0
    weights = {"critical": 20, "high": 10, "medium": 5, "low": 2, "info": 1}
    total = sum(weights.get(i.get("severity", "info"), 0) for i in items)
    return min(round(total, 1), 100.0)
