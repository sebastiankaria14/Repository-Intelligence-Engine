"""
Unit tests for LocalReasoningEngine.
Verifies deterministic zero-API-key code intelligence and citation generation.
"""

import pytest

from app.ai.local_engine import LocalReasoningEngine


@pytest.mark.asyncio
async def test_local_engine_security_query():
    engine = LocalReasoningEngine()
    summary = {
        "security": {
            "risk_score": 45.0,
            "findings": [
                {
                    "title": "Hardcoded API key",
                    "severity": "high",
                    "file_path": "backend/app/core/config.py",
                    "line_start": 28,
                    "recommendation": "Use environment variables.",
                }
            ],
        }
    }

    resp = await engine.answer("Are there any security vulnerabilities?", [], "repo-1", summary)
    assert resp.reasoning_type == "security"
    assert "45.0/100" in resp.answer
    assert "Hardcoded API key" in resp.answer
    assert len(resp.citations) == 1
    assert "backend/app/core/config.py:28" == resp.citations[0].reference
    assert "RIE Local Intelligence Engine" in resp.model_used


@pytest.mark.asyncio
async def test_local_engine_architecture_query():
    engine = LocalReasoningEngine()
    summary = {
        "architecture": {
            "pattern": "Layered Architecture",
            "confidence": 0.85,
            "layers": [
                {"name": "Api", "file_count": 5, "components": ["api", "routes"]},
                {"name": "Data", "file_count": 3, "components": ["models", "db"]},
            ],
        },
        "graph": {
            "hubs": [{"name": "backend/app/main.py", "type": "File", "score": 0.35}],
        },
    }

    resp = await engine.answer("What architecture pattern does this project use?", [], "repo-1", summary)
    assert resp.reasoning_type == "architecture"
    assert "Layered Architecture" in resp.answer
    assert "85%" in resp.answer
    assert len(resp.citations) > 0


@pytest.mark.asyncio
async def test_local_engine_dependencies_and_cycles():
    engine = LocalReasoningEngine()
    summary = {
        "dependencies": {
            "packages": [{"name": "fastapi", "version": "0.115.0", "source": "requirements.txt"}],
            "circular_dependencies": [["module_a.py", "module_b.py", "module_a.py"]],
        }
    }

    resp = await engine.answer("Check for circular dependencies", [], "repo-1", summary)
    assert resp.reasoning_type == "architecture"
    assert "module_a.py" in resp.answer
    assert len(resp.citations) > 0


@pytest.mark.asyncio
async def test_local_engine_api_query():
    engine = LocalReasoningEngine()
    summary = {
        "apis": {
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/api/repositories",
                    "handler_name": "list_repositories",
                    "file_path": "backend/app/api/repositories.py",
                    "line_start": 40,
                }
            ],
            "frameworks_detected": ["FastAPI"],
        }
    }

    resp = await engine.answer("List all API routes and endpoints", [], "repo-1", summary)
    assert resp.reasoning_type == "code"
    assert "/api/repositories" in resp.answer
    assert "FastAPI" in resp.answer
    assert len(resp.citations) == 1
