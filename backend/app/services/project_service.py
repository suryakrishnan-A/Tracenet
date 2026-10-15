"""Project and Scoped Credential Business Logic Service."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Tuple, Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.project import Project
from app.models.ingestion_key import IngestionKey
from app.schemas.project import ProjectCreate
from app.core.security import (
    generate_management_key,
    generate_ingestion_key,
    hash_api_key,
    INGESTION_KEY_PREFIX,
    MANAGEMENT_KEY_PREFIX,
)

logger = logging.getLogger(__name__)

ROLE_MANAGEMENT = "management"
ROLE_INGEST = "ingest_only"


async def create_project(
    db: AsyncSession,
    project_in: ProjectCreate,
) -> Tuple[Project, str, str]:
    """Create a new project, a management credential, and an initial scoped ingestion credential.

    Returns:
        (project, raw_management_key, raw_ingestion_key)
    Only SHA-256 hashes are persisted. Raw keys are returned strictly once.
    """
    raw_mgmt_key = generate_management_key()
    mgmt_hash = hash_api_key(raw_mgmt_key)

    project = Project(
        name=project_in.name.strip(),
        api_key_hash=mgmt_hash,
    )
    db.add(project)
    await db.flush()

    # Automatically provision initial scoped ingestion key
    raw_ingest_key = generate_ingestion_key()
    ingest_hash = hash_api_key(raw_ingest_key)
    default_ingest_key = IngestionKey(
        project_id=project.id,
        name="Default Ingestion Key",
        key_hash=ingest_hash,
        key_prefix=INGESTION_KEY_PREFIX,
        is_active=True,
    )
    db.add(default_ingest_key)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Created project id={project.id} name='{project.name}' with initial scoped ingestion key")
    return project, raw_mgmt_key, raw_ingest_key


async def authenticate_api_key(
    db: AsyncSession,
    raw_api_key: str,
) -> Tuple[Optional[Project], Optional[str], Optional[IngestionKey]]:
    """Authenticate raw credential and resolve tenant project and permission role.

    Resolution Strategy:
    1. Check active scoped ingestion keys (`IngestionKey` with `is_active=True`).
       Role: 'ingest_only' (Restricted solely to telemetry submission).
    2. Check project management credentials (`Project.api_key_hash`).
       Role: 'management' (Full project administration and telemetry submission).
    3. Return None if neither matches.
    """
    if not raw_api_key or not raw_api_key.strip():
        return None, None, None

    hashed_key = hash_api_key(raw_api_key)

    # 1. Check scoped ingestion keys
    ingest_query = (
        select(IngestionKey)
        .options(joinedload(IngestionKey.project))
        .where(IngestionKey.key_hash == hashed_key, IngestionKey.is_active == True)
    )
    ingest_res = await db.execute(ingest_query)
    ingestion_key = ingest_res.scalar_one_or_none()

    if ingestion_key and ingestion_key.project:
        return ingestion_key.project, ROLE_INGEST, ingestion_key

    # 2. Check management key
    mgmt_query = select(Project).where(Project.api_key_hash == hashed_key)
    mgmt_res = await db.execute(mgmt_query)
    project = mgmt_res.scalar_one_or_none()

    if project:
        return project, ROLE_MANAGEMENT, None

    return None, None, None


async def get_project_by_api_key(db: AsyncSession, raw_api_key: str) -> Optional[Project]:
    """Retrieve project by either credential type (kept for backward compatibility)."""
    project, _, _ = await authenticate_api_key(db, raw_api_key)
    return project


async def rotate_project_api_key(db: AsyncSession, project: Project) -> Tuple[Project, str]:
    """Rotate the management credential for an authorized project.

    Generates a new raw management key, replaces the stored hash, and invalidates previous key.
    """
    new_raw_key = generate_management_key()
    new_hash = hash_api_key(new_raw_key)

    project.api_key_hash = new_hash
    await db.commit()
    await db.refresh(project)

    logger.info(f"Rotated management API key for project id={project.id}")
    return project, new_raw_key


async def create_ingestion_key(
    db: AsyncSession,
    project: Project,
    name: str = "Application Ingestion Key",
) -> Tuple[IngestionKey, str]:
    """Provision a new scoped ingestion credential for the project.

    The raw key is returned once for presentation. Only the SHA-256 hash is stored.
    """
    raw_key = generate_ingestion_key()
    hashed = hash_api_key(raw_key)

    ingest_key = IngestionKey(
        project_id=project.id,
        name=name.strip() or "Application Ingestion Key",
        key_hash=hashed,
        key_prefix=INGESTION_KEY_PREFIX,
        is_active=True,
    )
    db.add(ingest_key)
    await db.commit()
    await db.refresh(ingest_key)

    logger.info(f"Provisioned new ingestion key id={ingest_key.id} for project id={project.id}")
    return ingest_key, raw_key


async def list_ingestion_keys(
    db: AsyncSession,
    project: Project,
) -> Sequence[IngestionKey]:
    """List all ingestion credentials (active and revoked) for an authorized project."""
    query = (
        select(IngestionKey)
        .where(IngestionKey.project_id == project.id)
        .order_by(IngestionKey.created_at.desc())
    )
    res = await db.execute(query)
    return res.scalars().all()


async def revoke_ingestion_key(
    db: AsyncSession,
    project: Project,
    key_id: uuid.UUID,
) -> Optional[IngestionKey]:
    """Revoke a scoped ingestion credential. Immediately terminates ingestion authorization."""
    query = select(IngestionKey).where(
        IngestionKey.id == key_id,
        IngestionKey.project_id == project.id,
    )
    res = await db.execute(query)
    ingest_key = res.scalar_one_or_none()
    if not ingest_key:
        return None

    ingest_key.is_active = False
    ingest_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ingest_key)

    logger.info(f"Revoked ingestion key id={ingest_key.id} for project id={project.id}")
    return ingest_key


async def rotate_ingestion_key(
    db: AsyncSession,
    project: Project,
    key_id: uuid.UUID,
) -> Optional[Tuple[IngestionKey, str]]:
    """Rotate an ingestion credential: revokes old key and provisions an active replacement."""
    old_key = await revoke_ingestion_key(db, project, key_id)
    if not old_key:
        return None

    # Provision replacement with identical name
    return await create_ingestion_key(db, project, name=old_key.name)
