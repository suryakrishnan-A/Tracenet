"""Issue Grouping Business Logic and Persistence Service."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from app.models.issue_group import IssueGroup
from app.models.telemetry_event import TelemetryEvent

logger = logging.getLogger(__name__)

SEVERITY_RANKS = {"info": 1, "warning": 2, "error": 3, "critical": 4}


async def upsert_issue_group(
    db: AsyncSession,
    project_id: uuid.UUID,
    fingerprint: str,
    title: str,
    severity: str,
    event_timestamp: datetime,
) -> IssueGroup:
    """Atomically insert or update an IssueGroup using PostgreSQL ON CONFLICT.
    
    Guarantees:
      - Thread and process concurrency safety (no duplicate issue groups).
      - Atomic counter increment (occurrence_count = occurrence_count + 1).
      - Proper last_seen timestamp updates.
      - Severity escalation if incoming event has higher severity.
    """
    bind = db.bind
    is_postgres = bind is not None and "postgresql" in bind.dialect.name.lower()

    if is_postgres:
        insert_stmt = pg_insert(IssueGroup).values(
            id=uuid.uuid4(),
            project_id=project_id,
            fingerprint=fingerprint,
            title=title,
            current_severity=severity,
            status="unresolved",
            occurrence_count=1,
            first_seen=event_timestamp,
            last_seen=event_timestamp,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        stmt = (
            insert_stmt.on_conflict_do_update(
                constraint="uq_project_fingerprint",
                set_={
                    "occurrence_count": IssueGroup.occurrence_count + 1,
                    "last_seen": func.greatest(IssueGroup.last_seen, event_timestamp),
                    "updated_at": datetime.now(timezone.utc),
                    "current_severity": case(
                        (insert_stmt.excluded.current_severity == "critical", "critical"),
                        (
                            (IssueGroup.current_severity != "critical")
                            & (insert_stmt.excluded.current_severity == "error"),
                            "error",
                        ),
                        (
                            (IssueGroup.current_severity == "info")
                            & (insert_stmt.excluded.current_severity == "warning"),
                            "warning",
                        ),
                        else_=IssueGroup.current_severity,
                    ),
                },
            )
            .returning(IssueGroup)
        )
        result = await db.execute(stmt)
        issue_group = result.scalar_one()
        return issue_group

    # Generic fallback with retry on IntegrityError (for SQLite/other dialects)
    query = select(IssueGroup).where(
        IssueGroup.project_id == project_id,
        IssueGroup.fingerprint == fingerprint,
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        existing.occurrence_count += 1
        if event_timestamp > existing.last_seen:
            existing.last_seen = event_timestamp
        existing.updated_at = datetime.now(timezone.utc)
        if SEVERITY_RANKS.get(severity, 0) > SEVERITY_RANKS.get(existing.current_severity, 0):
            existing.current_severity = severity
        return existing
    else:
        new_group = IssueGroup(
            project_id=project_id,
            fingerprint=fingerprint,
            title=title,
            current_severity=severity,
            status="unresolved",
            occurrence_count=1,
            first_seen=event_timestamp,
            last_seen=event_timestamp,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_group)
        try:
            await db.flush()
            return new_group
        except IntegrityError:
            # Concurrent insert won race, query existing
            res = await db.execute(query)
            existing = res.scalar_one()
            existing.occurrence_count += 1
            if event_timestamp > existing.last_seen:
                existing.last_seen = event_timestamp
            existing.updated_at = datetime.now(timezone.utc)
            if SEVERITY_RANKS.get(severity, 0) > SEVERITY_RANKS.get(existing.current_severity, 0):
                existing.current_severity = severity
            return existing


async def list_issues(
    db: AsyncSession,
    project_id: uuid.UUID,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[IssueGroup], int]:
    """List issue groups for a project with filtering and pagination."""
    query = select(IssueGroup).where(IssueGroup.project_id == project_id)

    if status:
        query = query.where(IssueGroup.status == status.strip().lower())
    if severity:
        query = query.where(IssueGroup.current_severity == severity.strip().lower())
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            IssueGroup.title.ilike(search_pattern) | IssueGroup.fingerprint.ilike(search_pattern)
        )

    # Count total matching records
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply ordering and pagination
    offset = (page - 1) * per_page
    query = query.order_by(IssueGroup.last_seen.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total


async def get_issue_by_id(
    db: AsyncSession,
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
) -> Optional[IssueGroup]:
    """Retrieve an issue group by ID, strictly enforcing project ownership."""
    query = select(IssueGroup).where(
        IssueGroup.id == issue_id,
        IssueGroup.project_id == project_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_recent_events_for_issue(
    db: AsyncSession,
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
    limit: int = 10,
) -> List[TelemetryEvent]:
    """Retrieve recent telemetry events belonging to an issue group."""
    query = (
        select(TelemetryEvent)
        .where(
            TelemetryEvent.issue_group_id == issue_id,
            TelemetryEvent.project_id == project_id,
        )
        .order_by(TelemetryEvent.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_issue_status(
    db: AsyncSession,
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
    new_status: str,
) -> Optional[IssueGroup]:
    """Update issue status (unresolved, investigating, resolved, ignored)."""
    issue = await get_issue_by_id(db, project_id, issue_id)
    if not issue:
        return None

    issue.status = new_status.strip().lower()
    issue.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(issue)
    return issue
