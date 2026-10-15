"""TelemetryEvent Model."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.issue_group import IssueGroup


class TelemetryEvent(Base):
    """Represents an ingested application event, failure, error, or metric."""

    __tablename__ = "telemetry_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("issue_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated IssueGroup cluster if error/failure event",
    )
    fingerprint: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Deterministic error fingerprint",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of event: e.g. error, metric, log, exception",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Severity: info, warning, error, critical",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable summary or error message",
    )
    stack_trace: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Raw stack trace or error backtrace",
    )
    endpoint: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        index=True,
        doc="Associated HTTP endpoint / route if applicable",
    )
    http_status: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Associated HTTP response status code",
    )
    duration_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Request or operation duration in milliseconds",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Arbitrary structured contextual attributes",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Client-side timestamp of event occurrence",
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="Timestamp when TraceNest ingested the event",
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="events",
    )
    issue_group: Mapped[Optional["IssueGroup"]] = relationship(
        "IssueGroup",
        back_populates="events",
    )

    __table_args__ = (
        Index("ix_telemetry_project_time", "project_id", "timestamp"),
        Index("ix_telemetry_project_sev", "project_id", "severity"),
        Index("ix_telemetry_project_type", "project_id", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<TelemetryEvent id={self.id} type={self.event_type} severity={self.severity}>"
