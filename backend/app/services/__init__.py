"""Services Package."""

from app.services.project_service import create_project, get_project_by_api_key
from app.services.telemetry_service import ingest_event
from app.services.normalization_service import (
    normalize_stack_trace,
    normalize_error_message,
    extract_top_frames,
    extract_exception_type,
)
from app.services.fingerprint_service import compute_fingerprint, generate_issue_title
from app.services.issue_service import (
    upsert_issue_group,
    list_issues,
    get_issue_by_id,
    get_recent_events_for_issue,
    update_issue_status,
)

__all__ = [
    "create_project",
    "get_project_by_api_key",
    "ingest_event",
    "normalize_stack_trace",
    "normalize_error_message",
    "extract_top_frames",
    "extract_exception_type",
    "compute_fingerprint",
    "generate_issue_title",
    "upsert_issue_group",
    "list_issues",
    "get_issue_by_id",
    "get_recent_events_for_issue",
    "update_issue_status",
]
