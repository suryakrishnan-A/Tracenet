"""Tests for Telemetry Ingestion API, Authentication, and Persistence."""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.telemetry_event import TelemetryEvent


@pytest.fixture
async def sample_project(async_client: AsyncClient) -> dict:
    """Fixture creating a test project and returning its ID and raw API key."""
    res = await async_client.post("/api/v1/projects", json={"name": "Auth Service"})
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_valid_telemetry_ingestion_with_x_api_key(
    async_client: AsyncClient,
    sample_project: dict,
    db_session: AsyncSession,
):
    """Test successful telemetry event ingestion using X-API-Key header."""
    headers = {"X-API-Key": sample_project["api_key"]}
    payload = {
        "event_type": "error",
        "severity": "critical",
        "message": "Connection refused to redis cluster",
        "stack_trace": "Traceback (most recent call last):\n  File 'cache.py', line 12: ConnectionError",
        "endpoint": "/api/v1/users/login",
        "http_status": 500,
        "duration_ms": 234.5,
        "metadata": {"cluster": "us-east-1", "attempt": 3},
    }

    response = await async_client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "received"
    assert "event_id" in data
    assert data["project_id"] == sample_project["id"]

    # Verify event persistence in the test database
    event_id = uuid.UUID(data["event_id"])
    result = await db_session.execute(
        select(TelemetryEvent).where(TelemetryEvent.id == event_id)
    )
    persisted_event = result.scalar_one_or_none()
    assert persisted_event is not None
    assert persisted_event.project_id == uuid.UUID(sample_project["id"])
    assert persisted_event.event_type == "error"
    assert persisted_event.severity == "critical"
    assert persisted_event.message == "Connection refused to redis cluster"
    assert persisted_event.endpoint == "/api/v1/users/login"
    assert persisted_event.http_status == 500
    assert persisted_event.duration_ms == 234.5
    assert persisted_event.metadata_json == {"cluster": "us-east-1", "attempt": 3}
    assert persisted_event.received_at is not None


@pytest.mark.asyncio
async def test_valid_telemetry_ingestion_with_bearer_token(
    async_client: AsyncClient,
    sample_project: dict,
):
    """Test telemetry ingestion using Authorization: Bearer <key>."""
    headers = {"Authorization": f"Bearer {sample_project['api_key']}"}
    payload = {
        "event_type": "metric",
        "severity": "info",
        "message": "API response latency recorded",
        "endpoint": "/api/v1/items",
        "http_status": 200,
        "duration_ms": 45.2,
    }

    response = await async_client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "received"
    assert data["project_id"] == sample_project["id"]


@pytest.mark.asyncio
async def test_telemetry_missing_api_key(async_client: AsyncClient):
    """Test that requests lacking an API key are rejected with 401 Unauthorized."""
    payload = {
        "event_type": "error",
        "message": "Unauthenticated error event",
    }
    response = await async_client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_telemetry_invalid_api_key(async_client: AsyncClient):
    """Test that requests with an invalid API key are rejected with 401 Unauthorized."""
    headers = {"X-API-Key": "tn_live_invalidkey1234567890abcdef"}
    payload = {
        "event_type": "error",
        "message": "Event with bogus key",
    }
    response = await async_client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 401
    assert "Invalid or inactive API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_telemetry_invalid_payloads(
    async_client: AsyncClient,
    sample_project: dict,
):
    """Test validation errors for malformed telemetry payloads."""
    headers = {"X-API-Key": sample_project["api_key"]}

    # 1. Missing message
    res1 = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error"},
        headers=headers,
    )
    assert res1.status_code == 422

    # 2. Invalid severity
    res2 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "extreme_fatal_disaster",
            "message": "Something happened",
        },
        headers=headers,
    )
    assert res2.status_code == 422

    # 3. Invalid HTTP status (< 100 or > 599)
    res3 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "message": "HTTP issue",
            "http_status": 999,
        },
        headers=headers,
    )
    assert res3.status_code == 422


@pytest.mark.asyncio
async def test_telemetry_payload_size_limit(
    async_client: AsyncClient,
    sample_project: dict,
):
    """Test that payloads exceeding the 1MB limit are rejected with 413 Payload Too Large."""
    headers = {
        "X-API-Key": sample_project["api_key"],
        "Content-Length": "2000000",  # Claim 2MB
    }
    payload = {
        "event_type": "error",
        "message": "Large payload simulation",
    }
    response = await async_client.post(
        "/api/v1/telemetry",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 413
    assert "exceeds maximum limit" in response.json()["detail"]
