"""Telemetry Ingestion Business Logic Service."""

import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.telemetry_event import TelemetryEvent
from app.schemas.telemetry import TelemetryEventCreate
from app.services.fingerprint_service import compute_fingerprint
from app.services.issue_service import upsert_issue_group

logger = logging.getLogger(__name__)


async def ingest_event(
    db: AsyncSession,
    project: Project,
    event_in: TelemetryEventCreate,
) -> TelemetryEvent:
    """Validate, fingerprint, group, and persist an incoming telemetry event.
    
    1. Computes deterministic SHA-256 fingerprint from stable error attributes.
    2. Atomically upserts the corresponding IssueGroup (incrementing occurrence counter).
    3. Persists the TelemetryEvent linked to the IssueGroup within a single transaction.
    """
    event_time = event_in.timestamp or datetime.now(timezone.utc)

    # Compute deterministic fingerprint and representative title
    fingerprint, title = compute_fingerprint(
        project_id=project.id,
        message=event_in.message,
        stack_trace=event_in.stack_trace,
        event_type=event_in.event_type,
        endpoint=event_in.endpoint,
        http_status=event_in.http_status,
    )

    # Atomically associate or create IssueGroup
    issue_group = await upsert_issue_group(
        db=db,
        project_id=project.id,
        fingerprint=fingerprint,
        title=title,
        severity=event_in.severity,
        event_timestamp=event_time,
    )

    # Persist the TelemetryEvent linked to the IssueGroup
    event = TelemetryEvent(
        project_id=project.id,
        issue_group_id=issue_group.id,
        fingerprint=fingerprint,
        event_type=event_in.event_type,
        severity=event_in.severity,
        message=event_in.message,
        stack_trace=event_in.stack_trace,
        endpoint=event_in.endpoint,
        http_status=event_in.http_status,
        duration_ms=event_in.duration_ms,
        metadata_json=event_in.metadata or {},
        timestamp=event_time,
        received_at=datetime.now(timezone.utc),
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info(
        f"Persisted telemetry event id={event.id} type={event.event_type} "
        f"severity={event.severity} issue_id={issue_group.id} project_id={project.id}"
    )
    return event
