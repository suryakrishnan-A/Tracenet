"""Security utilities for TraceNest: Scoped API key generation and hashing."""

import secrets
import hashlib
from typing import Optional

MANAGEMENT_KEY_PREFIX = "tn_mgmt_"
INGESTION_KEY_PREFIX = "tn_ingest_"
LEGACY_KEY_PREFIX = "tn_live_"

# Default alias for backward compatibility
API_KEY_PREFIX = MANAGEMENT_KEY_PREFIX


def generate_management_key() -> str:
    """Generate a high-entropy project management credential.

    Format: tn_mgmt_<24 hex bytes> (56 chars total).
    Allows project administration, issue updates, investigations, and credential management.
    """
    token = secrets.token_hex(24)
    return f"{MANAGEMENT_KEY_PREFIX}{token}"


def generate_ingestion_key() -> str:
    """Generate a high-entropy scoped ingestion credential.

    Format: tn_ingest_<24 hex bytes> (58 chars total).
    Restricted exclusively to telemetry event submission (POST /api/v1/telemetry).
    """
    token = secrets.token_hex(24)
    return f"{INGESTION_KEY_PREFIX}{token}"


def generate_api_key() -> str:
    """Backward compatibility alias for generating management credentials."""
    return generate_management_key()


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for secure database storage.

    Never store raw API keys in the database.
    """
    return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()


def get_key_prefix(api_key: str) -> str:
    """Extract standard prefix from key for auditing and logging."""
    if not api_key:
        return "unknown"
    for prefix in (MANAGEMENT_KEY_PREFIX, INGESTION_KEY_PREFIX, LEGACY_KEY_PREFIX):
        if api_key.startswith(prefix):
            return prefix
    return "custom_"


def mask_api_key(api_key: str) -> str:
    """Mask an API key for safe logging / display (e.g. tn_ingest_...9f2b)."""
    if not api_key:
        return "none"
    prefix = get_key_prefix(api_key)
    if len(api_key) <= 12:
        return "***"
    return f"{api_key[:len(prefix) + 4]}...{api_key[-4:]}"
