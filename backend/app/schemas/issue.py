"""IssueGroup request and response schemas."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

AllowedStatus = Literal["unresolved", "investigating", "resolved", "ignored"]


class IssueGroupRead(BaseModel):
    """Schema representing an issue group cluster."""
    id: uuid.UUID
    project_id: uuid.UUID
    fingerprint: str
    title: str
    current_severity: str
    status: str
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TelemetryEventRead(BaseModel):
    """Schema representing an individual event associated with an issue."""
    id: uuid.UUID
    project_id: uuid.UUID
    issue_group_id: Optional[uuid.UUID] = None
    fingerprint: Optional[str] = None
    event_type: str
    severity: str
    message: str
    stack_trace: Optional[str] = None
    endpoint: Optional[str] = None
    http_status: Optional[int] = None
    duration_ms: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None
    timestamp: datetime
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueDetailResponse(BaseModel):
    """Detailed issue response including recent occurrences."""
    issue: IssueGroupRead
    recent_events: List[TelemetryEventRead] = Field(default_factory=list)


class IssueStatusUpdate(BaseModel):
    """Request schema for transitioning issue status."""
    status: AllowedStatus = Field(
        ...,
        description="New status: unresolved, investigating, resolved, or ignored",
        example="investigating",
    )

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip().lower()
            if cleaned not in ("unresolved", "investigating", "resolved", "ignored"):
                raise ValueError(
                    f"Invalid status '{v}'. Allowed: unresolved, investigating, resolved, ignored"
                )
            return cleaned
        return v


class IssueListResponse(BaseModel):
    """Paginated list of issue groups."""
    items: List[IssueGroupRead]
    total: int
    page: int
    per_page: int
    total_pages: int
