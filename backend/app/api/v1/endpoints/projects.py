"""Projects and Credential Management API Endpoints."""

import uuid
from typing import List, Sequence
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectRead,
    ProjectRotateResponse,
    IngestionKeyCreate,
    IngestionKeyRead,
    IngestionKeyCreatedResponse,
)
from app.services.project_service import (
    create_project,
    rotate_project_api_key,
    create_ingestion_key,
    list_ingestion_keys,
    revoke_ingestion_key,
    rotate_ingestion_key,
)

router = APIRouter()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Project",
    description=(
        "Registers a new monitored project and returns one-time raw credentials: "
        "a project management key ('tn_mgmt_...') and a scoped ingestion key ('tn_ingest_...'). "
        "The raw keys are never stored in the database (only SHA-256 hashes)."
    ),
)
async def register_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create project and return initial management and ingestion credentials."""
    project, raw_mgmt_key, raw_ingest_key = await create_project(db, project_in)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        api_key=raw_mgmt_key,
        ingestion_key=raw_ingest_key,
        created_at=project.created_at,
    )


@router.get(
    "/me",
    response_model=ProjectRead,
    summary="Get Current Project Information",
    description="Returns metadata for the authenticated project. Requires management key.",
)
async def get_current_project_info(
    project: Project = Depends(get_current_project),
) -> ProjectRead:
    """Return currently authenticated project details without exposing secret key material."""
    return ProjectRead(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
    )


@router.post(
    "/rotate-key",
    response_model=ProjectRotateResponse,
    summary="Rotate Project Management Key",
    description=(
        "Immediately invalidates the currently authenticated management key and generates a new one. "
        "The new raw key is shown only once and must be stored securely."
    ),
)
async def rotate_current_project_key(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> ProjectRotateResponse:
    """Rotate the authenticated project's management API key."""
    rotated_proj, new_raw_key = await rotate_project_api_key(db, project)
    return ProjectRotateResponse(
        id=rotated_proj.id,
        name=rotated_proj.name,
        api_key=new_raw_key,
        message="Management API key rotated successfully. Store securely; previous key is now invalidated.",
        created_at=rotated_proj.created_at,
    )


# ------------------------------------------------------------------------------
# Scoped Ingestion Key Management Endpoints
# ------------------------------------------------------------------------------

@router.post(
    "/ingestion-keys",
    response_model=IngestionKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a Scoped Ingestion Key",
    description=(
        "Generates a new scoped ingestion token ('tn_ingest_...') restricted solely to telemetry ingestion. "
        "Requires project management key authorization. The raw key is returned only once."
    ),
)
async def provision_ingestion_key(
    key_in: IngestionKeyCreate = IngestionKeyCreate(),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> IngestionKeyCreatedResponse:
    """Create a new scoped ingestion key."""
    key_record, raw_key = await create_ingestion_key(db, project, name=key_in.name)
    return IngestionKeyCreatedResponse(
        id=key_record.id,
        project_id=project.id,
        name=key_record.name,
        ingestion_key=raw_key,
        key_prefix=key_record.key_prefix,
        is_active=key_record.is_active,
        created_at=key_record.created_at,
    )


@router.get(
    "/ingestion-keys",
    response_model=List[IngestionKeyRead],
    summary="List Project Ingestion Keys",
    description="Returns metadata for all ingestion keys associated with the authorized project (active and revoked).",
)
async def list_project_ingestion_keys(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> Sequence[IngestionKeyRead]:
    """List ingestion credentials without secret material."""
    keys = await list_ingestion_keys(db, project)
    return [IngestionKeyRead.model_validate(k) for k in keys]


@router.delete(
    "/ingestion-keys/{key_id}",
    response_model=IngestionKeyRead,
    summary="Revoke an Ingestion Key",
    description="Immediately revokes a scoped ingestion token. Further telemetry submissions using this key will be rejected.",
)
async def revoke_project_ingestion_key(
    key_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> IngestionKeyRead:
    """Revoke an existing ingestion credential."""
    revoked = await revoke_ingestion_key(db, project, key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion key with ID '{key_id}' not found in this project.",
        )
    return IngestionKeyRead.model_validate(revoked)


@router.post(
    "/ingestion-keys/{key_id}/rotate",
    response_model=IngestionKeyCreatedResponse,
    summary="Rotate an Ingestion Key",
    description="Atomically revokes an existing ingestion key and returns a newly active scoped replacement.",
)
async def rotate_project_ingestion_key(
    key_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> IngestionKeyCreatedResponse:
    """Rotate an ingestion credential."""
    rotated = await rotate_ingestion_key(db, project, key_id)
    if not rotated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion key with ID '{key_id}' not found in this project.",
        )
    new_key_record, raw_new_key = rotated
    return IngestionKeyCreatedResponse(
        id=new_key_record.id,
        project_id=project.id,
        name=new_key_record.name,
        ingestion_key=raw_new_key,
        key_prefix=new_key_record.key_prefix,
        is_active=new_key_record.is_active,
        created_at=new_key_record.created_at,
    )
