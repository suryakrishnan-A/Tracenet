"""Deterministic Error Fingerprinting Service.

Computes a deterministic SHA-256 fingerprint for grouping related telemetry errors
into an IssueGroup.

Fingerprinting Rules & Strategy:
=================================
1. Project Scoping:
   - The project_id is always incorporated into the hash seed to guarantee that
     identical errors across different monitored projects NEVER merge into the same issue.

2. With Stack Trace:
   - Seed components:
       a) project_id
       b) extracted or provided error_type (e.g., KeyError, TimeoutError, ZeroDivisionError)
       c) top relevant call frames from bottom-up: (file_basename, function_name)
       d) normalized exception message (ephemeral addresses, UUIDs, timestamps replaced)
   - Rationale: Code location (call site + function) and error category are the primary
     indicators of software defects. Variable memory pointers and runtime IDs are stripped.

3. Without Stack Trace (Fallback Strategy):
   - Seed components:
       a) project_id
       b) event_type (e.g., error, metric)
       c) extracted or detected error_type
       d) normalized message (ephemeral IDs replaced)
       e) endpoint / HTTP route (if available)
       f) http_status (if available)
   - Rationale: When stack traces are unavailable (e.g., log ingestion or network timeouts),
     the combination of endpoint, HTTP status, and normalized error message forms a stable cluster.

Limitations:
============
- Over-grouping: Highly generic error messages without stack traces (e.g. "Internal Server Error"
  with no endpoint or distinct phrasing) may group together.
- Under-grouping: When a function is renamed or moved across refactors, subsequent errors will
  produce a new fingerprint by design, representing the new code location.
"""

import hashlib
import json
import uuid
from typing import Optional, Dict, Any, Tuple
from app.services.normalization_service import (
    normalize_stack_trace,
    normalize_error_message,
    extract_top_frames,
    extract_exception_type,
)


def generate_issue_title(
    message: str,
    stack_trace: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> str:
    """Generate a clean, representative human-readable title for an IssueGroup."""
    exc_type = extract_exception_type(message, stack_trace)
    clean_msg = normalize_error_message(message).strip()

    # If message already starts with the exception type, keep it clean
    if clean_msg.startswith(f"{exc_type}:"):
        title = clean_msg
    else:
        title = f"{exc_type}: {clean_msg}" if clean_msg else exc_type

    if endpoint and not title.startswith(endpoint):
        title = f"[{endpoint}] {title}"

    # Truncate title if excessively long
    if len(title) > 500:
        title = title[:497] + "..."

    return title


def compute_fingerprint(
    project_id: uuid.UUID,
    message: str,
    stack_trace: Optional[str] = None,
    event_type: str = "error",
    endpoint: Optional[str] = None,
    http_status: Optional[int] = None,
) -> Tuple[str, str]:
    """Compute deterministic SHA-256 fingerprint and canonical title.
    
    Returns:
        Tuple[str, str]: (fingerprint_hash_hex, issue_title)
    """
    normalized_msg = normalize_error_message(message)
    exc_type = extract_exception_type(message, stack_trace)
    issue_title = generate_issue_title(message, stack_trace, endpoint)

    components: Dict[str, Any] = {
        "project_id": str(project_id),
        "error_type": exc_type,
    }

    if stack_trace and stack_trace.strip():
        # Stack trace present: normalize trace and extract call frames
        norm_trace = normalize_stack_trace(stack_trace)
        frames = extract_top_frames(norm_trace, max_frames=5)
        components["strategy"] = "stack_trace"
        components["top_frames"] = frames
        components["normalized_message"] = normalized_msg
        if endpoint:
            components["endpoint"] = endpoint
    else:
        # Fallback strategy: no stack trace available
        components["strategy"] = "message_fallback"
        components["event_type"] = event_type
        components["normalized_message"] = normalized_msg
        if endpoint:
            components["endpoint"] = endpoint
        if http_status:
            components["http_status"] = http_status

    # Canonical deterministic JSON serialization
    serialized = json.dumps(components, sort_keys=True, separators=(",", ":"))
    fingerprint_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    return fingerprint_hash, issue_title
