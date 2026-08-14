"""
Repository Intelligence Engine — Code Indexer
Indexes files and symbols into Meilisearch for full-text search.
Falls back gracefully when Meilisearch is unavailable.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rb", ".php", ".c", ".cpp", ".h", ".cs", ".rs"}


def index_codebase(repo_id: str, files: list[dict], symbols: list[dict]) -> dict:
    """Index files and symbols into Meilisearch."""
    total_files = 0
    total_symbols = 0
    errors: list[str] = []

    try:
        from app.search.client import get_search_client
        search_client = get_search_client()
    except Exception as e:  # noqa: BLE001
        log.warning("meilisearch_unavailable", error=str(e))
        return {"total_files": 0, "total_symbols": 0, "error": f"Meilisearch unavailable: {e}"}

    root = Path(files[0].get("repo_path", "")) if files else Path(".")

    file_documents: list[dict] = []
    for f in files:
        path = f.get("path", "")
        if not path or not any(path.endswith(ext) for ext in CODE_EXTENSIONS):
            continue
        abs_path = root / path
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        file_documents.append({
            "id": hashlib.sha256(f"{repo_id}:{path}".encode()).hexdigest()[:32],
            "repo_id": repo_id,
            "path": path,
            "name": Path(path).name,
            "language": f.get("language", ""),
            "content": content[:10000],
            "size_bytes": f.get("size_bytes", 0),
        })
        total_files += 1

    if file_documents:
        try:
            search_client.index_documents("files", file_documents)
        except Exception as e:  # noqa: BLE001
            errors.append(f"Meilisearch file index failed: {e}")

    symbol_documents: list[dict] = []
    for sym in symbols:
        symbol_documents.append({
            "id": hashlib.sha256(f"{repo_id}:{sym.get('file_path','')}:{sym.get('name','')}".encode()).hexdigest()[:32],
            "repo_id": repo_id,
            "name": sym.get("name", ""),
            "type": sym.get("type", ""),
            "file_path": sym.get("file_path", ""),
            "signature": sym.get("signature", ""),
            "line_start": sym.get("line_start", 0),
            "line_end": sym.get("line_end", 0),
        })
        total_symbols += 1

    if symbol_documents:
        try:
            search_client.index_documents("symbols", symbol_documents)
        except Exception as e:  # noqa: BLE001
            errors.append(f"Meilisearch symbol index failed: {e}")

    return {
        "total_files": total_files,
        "total_symbols": total_symbols,
        "errors": errors,
    }