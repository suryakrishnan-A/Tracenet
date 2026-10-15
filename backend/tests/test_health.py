"""Tests for Root and API v1 Health Endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient):
    """Test that GET /health returns 200 with expected payload."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "tracenest-backend"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient):
    """Test that GET /api/v1/health returns 200 with versioned status."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "TraceNest API"
    assert data["version"] == "0.1.0"
    assert data["api_version"] == "v1"
    assert data["environment"] == "development"
    assert "database_connected" in data
    assert isinstance(data["database_connected"], bool)
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_openapi_docs_reachable(async_client: AsyncClient):
    """Verify that OpenAPI documentation schema is properly mounted."""
    response = await async_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "TraceNest API"
    assert "/health" in data["paths"]
    assert "/api/v1/health" in data["paths"]
    assert "/api/v1/projects" in data["paths"]
    assert "/api/v1/telemetry" in data["paths"]
    assert "/api/v1/issues" in data["paths"]


@pytest.mark.asyncio
async def test_database_connectivity():
    """Verify that the database health check function connects and executes successfully."""
    from app.db.session import check_db_connection
    is_connected = await check_db_connection()
    assert is_connected is True
