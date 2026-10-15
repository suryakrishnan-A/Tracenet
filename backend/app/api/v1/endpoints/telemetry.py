"""Telemetry Ingestion Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_telemetry_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.telemetry import TelemetryEventCreate, TelemetryIngestResponse
from app.services.telemetry_service import ingest_event

router = APIRouter()

MAX_PAYLOAD_BYTES = 1_048_576  # 1 MB maximum payload limit


@router.post(
    "",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Telemetry Event",
    description=(
        "Authenticates the project API key via 'X-API-Key' or 'Authorization: Bearer <key>', "
        "validates the telemetry event payload, and persists it. "
        "Accepts either scoped ingestion credentials ('tn_ingest_...') or management credentials."
    ),
)
async def ingest_telemetry_event(
    event_in: TelemetryEventCreate,
    request: Request,
    content_length: Optional[int] = Header(default=None),
    project: Project = Depends(get_telemetry_project),
    db: AsyncSession = Depends(get_db),
) -> TelemetryIngestResponse:
    """Ingest and persist a validated telemetry event."""
    if content_length and content_length > MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Payload size ({content_length} bytes) exceeds maximum limit ({MAX_PAYLOAD_BYTES} bytes).",
        )

    persisted_event = await ingest_event(db, project, event_in)

    return TelemetryIngestResponse(
        status="received",
        event_id=persisted_event.id,
        project_id=project.id,
        issue_id=persisted_event.issue_group_id,
        fingerprint=persisted_event.fingerprint,
        received_at=persisted_event.received_at,
    )
