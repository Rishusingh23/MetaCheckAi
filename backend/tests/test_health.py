import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_api_health_endpoint_healthy(async_client: AsyncClient):
    """
    Test GET /api/health when database check succeeds.
    """
    with patch("app.api.v1.endpoints.health.check_db_health", return_value=True):
        response = await async_client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert data["services"]["database"] == "connected"
        assert data["project_name"] == "MetaCheck AI"


@pytest.mark.asyncio
async def test_api_health_endpoint_degraded(async_client: AsyncClient):
    """
    Test GET /api/health when database is unavailable.
    API should return status 'degraded' with database_connected: false, without crashing.
    """
    with patch("app.api.v1.endpoints.health.check_db_health", return_value=False):
        response = await async_client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["database_connected"] is False
        assert data["services"]["database"] == "disconnected"


@pytest.mark.asyncio
async def test_openapi_docs_accessible(async_client: AsyncClient):
    """
    Test that OpenAPI schema contains all Phase 2 endpoints.
    """
    response = await async_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]
    assert "/api/v1/products" in paths
    assert "/api/v1/inspections" in paths
    assert "/api/v1/rules" in paths
    assert "/api/v1/violations" in paths
    assert "/api/v1/reports" in paths
    assert "/api/v1/users" in paths
    assert "/api/v1/roles" in paths
