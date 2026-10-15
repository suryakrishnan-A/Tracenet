"""IssueGroup Model."""

import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.telemetry_event import TelemetryEvent


class IssueGroup(Base):
    """Represents a grouped cluster of related error events sharing a deterministic fingerprint."""

    __tablename__ = "issue_groups"

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
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Deterministic SHA-256 hash identifying this failure cluster",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Representative error title or summary",
    )
    current_severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="error",
        index=True,
        doc="Current/highest observed severity: info, warning, error, critical",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unresolved",
        index=True,
        doc="Investigation status: unresolved, investigating, resolved, ignored",
    )
    occurrence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Cumulative number of times this error cluster has been ingested",
    )
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp of first occurrence",
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="Timestamp of most recent occurrence",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="issue_groups",
    )
    events: Mapped[List["TelemetryEvent"]] = relationship(
        "TelemetryEvent",
        back_populates="issue_group",
        order_by="desc(TelemetryEvent.timestamp)",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "fingerprint", name="uq_project_fingerprint"),
        Index("ix_issues_project_status", "project_id", "status"),
        Index("ix_issues_project_severity", "project_id", "current_severity"),
        Index("ix_issues_project_last_seen", "project_id", "last_seen"),
    )

    def __repr__(self) -> str:
        return f"<IssueGroup id={self.id} fingerprint={self.fingerprint[:8]} status={self.status} count={self.occurrence_count}>"
