"""
Repository Intelligence Engine — Health Check Router
Comprehensive health check touching all backend services.
"""

from __future__ import annotations

import time
from typing import List

import redis.asyncio as aioredis
from fastapi import APIRouter
from neo4j import AsyncGraphDatabase

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import HealthResponse, ServiceHealth

router = APIRouter(tags=["health"])
log = get_logger(__name__)


async def _check_postgres() -> ServiceHealth:
    """Check PostgreSQL connectivity."""
    try:
        from sqlalchemy import text
        from app.core.database import engine

        start = time.monotonic()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(name="postgres", status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(name="postgres", status="unhealthy", details=str(e))


async def _check_redis() -> ServiceHealth:
    """Check Redis connectivity."""
    try:
        start = time.monotonic()
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(name="redis", status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(name="redis", status="unhealthy", details=str(e))


async def _check_neo4j() -> ServiceHealth:
    """Check Neo4j connectivity."""
    try:
        start = time.monotonic()
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        async with driver.session() as session:
            await session.run("RETURN 1")
        await driver.close()
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(name="neo4j", status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(name="neo4j", status="unhealthy", details=str(e))


async def _check_qdrant() -> ServiceHealth:
    """Check Qdrant connectivity."""
    try:
        import httpx

        start = time.monotonic()
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{settings.qdrant_host}:{settings.qdrant_port}/healthz")
            resp.raise_for_status()
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(name="qdrant", status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(name="qdrant", status="unhealthy", details=str(e))


async def _check_meilisearch() -> ServiceHealth:
    """Check Meilisearch connectivity."""
    try:
        import httpx

        start = time.monotonic()
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.meilisearch_url}/health")
            resp.raise_for_status()
        latency = (time.monotonic() - start) * 1000
        return ServiceHealth(name="meilisearch", status="healthy", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(name="meilisearch", status="unhealthy", details=str(e))


async def _check_ollama() -> ServiceHealth:
    """Check Ollama connectivity."""
    try:
        import httpx

        start = time.monotonic()
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
        latency = (time.monotonic() - start) * 1000
        data = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return ServiceHealth(
            name="ollama",
            status="healthy",
            latency_ms=round(latency, 2),
            details=f"Models: {', '.join(models) if models else 'none loaded'}",
        )
    except Exception as e:
        return ServiceHealth(name="ollama", status="unavailable", details=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check for all backend services.
    Returns individual status for each service dependency.
    """
    services: List[ServiceHealth] = []

    # Run all checks (could be parallelized with asyncio.gather but
    # keeping sequential for clarity and to avoid connection storms)
    for check in [
        _check_postgres,
        _check_redis,
        _check_neo4j,
        _check_qdrant,
        _check_meilisearch,
        _check_ollama,
    ]:
        try:
            result = await check()
            services.append(result)
        except Exception as e:
            log.error("health_check_error", check=check.__name__, error=str(e))
            services.append(
                ServiceHealth(name=check.__name__.replace("_check_", ""), status="unhealthy", details=str(e))
            )

    # Overall status: healthy if all core services (postgres, redis, neo4j) are healthy
    core_services = {"postgres", "redis", "neo4j"}
    core_healthy = all(
        s.status == "healthy" for s in services if s.name in core_services
    )
    overall = "healthy" if core_healthy else "degraded"

    return HealthResponse(
        status=overall,
        version="0.1.0",
        services=services,
    )
