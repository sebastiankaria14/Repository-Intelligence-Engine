"""
Repository Intelligence Engine — Qdrant Vector Client
Client wrapper for Qdrant vector database operations.
Will be fully implemented in Phase 6 (AI & Search Layer).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Collection names
CODE_COLLECTION = "code_chunks"
DOCS_COLLECTION = "documentation"
COMMITS_COLLECTION = "commit_messages"

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension


class VectorClient:
    """Wrapper around the Qdrant client for RIE vector operations."""

    def __init__(self):
        self._client: Optional[QdrantClient] = None

    def connect(self) -> None:
        self._client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        log.info("qdrant_connected", host=settings.qdrant_host)

    def ensure_collections(self) -> None:
        """Create collections if they don't exist."""
        for name in [CODE_COLLECTION, DOCS_COLLECTION, COMMITS_COLLECTION]:
            collections = [c.name for c in self._client.get_collections().collections]
            if name not in collections:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
                )
                log.info("qdrant_collection_created", name=name)

    def close(self) -> None:
        if self._client:
            self._client.close()

    async def upsert_vectors(
        self,
        collection: str,
        points: List[Dict[str, Any]],
    ) -> None:
        """Upsert vectors into a collection. Each point: {id, vector, payload}."""
        structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {}))
            for p in points
        ]
        self._client.upsert(collection_name=collection, points=structs)

    async def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        filter_conditions: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        results = self._client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=filter_conditions,
        )
        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload,
            }
            for r in results
        ]


_vector_client: Optional[VectorClient] = None


def get_vector_client() -> VectorClient:
    global _vector_client
    if _vector_client is None:
        _vector_client = VectorClient()
        _vector_client.connect()
        _vector_client.ensure_collections()
    return _vector_client
