"""Tests for Scoped Ingestion Credentials & Permission Enforcement (Phase 8).

Verifies:
1. Registration provisions both management (tn_mgmt_*) and scoped ingestion (tn_ingest_*) keys.
2. Ingestion keys are strictly permitted to POST /api/v1/telemetry.
3. Ingestion keys are strictly FORBIDDEN (HTTP 403) from:
   - Project management (/projects/me, /projects/rotate-key, /projects/ingestion-keys)
   - Issue explorer (/issues, /issues/{id}, PATCH /issues/{id})
   - AI investigation (/issues/{id}/investigate)
4. Management keys retain full permissions (admin endpoints + backward-compatible telemetry).
5. Ingestion key lifecycle: create, list, revoke, and rotate.
6. Revoked and invalid credentials return HTTP 401.
7. Tenant isolation across projects.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.ingestion_key import IngestionKey
from app.core.security import hash_api_key, MANAGEMENT_KEY_PREFIX, INGESTION_KEY_PREFIX


@pytest.mark.asyncio
async def test_project_registration_provisions_both_keys(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Registering a project must return both management and scoped ingestion credentials."""
    payload = {"name": "Scoped Credential Test Service"}
    resp = await async_client.post("/api/v1/projects", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert "api_key" in data
    assert "ingestion_key" in data
    mgmt_key = data["api_key"]
    ingest_key = data["ingestion_key"]

    assert mgmt_key.startswith(MANAGEMENT_KEY_PREFIX)
    assert ingest_key.startswith(INGESTION_KEY_PREFIX)
    assert mgmt_key != ingest_key

    # Verify hashes in database; raw secrets must NEVER be persisted plaintext
    proj_id = uuid.UUID(data["id"])
    result = await db_session.execute(select(Project).where(Project.id == proj_id))
    project = result.scalar_one_or_none()
    assert project is not None
    assert project.api_key_hash == hash_api_key(mgmt_key)

    key_res = await db_session.execute(
        select(IngestionKey).where(IngestionKey.project_id == proj_id)
    )
    ingest_keys = list(key_res.scalars().all())
    assert len(ingest_keys) == 1
    assert ingest_keys[0].key_hash == hash_api_key(ingest_key)
    assert ingest_keys[0].is_active is True
    assert ingest_keys[0].revoked_at is None


@pytest.mark.asyncio
async def test_scoped_ingestion_key_submits_telemetry(async_client: AsyncClient):
    """Scoped ingestion key can successfully ingest telemetry."""
    # 1. Register project
    reg_resp = await async_client.post("/api/v1/projects", json={"name": "Ingestion Allowed App"})
    assert reg_resp.status_code == 201
    ingest_key = reg_resp.json()["ingestion_key"]

    # 2. Ingest telemetry using scoped key
    telemetry_payload = {
        "event_type": "error",
        "severity": "error",
        "message": "ConnectionRefusedError: Unable to connect to redis cache",
        "stack_trace": 'Traceback (most recent call last):\n  File "cache.py", line 12, in get\n    raise ConnectionRefusedError()',
        "service_name": "checkout-api",
        "environment": "production",
    }
    resp = await async_client.post(
        "/api/v1/telemetry",
        json=telemetry_payload,
        headers={"X-API-Key": ingest_key},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "received"
    assert "event_id" in body
    assert "issue_id" in body


@pytest.mark.asyncio
async def test_scoped_ingestion_key_blocked_from_management_endpoints(
    async_client: AsyncClient,
):
    """Scoped ingestion key must be rejected with HTTP 403 on all management endpoints."""
    reg_resp = await async_client.post("/api/v1/projects", json={"name": "Security Boundary Test"})
    ingest_key = reg_resp.json()["ingestion_key"]
    headers = {"X-API-Key": ingest_key}

    # GET /projects/me -> 403 Forbidden
    r_me = await async_client.get("/api/v1/projects/me", headers=headers)
    assert r_me.status_code == 403
    assert "Forbidden: Ingestion credentials" in r_me.json()["detail"]

    # POST /projects/rotate-key -> 403 Forbidden
    r_rotate = await async_client.post("/api/v1/projects/rotate-key", headers=headers)
    assert r_rotate.status_code == 403
    assert "Forbidden: Ingestion credentials" in r_rotate.json()["detail"]

    # GET /projects/ingestion-keys -> 403 Forbidden
    r_list = await async_client.get("/api/v1/projects/ingestion-keys", headers=headers)
    assert r_list.status_code == 403

    # POST /projects/ingestion-keys -> 403 Forbidden
    r_create = await async_client.post(
        "/api/v1/projects/ingestion-keys",
        json={"name": "Unauthorized Ingestion Key"},
        headers=headers,
    )
    assert r_create.status_code == 403

    # DELETE /projects/ingestion-keys/{dummy_id} -> 403 Forbidden
    r_del = await async_client.delete(
        f"/api/v1/projects/ingestion-keys/{uuid.uuid4()}",
        headers=headers,
    )
    assert r_del.status_code == 403


@pytest.mark.asyncio
async def test_scoped_ingestion_key_blocked_from_issues_and_investigations(
    async_client: AsyncClient,
):
    """Scoped ingestion key must be rejected with HTTP 403 on issues and AI investigations."""
    # 1. Register project
    reg_resp = await async_client.post("/api/v1/projects", json={"name": "Issue Security Test"})
    ingest_key = reg_resp.json()["ingestion_key"]
    mgmt_key = reg_resp.json()["api_key"]

    # 2. Ingest an event to generate an issue
    await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "critical",
            "message": "ZeroDivisionError: division by zero",
            "service_name": "billing",
        },
        headers={"X-API-Key": ingest_key},
    )

    # Fetch issue ID via management key
    issues_resp = await async_client.get("/api/v1/issues", headers={"X-API-Key": mgmt_key})
    assert issues_resp.status_code == 200
    issue_data = issues_resp.json()
    assert issue_data["total"] >= 1
    issue_id = issue_data["items"][0]["id"]

    # 3. Now verify Ingestion key is rejected with 403 on all issue/investigation routes
    ingest_headers = {"X-API-Key": ingest_key}

    # GET /issues -> 403
    r1 = await async_client.get("/api/v1/issues", headers=ingest_headers)
    assert r1.status_code == 403

    # GET /issues/{issue_id} -> 403
    r2 = await async_client.get(f"/api/v1/issues/{issue_id}", headers=ingest_headers)
    assert r2.status_code == 403

    # PATCH /issues/{issue_id} -> 403
    r3 = await async_client.patch(
        f"/api/v1/issues/{issue_id}",
        json={"status": "resolved"},
        headers=ingest_headers,
    )
    assert r3.status_code == 403

    # POST /issues/{issue_id}/investigate -> 403
    r4 = await async_client.post(
        f"/api/v1/issues/{issue_id}/investigate",
        headers=ingest_headers,
    )
    assert r4.status_code == 403


@pytest.mark.asyncio
async def test_management_key_retains_full_privileges(async_client: AsyncClient):
    """Management key can access both administrative endpoints and telemetry ingestion."""
    reg_resp = await async_client.post("/api/v1/projects", json={"name": "Full Access Project"})
    mgmt_key = reg_resp.json()["api_key"]
    headers = {"X-API-Key": mgmt_key}

    # 1. Telemetry ingestion works with management key (backward compatibility)
    t_resp = await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "error",
            "message": "IndexError: list index out of range",
            "service_name": "worker",
        },
        headers=headers,
    )
    assert t_resp.status_code == 201

    # 2. Get project me
    me_resp = await async_client.get("/api/v1/projects/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["name"] == "Full Access Project"

    # 3. List issues
    issues_resp = await async_client.get("/api/v1/issues", headers=headers)
    assert issues_resp.status_code == 200

    # 4. List ingestion keys
    keys_resp = await async_client.get("/api/v1/projects/ingestion-keys", headers=headers)
    assert keys_resp.status_code == 200
    assert len(keys_resp.json()) == 1


@pytest.mark.asyncio
async def test_ingestion_key_lifecycle_creation_revocation_rotation(
    async_client: AsyncClient,
):
    """Test full ingestion credential lifecycle: create, list, revoke, and rotate."""
    reg_resp = await async_client.post("/api/v1/projects", json={"name": "Lifecycle Project"})
    mgmt_key = reg_resp.json()["api_key"]
    mgmt_headers = {"X-API-Key": mgmt_key}

    # 1. Create a dedicated ingestion key for a specific environment
    create_resp = await async_client.post(
        "/api/v1/projects/ingestion-keys",
        json={"name": "Staging Backend SDK Key"},
        headers=mgmt_headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    staging_key_id = created_data["id"]
    staging_raw_key = created_data["ingestion_key"]
    assert staging_raw_key.startswith(INGESTION_KEY_PREFIX)
    assert created_data["name"] == "Staging Backend SDK Key"

    # 2. Verify staging key works for telemetry
    staging_headers = {"X-API-Key": staging_raw_key}
    t_resp = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "warning", "message": "Cache warm up delay"},
        headers=staging_headers,
    )
    assert t_resp.status_code == 201

    # 3. List ingestion keys - confirm raw secrets are NEVER exposed in list responses
    list_resp = await async_client.get("/api/v1/projects/ingestion-keys", headers=mgmt_headers)
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert len(keys) == 2  # initial default + staging
    for k in keys:
        assert "ingestion_key" not in k
        assert "key_hash" not in k
        assert "key_prefix" in k
        assert k["key_prefix"].startswith(INGESTION_KEY_PREFIX)
        assert k["is_active"] is True

    # 4. Revoke staging key
    del_resp = await async_client.delete(
        f"/api/v1/projects/ingestion-keys/{staging_key_id}",
        headers=mgmt_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["is_active"] is False
    assert del_resp.json()["revoked_at"] is not None

    # 5. Telemetry with revoked key must be rejected (401 Unauthorized)
    t_revoked_resp = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "error", "message": "Should be rejected"},
        headers=staging_headers,
    )
    assert t_revoked_resp.status_code == 401

    # 6. Rotate initial ingestion key
    initial_key = next(k for k in keys if k["id"] != staging_key_id)
    initial_key_id = initial_key["id"]
    rot_resp = await async_client.post(
        f"/api/v1/projects/ingestion-keys/{initial_key_id}/rotate",
        headers=mgmt_headers,
    )
    assert rot_resp.status_code == 200
    rotated_data = rot_resp.json()
    new_raw_key = rotated_data["ingestion_key"]
    assert new_raw_key.startswith(INGESTION_KEY_PREFIX)

    # Old initial key is now revoked and rejected
    old_initial_key = reg_resp.json()["ingestion_key"]
    t_old_resp = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "error", "message": "Old key rejected"},
        headers={"X-API-Key": old_initial_key},
    )
    assert t_old_resp.status_code == 401

    # New rotated key works
    t_new_resp = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "info", "message": "Rotated key works"},
        headers={"X-API-Key": new_raw_key},
    )
    assert t_new_resp.status_code == 201


@pytest.mark.asyncio
async def test_tenant_isolation_with_scoped_credentials(async_client: AsyncClient):
    """Telemetry sent via Project A's ingestion key must never leak into Project B."""
    # Register Project A
    resp_a = await async_client.post("/api/v1/projects", json={"name": "Tenant Alpha"})
    key_a_ingest = resp_a.json()["ingestion_key"]
    key_a_mgmt = resp_a.json()["api_key"]

    # Register Project B
    resp_b = await async_client.post("/api/v1/projects", json={"name": "Tenant Beta"})
    key_b_mgmt = resp_b.json()["api_key"]

    # Send event to Project A
    await async_client.post(
        "/api/v1/telemetry",
        json={
            "event_type": "error",
            "severity": "critical",
            "message": "AlphaSecretDataLeakException: confidential token",
            "service_name": "alpha-auth",
        },
        headers={"X-API-Key": key_a_ingest},
    )

    # Verify Project A has 1 issue
    issues_a = await async_client.get("/api/v1/issues", headers={"X-API-Key": key_a_mgmt})
    assert issues_a.status_code == 200
    assert issues_a.json()["total"] == 1
    assert "AlphaSecretDataLeakException" in issues_a.json()["items"][0]["title"]

    # Verify Project B has 0 issues
    issues_b = await async_client.get("/api/v1/issues", headers={"X-API-Key": key_b_mgmt})
    assert issues_b.status_code == 200
    assert issues_b.json()["total"] == 0
    assert len(issues_b.json()["items"]) == 0
