"""Project and Credential Request and Response Schemas."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ProjectCreate(BaseModel):
    """Schema for registering a new monitored project."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User-friendly name of the project or service",
        example="Payment Service",
    )


class ProjectResponse(BaseModel):
    """Response returned upon project creation containing credentials.
    
    IMPORTANT: The raw credentials are displayed ONLY ONCE during creation.
    The database stores only cryptographic SHA-256 hashes.
    """
    id: uuid.UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    name: str = Field(..., example="Payment Service")
    api_key: str = Field(
        ...,
        description="Project management key. Required for dashboard, incident management, and investigations.",
        example="tn_mgmt_abcdef0123456789...",
    )
    ingestion_key: Optional[str] = Field(
        default=None,
        description="Scoped telemetry ingestion key (tn_ingest_...). Use in SDKs and monitored services.",
        example="tn_ingest_1234567890abcdef...",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectRead(BaseModel):
    """Public project schema without secret key material."""
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectRotateResponse(BaseModel):
    """Response returned upon management API key rotation."""
    id: uuid.UUID
    name: str
    api_key: str = Field(
        ...,
        description="New raw management API key. Immediately replaces the previous management key.",
        example="tn_mgmt_fedcba9876543210...",
    )
    message: str = "Management API key rotated successfully. Store securely; previous key is now invalidated."
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionKeyCreate(BaseModel):
    """Schema for provisioning a new scoped ingestion credential."""
    name: str = Field(
        default="Application Ingestion Key",
        min_length=1,
        max_length=255,
        description="Descriptive identifier for this ingestion token",
        example="Production ECS Ingestion Key",
    )


class IngestionKeyRead(BaseModel):
    """Public ingestion key metadata (never exposes secret hash or raw token)."""
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IngestionKeyCreatedResponse(BaseModel):
    """One-time response returning newly generated raw ingestion credential."""
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    ingestion_key: str = Field(
        ...,
        description="Raw scoped ingestion key (tn_ingest_...). Displayed only once.",
        example="tn_ingest_a1b2c3d4e5f67890...",
    )
    key_prefix: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
