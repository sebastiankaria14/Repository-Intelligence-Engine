"""
Repository Intelligence Engine — RAG Orchestrator
Combines Neo4j graph context, Qdrant vector similarity, and Meilisearch
full-text results into a grounded prompt for the Ollama LLM, then returns a
fully-cited answer.

All external clients are resolved lazily and failures are tolerated: if a
service is unavailable, that retrieval source is simply skipped rather than
failing the whole request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.ollama_client import OllamaClient, ollama_client
from app.ai.prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_NO_CONTEXT,
    USER_PROMPT_WITH_CONTEXT,
    determine_reasoning_type,
    trim_snippet,
)
from app.core.logging import get_logger
from app.models.schemas import Citation

log = get_logger(__name__)

# Collection / index names — mirrored in the vector & search clients but kept
# here so the orchestrator can be tested without importing those heavy deps.
CODE_COLLECTION = "code_chunks"
FILES_INDEX = "files"
SYMBOLS_INDEX = "symbols"

# Soft ceiling on the prompt length to avoid blowing past model context.
MAX_CONTEXT_CHUNKS = 12
MAX_SNIPPET_CHARS = 400


@dataclass
class ContextChunk:
    text: str
    citation: Citation


@dataclass
class RAGResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    model_used: str = "none"
    reasoning_type: str = "general"


class RAGOrchestrator:
    """Orchestrates retrieval across graph, vector, and search stores."""

    def __init__(
        self,
        ollama: OllamaClient | None = None,
        graph_repo: Any = None,
        vector_client: Any = None,
        search_client: Any = None,
    ):
        self._ollama = ollama or ollama_client
        self._graph_repo = graph_repo
        self._vector_client = vector_client
        self._search_client = search_client

    # ── Client resolution (lazy + fault-tolerant) ────────────

    async def _get_graph(self) -> Any:
        if self._graph_repo is not None:
            return self._graph_repo
        try:
            from app.graph import get_graph_repository

            self._graph_repo = await get_graph_repository()
        except Exception as exc:  # noqa: BLE001
            log.warning("graph_unavailable", error=str(exc))
            self._graph_repo = None
        return self._graph_repo

    def _get_vector(self) -> Any:
        if self._vector_client is not None:
            return self._vector_client
        try:
            from app.vector.client import get_vector_client

            self._vector_client = get_vector_client()
        except Exception as exc:  # noqa: BLE001
            log.warning("vector_unavailable", error=str(exc))
            self._vector_client = None
        return self._vector_client

    def _get_search(self) -> Any:
        if self._search_client is not None:
            return self._search_client
        try:
            from app.search.client import get_search_client

            self._search_client = get_search_client()
        except Exception as exc:  # noqa: BLE001
            log.warning("search_unavailable", error=str(exc))
            self._search_client = None
        return self._search_client

    # ── Retrieval ─────────────────────────────────────────────

    async def retrieve(self, repo_id: str, query: str) -> list[ContextChunk]:
        """Gather the most relevant context chunks across all stores."""
        chunks: list[ContextChunk] = []

        graph_chunks = await self._retrieve_graph(repo_id, query)
        chunks.extend(graph_chunks)

        vector_chunks = await self._retrieve_vector(repo_id, query)
        chunks.extend(vector_chunks)

        search_chunks = await self._retrieve_search(repo_id, query)
        chunks.extend(search_chunks)

        # De-duplicate by text and cap the total.
        seen: set[str] = set()
        unique: list[ContextChunk] = []
        for chunk in chunks:
            if chunk.text in seen:
                continue
            seen.add(chunk.text)
            unique.append(chunk)
        return unique[:MAX_CONTEXT_CHUNKS]

    async def _retrieve_graph(self, repo_id: str, query: str) -> list[ContextChunk]:
        graph = await self._get_graph()
        if graph is None:
            return []
        try:
            subgraph = await graph.get_subgraph(repo_id, limit=30)
        except Exception as exc:  # noqa: BLE001
            log.warning("graph_query_failed", error=str(exc))
            return []

        chunks: list[ContextChunk] = []
        for node in subgraph.nodes:
            props = node.properties or {}
            label = node.labels[0] if node.labels else "Node"
            name = props.get("name") or props.get("path") or node.id
            snippet = trim_snippet(f"{label}: {name}", MAX_SNIPPET_CHARS)
            chunks.append(
                ContextChunk(
                    text=f"Knowledge graph node — {label}: {name}",
                    citation=Citation(
                        type="graph_node",
                        reference=node.id,
                        snippet=snippet,
                        relevance_score=1.0,
                    ),
                )
            )
        return chunks

    async def _retrieve_vector(self, repo_id: str, query: str) -> list[ContextChunk]:
        vector_client = self._get_vector()
        if vector_client is None:
            return []
        try:
            query_vector = await self._ollama.embed(query)
        except Exception as exc:  # noqa: BLE001
            log.warning("embedding_failed", error=str(exc))
            return []

        try:
            results = vector_client.search(
                CODE_COLLECTION, query_vector, limit=5,
                filter_conditions={"repo_id": repo_id},
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("vector_search_failed", error=str(exc))
            return []

        chunks: list[ContextChunk] = []
        for hit in results:
            payload = hit.get("payload") or {}
            file_path = payload.get("file_path") or payload.get("path") or "unknown"
            content = payload.get("content", "") or ""
            chunks.append(
                ContextChunk(
                    text=trim_snippet(content, MAX_SNIPPET_CHARS),
                    citation=Citation(
                        type="file",
                        reference=file_path,
                        snippet=trim_snippet(content, MAX_SNIPPET_CHARS),
                        relevance_score=round(float(hit.get("score", 0.0)), 4),
                    ),
                )
            )
        return chunks

    async def _retrieve_search(self, repo_id: str, query: str) -> list[ContextChunk]:
        search = self._get_search()
        if search is None:
            return []
        try:
            file_hits = search.search(FILES_INDEX, query, limit=3)
            symbol_hits = search.search(SYMBOLS_INDEX, query, limit=3)
        except Exception as exc:  # noqa: BLE001
            log.warning("search_failed", error=str(exc))
            return []

        chunks: list[ContextChunk] = []
        for hit in list(file_hits) + list(symbol_hits):
            file_path = hit.get("file_path") or hit.get("path") or "unknown"
            content = hit.get("content", "") or ""
            chunks.append(
                ContextChunk(
                    text=trim_snippet(content, MAX_SNIPPET_CHARS),
                    citation=Citation(
                        type="file",
                        reference=file_path,
                        snippet=trim_snippet(content, MAX_SNIPPET_CHARS),
                        relevance_score=1.0,
                    ),
                )
            )
        return chunks

    # ── Generation ─────────────────────────────────────────

    async def answer(
        self,
        query: str,
        history: list[dict[str, str]],
        repo_id: str,
        model: str | None = None,
    ) -> RAGResult:
        reasoning_type = determine_reasoning_type(query)
        model_name = model or self._ollama.select_model(reasoning_type)

        chunks = await self.retrieve(repo_id, query)

        if not chunks:
            user_prompt = USER_PROMPT_NO_CONTEXT.format(query=query)
            citations: list[Citation] = []
        else:
            context_parts = [
                f"[{i + 1}] {chunk.text}" for i, chunk in enumerate(chunks)
            ]
            user_prompt = USER_PROMPT_WITH_CONTEXT.format(
                context="\n".join(context_parts), query=query
            )
            citations = [chunk.citation for chunk in chunks]

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        for msg in history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_prompt})

        try:
            answer = await self._ollama.chat(
                messages,
                model=model_name,
                temperature=0.3 if reasoning_type == "general" else 0.1,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("ollama_generation_failed", error=str(exc))
            answer = (
                "Sorry, I couldn't generate a response. The AI backend (Ollama) "
                "may not be running or the requested model is unavailable. "
                "Please ensure Ollama is running and the model has been pulled."
            )

        return RAGResult(
            answer=answer,
            citations=citations,
            model_used=model_name,
            reasoning_type=reasoning_type,
        )


rag_orchestrator = RAGOrchestrator()
