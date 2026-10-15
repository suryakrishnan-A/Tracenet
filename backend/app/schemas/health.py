"""Health check schemas."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class BasicHealthResponse(BaseModel):
    """Schema for root /health check."""
    status: str = Field(default="ok", example="ok")
    service: str = Field(default="tracenest-backend", example="tracenest-backend")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApiHealthResponse(BaseModel):
    """Schema for versioned /api/v1/health check."""
    status: str = Field(default="ok", example="ok")
    app_name: str = Field(..., example="TraceNest API")
    version: str = Field(..., example="0.1.0")
    environment: str = Field(..., example="development")
    api_version: str = Field(default="v1", example="v1")
    database_connected: bool = Field(default=False, example=False)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
