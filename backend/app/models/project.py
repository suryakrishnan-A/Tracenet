"""Project Model."""

import uuid
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.telemetry_event import TelemetryEvent
    from app.models.issue_group import IssueGroup
    from app.models.ingestion_key import IngestionKey


class Project(Base):
    """Represents a monitored application or service registered in TraceNest."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    api_key_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
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
    events: Mapped[List["TelemetryEvent"]] = relationship(
        "TelemetryEvent",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(TelemetryEvent.timestamp)",
    )
    issue_groups: Mapped[List["IssueGroup"]] = relationship(
        "IssueGroup",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(IssueGroup.last_seen)",
    )
    ingestion_keys: Mapped[List["IngestionKey"]] = relationship(
        "IngestionKey",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(IngestionKey.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name='{self.name}'>"
