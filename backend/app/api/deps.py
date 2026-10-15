"""API Authentication and Dependency Injection with Scoped Credential Enforcement."""

from typing import Optional, Tuple
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.project import Project
from app.services.project_service import authenticate_api_key, ROLE_MANAGEMENT, ROLE_INGEST


async def get_authenticated_project(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Project, str]:
    """Authenticate incoming request credentials and resolve project tenant & role.

    Extracts credential from 'X-API-Key' or 'Authorization: Bearer <token>'.
    Rejects missing or invalid credentials with HTTP 401.
    """
    api_key: Optional[str] = None

    if x_api_key and x_api_key.strip():
        api_key = x_api_key.strip()
    elif authorization and authorization.strip():
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            api_key = parts[1]
        elif len(parts) == 1:
            api_key = parts[0]

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via 'X-API-Key' header or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    project, role, _ = await authenticate_api_key(db, api_key)
    if not project or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return project, role


async def get_management_project(
    auth: Tuple[Project, str] = Depends(get_authenticated_project),
) -> Project:
    """Enforce that incoming request is authenticated with a management credential.

    Restricted ingestion credentials ('tn_ingest_...') are rejected with HTTP 403 Forbidden.
    """
    project, role = auth
    if role != ROLE_MANAGEMENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Forbidden: Ingestion credentials ('tn_ingest_...') are restricted solely to telemetry submission. "
                "Management and incident investigation endpoints require a project management key."
            ),
        )
    return project


async def get_telemetry_project(
    auth: Tuple[Project, str] = Depends(get_authenticated_project),
) -> Project:
    """Authenticate telemetry ingestion endpoint.

    Permits both scoped ingestion keys ('tn_ingest_...') and management keys (backward compatibility).
    """
    project, _ = auth
    return project


# Alias get_current_project to get_management_project to protect all issue,
# investigation, and project management routes by default.
get_current_project = get_management_project
