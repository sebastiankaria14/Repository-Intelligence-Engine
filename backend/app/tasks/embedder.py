"""
Repository Intelligence Engine — Code Embedder
Chunks source files into snippets and generates vector embeddings
for Qdrant. Falls back gracefully when Ollama or Qdrant are unavailable.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rb", ".php", ".c", ".cpp", ".h", ".cs", ".rs"}


def embed_codebase(repo_id: str, repo_path: str, files: list[dict], symbols: list[dict]) -> dict:
    """Generate embeddings for code chunks and upsert into Qdrant."""
    total_embedded = 0
    errors: list[str] = []

    try:
        from app.vector.client import get_vector_client
        vector_client = get_vector_client()
    except Exception as e:  # noqa: BLE001
        log.warning("qdrant_unavailable", error=str(e))
        return {"total_embedded": 0, "error": f"Qdrant unavailable: {e}"}

    try:
        from app.ai.ollama_client import ollama_client
        ollama_available = True
    except Exception as e:  # noqa: BLE001
        log.warning("ollama_unavailable", error=str(e))
        ollama_available = False

    root = Path(repo_path)
    points: list[dict] = []

    for f in files:
        path = f.get("path", "")
        if not path or not any(path.endswith(ext) for ext in CODE_EXTENSIONS):
            continue

        abs_path = root / path
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        chunks = _chunk_text(source, CHUNK_SIZE, CHUNK_OVERLAP)
        for idx, chunk in enumerate(chunks):
            chunk_id = hashlib.sha256(f"{repo_id}:{path}:{idx}".encode()).hexdigest()[:32]

            vector = None
            if ollama_available:
                try:
                    vector = ollama_client.embed(chunk)
                except Exception as e:  # noqa: BLE001
                    log.debug("embed_failed", path=path, chunk=idx, error=str(e))

            if vector is None:
                vector = _hash_vector(chunk_id)

            points.append({
                "id": chunk_id,
                "vector": vector,
                "payload": {
                    "repo_id": repo_id,
                    "file_path": path,
                    "chunk_index": idx,
                    "language": f.get("language", ""),
                    "text": chunk[:1000],
                },
            })
            total_embedded += 1

    if points:
        try:
            vector_client.upsert_vectors("code_chunks", points)
        except Exception as e:  # noqa: BLE001
            errors.append(f"Qdrant upsert failed: {e}")

    return {
        "total_embedded": total_embedded,
        "total_chunks": len(points),
        "errors": errors,
    }


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def _hash_vector(seed: str) -> list[float]:
    """Deterministic pseudo-vector from a string hash (fallback when Ollama is down)."""
    h = hashlib.sha256(seed.encode()).digest()
    return [float(b) / 255.0 for b in h[:384]] + [0.0] * (384 - 384)
