"""Serialization, Exception Formatting, and Metadata Sanitization."""

import json
import traceback
from typing import Any, Dict, Optional

SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "cookie",
    "access_token",
    "private_key",
)

MAX_MESSAGE_CHARS = 10000
MAX_STACK_CHARS = 100000


def format_exception_message(exc: BaseException) -> str:
    """Format human-readable exception summary."""
    exc_type = type(exc).__name__
    msg = str(exc).strip()
    if msg:
        full = f"{exc_type}: {msg}"
    else:
        full = exc_type
    return full[:MAX_MESSAGE_CHARS]


def format_stack_trace(exc: BaseException) -> str:
    """Extract and format complete exception stack trace."""
    frames = traceback.format_exception(type(exc), exc, exc.__traceback__)
    raw_stack = "".join(frames)
    return raw_stack[:MAX_STACK_CHARS]


def sanitize_metadata(
    metadata: Optional[Dict[str, Any]],
    max_bytes: int = 32768,
) -> Dict[str, Any]:
    """Scrub sensitive keys and ensure payload size is bounded."""
    if not metadata:
        return {}

    sanitized: Dict[str, Any] = {}

    for key, val in metadata.items():
        key_str = str(key)
        lower_key = key_str.lower()

        # Check for sensitive key substrings
        if any(substr in lower_key for substr in SENSITIVE_KEY_SUBSTRINGS):
            sanitized[key_str] = "[REDACTED]"
            continue

        # Ensure JSON-safe values
        sanitized[key_str] = _make_json_safe(val)

    # Size check
    try:
        encoded_len = len(json.dumps(sanitized))
        if encoded_len > max_bytes:
            return {
                "_warning": f"Metadata payload ({encoded_len} bytes) exceeded limit of {max_bytes} bytes and was truncated.",
                "truncated_keys": list(sanitized.keys())[:10],
            }
    except Exception:
        return {"_error": "Metadata could not be serialized to JSON"}

    return sanitized


def _make_json_safe(obj: Any, depth: int = 0) -> Any:
    """Recursively convert arbitrary objects to standard JSON-serializable types."""
    if depth > 5:
        return str(obj)

    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v, depth + 1) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [_make_json_safe(item, depth + 1) for item in obj]

    return str(obj)
