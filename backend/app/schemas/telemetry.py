"""Telemetry event request and response schemas."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

AllowedSeverity = Literal["info", "warning", "error", "critical"]


class TelemetryEventCreate(BaseModel):
    """Schema for ingesting a telemetry event or failure report."""
    event_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Event classification, e.g. error, metric, log, exception",
        example="error",
    )
    severity: AllowedSeverity = Field(
        default="error",
        description="Severity level: info, warning, error, critical",
        example="error",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Human-readable event message or error summary",
        example="Database connection timeout on pool checkout",
    )
    stack_trace: Optional[str] = Field(
        default=None,
        max_length=100000,
        description="Raw stack trace or error backtrace",
        example="Traceback (most recent call last):\n  File 'app.py', line 42, in process\nTimeoutError: connection timed out",
    )
    endpoint: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Associated HTTP endpoint or API path",
        example="/api/v1/checkout",
    )
    http_status: Optional[int] = Field(
        default=None,
        ge=100,
        le=599,
        description="HTTP status code if associated with an HTTP request",
        example=504,
    )
    duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Operation duration in milliseconds",
        example=1523.5,
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Structured arbitrary key-value context attributes",
        example={"user_id": "usr_981", "retry_count": 3, "environment": "production"},
    )
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when event occurred on client (UTC)",
    )

    @field_validator("event_type", mode="before")
    @classmethod
    def clean_event_type(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip().lower()
            if not cleaned:
                raise ValueError("event_type cannot be empty or whitespace")
            return cleaned
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def clean_severity(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip().lower()
            if cleaned not in ("info", "warning", "error", "critical"):
                raise ValueError(f"Invalid severity '{v}'. Allowed: info, warning, error, critical")
            return cleaned
        return v

    @model_validator(mode="before")
    @classmethod
    def handle_metadata_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "metadata" not in data and "metadata_json" in data:
                data["metadata"] = data["metadata_json"]
        return data

    model_config = ConfigDict(extra="ignore")


class TelemetryIngestResponse(BaseModel):
    """Acknowledgement returned after successful telemetry ingestion."""
    status: str = Field(default="received", example="received")
    event_id: uuid.UUID = Field(..., example="7c9e6679-7425-40de-944b-e07fc1f90ae7")
    project_id: uuid.UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    issue_id: Optional[uuid.UUID] = Field(default=None, example="8b1e4412-12aa-4db0-8f20-e3f5f16fb111")
    fingerprint: Optional[str] = Field(default=None, example="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)
