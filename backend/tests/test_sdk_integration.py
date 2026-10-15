"""End-to-End Integration Tests for TraceNest Python SDK against Live FastAPI Backend."""

import pytest
import httpx
from httpx import ASGITransport, AsyncClient

from app.main import app
from tracenest import AsyncTraceNest, TraceNestDeliveryError


@pytest.mark.asyncio
async def test_sdk_e2e_event_delivery_and_persistence(async_client: AsyncClient):
    """Verify SDK transmits telemetry, backend authenticates, persists, and groups the issue."""
    # 1. Register a project through backend API
    reg_res = await async_client.post("/api/v1/projects", json={"name": "SDK E2E Test App"})
    assert reg_res.status_code == 201
    proj_data = reg_res.json()
    api_key = proj_data["api_key"]
    project_id = proj_data["id"]

    # 2. Wire Python SDK to backend using async_client
    async with AsyncTraceNest(api_key=api_key, client=async_client) as sdk:
        # Trigger and capture a simulated application exception
        try:
            raise ConnectionResetError("Database connection dropped during payment checkout")
        except ConnectionResetError as exc:
            delivery = await sdk.capture_exception(
                exc,
                endpoint="/api/v1/checkout/process",
                http_status=500,
                duration_ms=210.5,
                request_id="trace-req-e2e-001",
                metadata={"cart_id": "cart_1001", "retry_count": 2},
            )

    # 3. Verify SDK delivery response
    assert delivery.success is True
    assert delivery.status_code == 201
    assert delivery.event_id is not None
    assert delivery.project_id == project_id
    assert delivery.issue_id is not None
    assert delivery.fingerprint is not None

    # 4. Query backend issues endpoint to confirm issue group creation
    issues_res = await async_client.get(
        "/api/v1/issues",
        headers={"X-API-Key": api_key},
    )
    assert issues_res.status_code == 200
    issue_list = issues_res.json()
    assert issue_list["total"] == 1
    created_issue = issue_list["items"][0]
    assert created_issue["id"] == delivery.issue_id
    assert created_issue["occurrence_count"] == 1
    assert "ConnectionResetError" in created_issue["title"]


@pytest.mark.asyncio
async def test_sdk_e2e_issue_grouping_on_repeated_errors(async_client: AsyncClient):
    """Verify repeated equivalent errors sent via SDK join the exact same issue group."""
    # 1. Create project
    reg_res = await async_client.post("/api/v1/projects", json={"name": "Grouping App"})
    api_key = reg_res.json()["api_key"]

    async with AsyncTraceNest(api_key=api_key, client=async_client) as sdk:
        # Capture error 1
        try:
            raise KeyError("missing_auth_header")
        except KeyError as exc:
            res1 = await sdk.capture_exception(exc, endpoint="/api/v1/user/profile")

        # Capture equivalent error 2 (different metadata/timing, same stack & exception)
        try:
            raise KeyError("missing_auth_header")
        except KeyError as exc:
            res2 = await sdk.capture_exception(exc, endpoint="/api/v1/user/profile")

    assert res1.success is True
    assert res2.success is True
    assert res1.issue_id == res2.issue_id
    assert res1.fingerprint == res2.fingerprint

    # Verify occurrence count incremented to 2
    issue_res = await async_client.get(
        f"/api/v1/issues/{res1.issue_id}",
        headers={"X-API-Key": api_key},
    )
    assert issue_res.status_code == 200
    issue_data = issue_res.json()["issue"]
    recent_events = issue_res.json()["recent_events"]

    assert issue_data["occurrence_count"] == 2
    assert len(recent_events) == 2


@pytest.mark.asyncio
async def test_sdk_e2e_unauthorized_rejection(async_client: AsyncClient):
    """Verify SDK handles unauthorized responses gracefully without modifying app exceptions."""
    # Client with invalid key
    async with AsyncTraceNest(api_key="tn_live_invalid_bad_key_123", client=async_client) as sdk:
        res = await sdk.capture_event("Operational failure", severity="error")

    assert res.success is False
    assert res.status_code == 401
    assert "rejected telemetry with HTTP 401" in res.error

    # Verify raise_on_delivery_error raises TraceNestDeliveryError
    raising_sdk = AsyncTraceNest(
        api_key="tn_live_invalid_bad_key_123",
        raise_on_delivery_error=True,
        client=async_client,
    )
    with pytest.raises(TraceNestDeliveryError) as exc_info:
        await raising_sdk.capture_event("Boom")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_sdk_e2e_multi_project_tenant_isolation(async_client: AsyncClient):
    """Verify telemetry and issue groups from different projects remain strictly isolated."""
    # Register Project Alpha
    res_a = await async_client.post("/api/v1/projects", json={"name": "Project Alpha"})
    key_a = res_a.json()["api_key"]

    # Register Project Beta
    res_b = await async_client.post("/api/v1/projects", json={"name": "Project Beta"})
    key_b = res_b.json()["api_key"]

    # SDK for Project Alpha
    async with AsyncTraceNest(api_key=key_a, client=async_client) as sdk_a:
        await sdk_a.capture_event("Alpha distinct incident", severity="warning")

    # SDK for Project Beta
    async with AsyncTraceNest(api_key=key_b, client=async_client) as sdk_b:
        await sdk_b.capture_event("Beta distinct incident", severity="critical")

    # Project Alpha must only see Alpha's issues
    issues_a = (await async_client.get("/api/v1/issues", headers={"X-API-Key": key_a})).json()
    assert issues_a["total"] == 1
    assert "Alpha distinct incident" in issues_a["items"][0]["title"]

    # Project Beta must only see Beta's issues
    issues_b = (await async_client.get("/api/v1/issues", headers={"X-API-Key": key_b})).json()
    assert issues_b["total"] == 1
    assert "Beta distinct incident" in issues_b["items"][0]["title"]
