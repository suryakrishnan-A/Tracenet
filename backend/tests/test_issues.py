"""Integration and End-to-End Tests for Issue Grouping, Deduplication, and Issues API."""

import pytest
import asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.issue_group import IssueGroup
from app.models.telemetry_event import TelemetryEvent


@pytest.fixture
async def project_a(async_client: AsyncClient) -> dict:
    """Fixture creating primary test project."""
    res = await async_client.post("/api/v1/projects", json={"name": "Billing Service"})
    assert res.status_code == 201
    return res.json()


@pytest.fixture
async def project_b(async_client: AsyncClient) -> dict:
    """Fixture creating secondary test project for isolation testing."""
    res = await async_client.post("/api/v1/projects", json={"name": "Notification Service"})
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_repeated_equivalent_errors_group_into_single_issue(
    async_client: AsyncClient,
    project_a: dict,
    db_session: AsyncSession,
):
    """Test that two equivalent errors differing only by volatile memory addresses group together."""
    headers = {"X-API-Key": project_a["api_key"]}
    trace1 = (
        'Traceback (most recent call last):\n'
        '  File "billing.py", line 42, in charge\n'
        '    obj = <Gateway object at 0x7fa1203001a0>\n'
        'ConnectionError: Gateway timeout\n'
    )
    trace2 = (
        'Traceback (most recent call last):\n'
        '  File "billing.py", line 42, in charge\n'
        '    obj = <Gateway object at 0x000002EE59C986B0>\n'
        'ConnectionError: Gateway timeout\n'
    )

    # Ingest occurrence 1
    res1 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "error",
            "message": "Gateway timeout",
            "stack_trace": trace1,
        },
        headers=headers,
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["issue_id"] is not None

    # Ingest occurrence 2
    res2 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "error",
            "message": "Gateway timeout",
            "stack_trace": trace2,
        },
        headers=headers,
    )
    assert res2.status_code == 201
    data2 = res2.json()

    # Both occurrences must resolve to the SAME IssueGroup and fingerprint
    assert data1["issue_id"] == data2["issue_id"]
    assert data1["fingerprint"] == data2["fingerprint"]

    # Verify database state
    issue_id = uuid.UUID(data1["issue_id"])
    result = await db_session.execute(select(IssueGroup).where(IssueGroup.id == issue_id))
    issue = result.scalar_one()
    assert issue.occurrence_count == 2
    assert issue.status == "unresolved"
    assert issue.first_seen <= issue.last_seen


@pytest.mark.asyncio
async def test_different_errors_produce_separate_issue_groups(
    async_client: AsyncClient,
    project_a: dict,
    db_session: AsyncSession,
):
    """Distinct errors produce separate IssueGroup records with distinct fingerprints."""
    headers = {"X-API-Key": project_a["api_key"]}

    res1 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "error",
            "message": "KeyError: 'card_token'",
            "stack_trace": 'File "card.py", line 12, in parse\nKeyError: "card_token"',
        },
        headers=headers,
    )
    assert res1.status_code == 201

    res2 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "critical",
            "message": "ZeroDivisionError: integer division or modulo by zero",
            "stack_trace": 'File "math_util.py", line 9, in divide\nZeroDivisionError: division',
        },
        headers=headers,
    )
    assert res2.status_code == 201

    data1 = res1.json()
    data2 = res2.json()

    assert data1["issue_id"] != data2["issue_id"]
    assert data1["fingerprint"] != data2["fingerprint"]

    # Verify 2 distinct issue groups exist in database
    result = await db_session.execute(
        select(IssueGroup).where(IssueGroup.project_id == uuid.UUID(project_a["id"]))
    )
    issues = list(result.scalars().all())
    assert len(issues) == 2


@pytest.mark.asyncio
async def test_severity_escalates_on_subsequent_occurrence(
    async_client: AsyncClient,
    project_a: dict,
    db_session: AsyncSession,
):
    """When a subsequent event has higher severity (critical > warning), IssueGroup escalates."""
    headers = {"X-API-Key": project_a["api_key"]}
    trace = 'File "worker.py", line 10, in run\nWorkerFault: degradation'

    # 1. Initial occurrence with 'warning'
    res1 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "warning",
            "message": "Worker degradation warning",
            "stack_trace": trace,
        },
        headers=headers,
    )
    assert res1.status_code == 201
    issue_id = uuid.UUID(res1.json()["issue_id"])

    # Verify initial severity
    issue_before = (
        await db_session.execute(select(IssueGroup).where(IssueGroup.id == issue_id))
    ).scalar_one()
    assert issue_before.current_severity == "warning"

    # 2. Subsequent occurrence with 'critical'
    res2 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "critical",
            "message": "Worker degradation warning",
            "stack_trace": trace,
        },
        headers=headers,
    )
    assert res2.status_code == 201

    # Verify severity was escalated
    await db_session.refresh(issue_before)
    assert issue_before.current_severity == "critical"
    assert issue_before.occurrence_count == 2


@pytest.mark.asyncio
async def test_missing_stack_trace_grouping(
    async_client: AsyncClient,
    project_a: dict,
):
    """Telemetry without stack traces groups properly using fallback fields."""
    headers = {"X-API-Key": project_a["api_key"]}

    res1 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "error",
            "message": "HTTP 503 Service Unavailable",
            "endpoint": "/api/v1/sync",
            "http_status": 503,
        },
        headers=headers,
    )
    assert res1.status_code == 201

    res2 = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "error",
            "message": "HTTP 503 Service Unavailable",
            "endpoint": "/api/v1/sync",
            "http_status": 503,
        },
        headers=headers,
    )
    assert res2.status_code == 201

    assert res1.json()["issue_id"] == res2.json()["issue_id"]


@pytest.mark.asyncio
async def test_list_issues_filtering_and_pagination(
    async_client: AsyncClient,
    project_a: dict,
):
    """Test GET /api/v1/issues with status, severity, and search filters."""
    headers = {"X-API-Key": project_a["api_key"]}

    # Create 3 distinct issues
    for msg, sev in [
        ("AuthTokenExpired: session ended", "warning"),
        ("DatabaseTimeout: query exceeded limit", "error"),
        ("OutofMemory: worker crashed", "critical"),
    ]:
        res = await async_client.post(
            "/api/v1/telemetry",
            json={"event_type": "error", "severity": sev, "message": msg},
            headers=headers,
        )
        assert res.status_code == 201

    # 1. List all (total 3)
    list_res = await async_client.get("/api/v1/issues", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # 2. Filter by severity=critical
    crit_res = await async_client.get("/api/v1/issues?severity=critical", headers=headers)
    assert crit_res.status_code == 200
    assert crit_res.json()["total"] == 1
    assert crit_res.json()["items"][0]["current_severity"] == "critical"

    # 3. Filter by search=Timeout
    search_res = await async_client.get("/api/v1/issues?search=Timeout", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert "DatabaseTimeout" in search_res.json()["items"][0]["title"]

    # 4. Pagination (per_page=1)
    page_res = await async_client.get("/api/v1/issues?page=1&per_page=1", headers=headers)
    assert page_res.status_code == 200
    assert len(page_res.json()["items"]) == 1
    assert page_res.json()["total_pages"] == 3


@pytest.mark.asyncio
async def test_get_issue_details_and_recent_events(
    async_client: AsyncClient,
    project_a: dict,
):
    """Test GET /api/v1/issues/{issue_id} returns issue and recent occurrences."""
    headers = {"X-API-Key": project_a["api_key"]}

    # Ingest 2 events for same issue
    res1 = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "error", "message": "Disk write failure"},
        headers=headers,
    )
    issue_id = res1.json()["issue_id"]

    await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "error", "message": "Disk write failure"},
        headers=headers,
    )

    detail_res = await async_client.get(f"/api/v1/issues/{issue_id}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["issue"]["id"] == issue_id
    assert data["issue"]["occurrence_count"] == 2
    assert len(data["recent_events"]) == 2
    assert data["recent_events"][0]["message"] == "Disk write failure"


@pytest.mark.asyncio
async def test_patch_issue_status(
    async_client: AsyncClient,
    project_a: dict,
):
    """Test PATCH /api/v1/issues/{issue_id} status transitions."""
    headers = {"X-API-Key": project_a["api_key"]}

    res = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "error", "message": "NullPointerException"},
        headers=headers,
    )
    issue_id = res.json()["issue_id"]

    # Update to 'investigating'
    p1 = await async_client.patch(
        f"/api/v1/issues/{issue_id}",
        json={"status": "investigating"},
        headers=headers,
    )
    assert p1.status_code == 200
    assert p1.json()["status"] == "investigating"

    # Update to 'resolved'
    p2 = await async_client.patch(
        f"/api/v1/issues/{issue_id}",
        json={"status": "resolved"},
        headers=headers,
    )
    assert p2.status_code == 200
    assert p2.json()["status"] == "resolved"

    # Reject invalid status
    bad = await async_client.patch(
        f"/api/v1/issues/{issue_id}",
        json={"status": "not_a_real_status"},
        headers=headers,
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_project_isolation_on_issues(
    async_client: AsyncClient,
    project_a: dict,
    project_b: dict,
):
    """Project B must NOT be able to access or modify Project A's issue."""
    headers_a = {"X-API-Key": project_a["api_key"]}
    headers_b = {"X-API-Key": project_b["api_key"]}

    # Create issue in Project A
    res = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "error", "message": "Sensitive payment error"},
        headers=headers_a,
    )
    issue_a_id = res.json()["issue_id"]

    # Project B tries to GET Project A's issue
    get_res = await async_client.get(f"/api/v1/issues/{issue_a_id}", headers=headers_b)
    assert get_res.status_code == 404

    # Project B tries to PATCH Project A's issue
    patch_res = await async_client.patch(
        f"/api/v1/issues/{issue_a_id}",
        json={"status": "resolved"},
        headers=headers_b,
    )
    assert patch_res.status_code == 404

    # Project B's issue list should be empty
    list_b = await async_client.get("/api/v1/issues", headers=headers_b)
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0


@pytest.mark.asyncio
async def test_concurrent_telemetry_ingestion_safety(
    async_client: AsyncClient,
    project_a: dict,
    db_session: AsyncSession,
):
    """Simulate concurrent ingestion of the same error to test atomic upsert safety."""
    headers = {"X-API-Key": project_a["api_key"]}
    trace = 'File "concurrency.py", line 5, in race\nRuntimeError: lock conflict'

    payload = {
        "event_type": "error",
        "severity": "error",
        "message": "lock conflict",
        "stack_trace": trace,
    }

    # Dispatch 5 concurrent requests
    responses = await asyncio.gather(*[
        async_client.post("/api/v1/telemetry", json=payload, headers=headers)
        for _ in range(5)
    ])

    for r in responses:
        assert r.status_code == 201

    issue_ids = {r.json()["issue_id"] for r in responses}
    # All 5 requests must map to exactly 1 IssueGroup
    assert len(issue_ids) == 1

    issue_id = uuid.UUID(list(issue_ids)[0])
    issue = (
        await db_session.execute(select(IssueGroup).where(IssueGroup.id == issue_id))
    ).scalar_one()

    # Occurrence counter must equal exactly 5
    assert issue.occurrence_count == 5
