"""
RIE Backend — RAG Orchestrator Tests
Tests the orchestrator with fully mocked external clients so no Neo4j/Qdrant/
Meilisearch/Ollama services are required.
"""

from types import SimpleNamespace

import pytest

from app.ai.prompts import determine_reasoning_type, trim_snippet
from app.ai.rag import CODE_COLLECTION, SYMBOLS_INDEX, RAGOrchestrator

# ── Fake clients ───────────────────────────────────────


class FakeOllama:
    def __init__(self, chat_response="Answer here", embed_vector=None, chat_raises=None):
        self._chat_response = chat_response
        self._embed_vector = embed_vector or [0.1] * 8
        self._chat_raises = chat_raises
        self.chat_calls = []
        self.embed_calls = []
        self.selected = []

    async def list_models(self):
        return []

    async def generate(self, prompt, model=None, system=None, temperature=0.3):
        return "generated"

    async def chat(self, messages, model=None, temperature=0.3):
        self.chat_calls.append({"messages": messages, "model": model, "temperature": temperature})
        if self._chat_raises:
            raise self._chat_raises
        return self._chat_response

    async def embed(self, text, model="all-minilm"):
        self.embed_calls.append(text)
        return self._embed_vector

    def select_model(self, query_type):
        self.selected.append(query_type)
        if query_type in ("code", "security", "performance", "architecture"):
            return "deepseek-coder:6.7b"
        return "qwen2:7b"


class FakeGraph:
    def __init__(self, nodes=None):
        self.nodes = nodes or []

    async def get_subgraph(self, repo_id, node_types=None, limit=200):
        return SimpleNamespace(nodes=self.nodes, relationships=[])

    async def connect(self):
        pass

    async def close(self):
        pass


class FakeVector:
    def __init__(self, hits=None):
        self.hits = hits or []

    def search(self, collection, query_vector, limit=10, filter_conditions=None):
        self.last_collection = collection
        self.last_filter = filter_conditions
        return self.hits

    def connect(self):
        pass

    def ensure_collections(self):
        pass

    def close(self):
        pass


class FakeSearch:
    def __init__(self, hits=None):
        self.hits = hits or []

    def search(self, index_name, query, limit=20, filter_str=None):
        self.last_index = index_name
        return self.hits

    def connect(self):
        pass

    def ensure_indexes(self):
        pass

    def close(self):
        pass


# ── Prompt helpers ───────────────────────────────────


@pytest.mark.parametrize(
    "query,expected",
    [
        ("how do i greet users", "code"),
        ("what's the architecture pattern", "architecture"),
        ("are there security vulnerabilities", "security"),
        ("why is this slow and the latency high", "performance"),
        ("tell me about the project", "general"),
    ],
)
def test_determine_reasoning_type(query, expected):
    assert determine_reasoning_type(query) == expected


def test_trim_snippet_short():
    assert trim_snippet("short text") == "short text"


def test_trim_snippet_long():
    long = "x" * 500
    result = trim_snippet(long, 100)
    assert len(result) == 100
    assert result.endswith("…")


# ── RAG orchestration ───────────────────────────────────


@pytest.mark.asyncio
async def test_answer_with_full_context():
    graph = FakeGraph(
        nodes=[
            SimpleNamespace(
                id="n1",
                labels=["File"],
                properties={"name": "main.py", "path": "src/main.py"},
            )
        ]
    )
    vector = FakeVector(
        hits=[
            {
                "id": "v1",
                "score": 0.95,
                "payload": {
                    "file_path": "src/main.py",
                    "content": "def greet(): print('hello')",
                },
            }
        ]
    )
    search = FakeSearch(hits=[{"file_path": "src/main.py", "content": "hello world"}])
    ollama = FakeOllama(chat_response="The codebase exposes a greet function.")

    orch = RAGOrchestrator(
        ollama=ollama, graph_repo=graph, vector_client=vector, search_client=search
    )
    result = await orch.answer("What does this codebase do", [], "repo-1")

    assert result.answer == "The codebase exposes a greet function."
    # 'codebase' contains 'code' → code reasoning → deepseek model
    assert result.model_used == "deepseek-coder:6.7b"
    assert result.reasoning_type == "code"
    assert ollama.chat_calls[0]["model"] == "deepseek-coder:6.7b"
    assert len(result.citations) > 0
    assert any(c.type == "graph_node" for c in result.citations)
    assert any(c.type == "file" for c in result.citations)
    # Vector search used the code collection with a filter
    assert vector.last_collection == CODE_COLLECTION
    assert vector.last_filter == {"repo_id": "repo-1"}
    # Search ran against both indices
    assert search.last_index == SYMBOLS_INDEX


@pytest.mark.asyncio
async def test_answer_with_no_context_uses_no_context_prompt():
    graph = FakeGraph(nodes=[])
    vector = FakeVector(hits=[])
    search = FakeSearch(hits=[])
    ollama = FakeOllama(chat_response="I'm not sure about that.")

    orch = RAGOrchestrator(
        ollama=ollama, graph_repo=graph, vector_client=vector, search_client=search
    )
    result = await orch.answer("Who wrote this code", [], "repo-1")

    assert result.answer == "I'm not sure about that."
    assert result.citations == []
    # Embeddings were still attempted even without graph hits
    assert ollama.embed_calls == ["Who wrote this code"]


@pytest.mark.asyncio
async def test_answer_graceful_when_ollama_unavailable():
    graph = FakeGraph(nodes=[])
    vector = FakeVector(hits=[])
    search = FakeSearch(hits=[])
    ollama = FakeOllama(chat_raises=RuntimeError("connection refused"))

    orch = RAGOrchestrator(
        ollama=ollama, graph_repo=graph, vector_client=vector, search_client=search
    )
    result = await orch.answer("Tell me something", [], "repo-1")

    assert "couldn't generate" in result.answer
    assert result.citations == []


@pytest.mark.asyncio
async def test_answer_passes_history_to_model():
    graph = FakeGraph(nodes=[])
    vector = FakeVector(hits=[])
    search = FakeSearch(hits=[])
    ollama = FakeOllama(chat_response="ok")

    orch = RAGOrchestrator(
        ollama=ollama, graph_repo=graph, vector_client=vector, search_client=search
    )
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    await orch.answer("follow up", history, "repo-1")

    sent_messages = ollama.chat_calls[0]["messages"]
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[1]["role"] == "user"
    assert sent_messages[1]["content"] == "hello"
    assert sent_messages[2]["role"] == "assistant"
    assert sent_messages[2]["content"] == "hi there"
    assert sent_messages[-1]["role"] == "user"
    assert "follow up" in sent_messages[-1]["content"]
