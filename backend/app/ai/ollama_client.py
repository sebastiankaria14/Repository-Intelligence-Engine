"""
Repository Intelligence Engine — Ollama AI Client
Client for Ollama-served LLM models (DeepSeek Coder, Qwen, Llama 3).
Will be fully implemented in Phase 6 (AI & Search Layer).
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Model routing
CODE_MODEL = "deepseek-coder:6.7b"
GENERAL_MODEL = "qwen2:7b"
FALLBACK_MODEL = "llama3:8b"


class OllamaClient:
    """Client for the Ollama local model runtime."""

    def __init__(self):
        self.base_url = settings.ollama_base_url

    async def list_models(self) -> list[str]:
        """List available models."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a completion from a prompt."""
        model = model or GENERAL_MODEL
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Chat completion with message history."""
        model = model or GENERAL_MODEL
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")

    async def embed(self, text: str, model: str = "all-minilm") -> list[float]:
        """Generate embeddings for text."""
        payload = {
            "model": model,
            "prompt": text,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/api/embeddings", json=payload)
            resp.raise_for_status()
            return resp.json().get("embedding", [])

    def select_model(self, query_type: str) -> str:
        """Select the best model based on query type."""
        if query_type in ("code", "security", "performance", "architecture"):
            return CODE_MODEL
        return GENERAL_MODEL


ollama_client = OllamaClient()
