"""Tests for Project Management Endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.project import Project
from app.core.security import hash_api_key


@pytest.mark.asyncio
async def test_create_project_success(async_client: AsyncClient, db_session: AsyncSession):
    """Test successful project registration, API key generation, and hash persistence."""
    payload = {"name": "Payment Gateway Service"}
    response = await async_client.post("/api/v1/projects", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Payment Gateway Service"
    assert "id" in data
    assert "api_key" in data
    raw_api_key = data["api_key"]
    assert raw_api_key.startswith("tn_mgmt_") or raw_api_key.startswith("tn_live_")
    assert "ingestion_key" in data
    assert data["ingestion_key"].startswith("tn_ingest_")

    # Verify event persistence and ensure raw API key is NEVER stored in database
    result = await db_session.execute(
        select(Project).where(Project.name == "Payment Gateway Service")
    )
    db_project = result.scalar_one_or_none()
    assert db_project is not None
    assert db_project.api_key_hash == hash_api_key(raw_api_key)
    assert raw_api_key not in db_project.api_key_hash


@pytest.mark.asyncio
async def test_create_project_validation_failure(async_client: AsyncClient):
    """Test project creation rejects empty names or invalid JSON structures."""
    # Empty string name
    res1 = await async_client.post("/api/v1/projects", json={"name": ""})
    assert res1.status_code == 422

    # Missing name field
    res2 = await async_client.post("/api/v1/projects", json={})
    assert res2.status_code == 422
