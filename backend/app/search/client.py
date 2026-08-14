"""
Repository Intelligence Engine — Meilisearch Client
Client wrapper for Meilisearch full-text search.
Will be fully implemented in Phase 6 (AI & Search Layer).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import meilisearch

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Index names
FILES_INDEX = "files"
SYMBOLS_INDEX = "symbols"
DOCS_INDEX = "docs"


class SearchClient:
    """Wrapper around the Meilisearch client for RIE search operations."""

    def __init__(self):
        self._client: Optional[meilisearch.Client] = None

    def connect(self) -> None:
        self._client = meilisearch.Client(
            settings.meilisearch_url,
            settings.meilisearch_master_key,
        )
        log.info("meilisearch_connected", url=settings.meilisearch_url)

    def ensure_indexes(self) -> None:
        """Create indexes if they don't exist."""
        existing = {idx.uid for idx in self._client.get_indexes()["results"]}
        for name in [FILES_INDEX, SYMBOLS_INDEX, DOCS_INDEX]:
            if name not in existing:
                self._client.create_index(name, {"primaryKey": "id"})
                log.info("meilisearch_index_created", name=name)

        # Configure searchable attributes
        self._client.index(FILES_INDEX).update_searchable_attributes(
            ["path", "name", "content", "language"]
        )
        self._client.index(SYMBOLS_INDEX).update_searchable_attributes(
            ["name", "type", "file_path", "signature"]
        )
        self._client.index(DOCS_INDEX).update_searchable_attributes(
            ["title", "content", "file_path"]
        )

    def close(self) -> None:
        pass  # Meilisearch client doesn't need explicit close

    async def index_documents(self, index_name: str, documents: List[Dict[str, Any]]) -> None:
        """Add or update documents in an index."""
        self._client.index(index_name).add_documents(documents)

    async def search(
        self,
        index_name: str,
        query: str,
        limit: int = 20,
        filter_str: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search an index."""
        params = {"limit": limit}
        if filter_str:
            params["filter"] = filter_str
        result = self._client.index(index_name).search(query, params)
        return result.get("hits", [])


_search_client: Optional[SearchClient] = None


def get_search_client() -> SearchClient:
    global _search_client
    if _search_client is None:
        _search_client = SearchClient()
        _search_client.connect()
        _search_client.ensure_indexes()
    return _search_client
