"""
RIE Backend — Health Endpoint Tests
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint returns app info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Repository Intelligence Engine"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient):
    """Test the health endpoint responds (may show degraded if services unavailable)."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "version" in data
