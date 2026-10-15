"""Stack Trace and Error Message Normalization Service.

Normalizes stack traces, error messages, and failure signatures by stripping volatile
ephemeral values (memory addresses, UUIDs, timestamps, dynamic IDs) while strictly preserving
structural code elements (function names, file references, exception types, and stack hierarchy).
"""

import re
from typing import List, Optional, Tuple

# Regex patterns for volatile tokens
RE_LINE_ENDINGS = re.compile(r"\r\n|\r")
RE_HEX_ADDRESS = re.compile(r"\b0x[0-9a-fA-F]{4,16}\b")
RE_OBJECT_AT_ADDR = re.compile(r"<([\w\.]+) object at 0x[0-9a-fA-F]+>")
RE_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
RE_ISO_TIMESTAMP = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
RE_EPOCH_TIMESTAMP = re.compile(
    r"\b(?P<prefix>timestamp|time|ts|date|epoch)(?P<sep>[=:\s]+)\d{10,13}\b",
    re.IGNORECASE,
)
RE_REQUEST_ID = re.compile(
    r"\b(?:req|request|corr|correlation|trace|span)[-_]?[0-9a-fA-F]{8,32}\b",
    re.IGNORECASE,
)
RE_THREAD_PROCESS_ID = re.compile(
    r"\b(?:thread|process|worker|task)[-_ ]#?\d+\b",
    re.IGNORECASE,
)
RE_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")

# Python and JS stack frame patterns
RE_PY_FRAME = re.compile(
    r'File\s+"(?P<file>[^"]+)",\s+line\s+(?P<line>\d+),\s+in\s+(?P<func>[a-zA-Z0-9_<>]+)'
)
RE_JS_FRAME = re.compile(
    r"at\s+(?:(?P<func>[a-zA-Z0-9_$.<>]+)\s+\()?(?P<file>[^:()]+):(?P<line>\d+):(?P<col>\d+)\)?"
)
RE_EXCEPTION_LINE = re.compile(
    r"^(?P<exc_type>[a-zA-Z0-9_.]*(?:Error|Exception|Warning|Fault|Failure|Crash)):\s*(?P<exc_msg>.*)$",
    re.MULTILINE,
)


def normalize_whitespace(text: str) -> str:
    """Normalize line endings and redundant whitespace."""
    if not text:
        return ""
    # Standardize to LF
    text = RE_LINE_ENDINGS.sub("\n", text)
    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in text.split("\n")]
    joined = "\n".join(lines).strip()
    # Collapse multiple blank lines
    return RE_MULTIPLE_BLANK_LINES.sub("\n\n", joined)


def normalize_volatile_tokens(text: str) -> str:
    """Replace volatile memory addresses, UUIDs, timestamps, and request IDs with stable placeholders."""
    if not text:
        return ""

    # Replace object representations <Class object at 0x7f8...> -> <Class object at <address>>
    text = RE_OBJECT_AT_ADDR.sub(r"<\1 object at <address>>", text)
    # Replace standalone hex memory addresses
    text = RE_HEX_ADDRESS.sub("<address>", text)
    # Replace UUIDs
    text = RE_UUID.sub("<uuid>", text)
    # Replace ISO timestamps
    text = RE_ISO_TIMESTAMP.sub("<timestamp>", text)
    # Replace epoch timestamp values
    text = RE_EPOCH_TIMESTAMP.sub(r"\g<prefix>\g<sep><timestamp>", text)
    # Replace ephemeral request / correlation IDs
    text = RE_REQUEST_ID.sub("<req_id>", text)
    # Standardize thread / worker identifiers
    text = RE_THREAD_PROCESS_ID.sub("<worker_id>", text)

    return text


def normalize_stack_trace(stack_trace: Optional[str]) -> str:
    """Produce a canonical normalized stack trace.
    
    Preserves:
      - File paths, modules, and call hierarchy
      - Function and method names
      - Line numbers in frame definitions
      - Exception classes and core error phrasing
    Replaces:
      - Memory addresses -> <address>
      - Ephemeral IDs / UUIDs -> <uuid>
      - Ephemeral timestamps -> <timestamp>
    """
    if not stack_trace or not stack_trace.strip():
        return ""

    cleaned = normalize_whitespace(stack_trace)
    return normalize_volatile_tokens(cleaned)


def normalize_error_message(message: str) -> str:
    """Normalize an error message by stripping ephemeral runtime values."""
    if not message:
        return ""
    cleaned = normalize_whitespace(message)
    return normalize_volatile_tokens(cleaned)


def extract_top_frames(stack_trace: Optional[str], max_frames: int = 5) -> List[Tuple[str, str]]:
    """Extract up to max_frames relevant (file, func) frames from the stack trace.
    
    Reads from the bottom of the stack trace upwards (closest to the failure site).
    """
    if not stack_trace:
        return []

    frames: List[Tuple[str, str]] = []

    # Check for Python stack frames
    py_matches = list(RE_PY_FRAME.finditer(stack_trace))
    if py_matches:
        for m in reversed(py_matches):
            file_path = m.group("file").replace("\\", "/").split("/")[-1]
            func_name = m.group("func")
            frames.append((file_path, func_name))
            if len(frames) >= max_frames:
                break
        return frames

    # Check for JavaScript / TypeScript stack frames
    js_matches = list(RE_JS_FRAME.finditer(stack_trace))
    if js_matches:
        for m in reversed(js_matches):
            file_path = m.group("file").replace("\\", "/").split("/")[-1]
            func_name = m.group("func") or "<anonymous>"
            frames.append((file_path, func_name))
            if len(frames) >= max_frames:
                break
        return frames

    return frames


def extract_exception_type(message: str, stack_trace: Optional[str]) -> str:
    """Heuristically extract the exception type (e.g., TimeoutError, ValueError).
    
    Checks the stack trace first, then falls back to message inspection.
    """
    if stack_trace:
        exc_matches = list(RE_EXCEPTION_LINE.finditer(stack_trace))
        if exc_matches:
            return exc_matches[-1].group("exc_type").split(".")[-1]

    # Check message prefix (e.g., "ConnectionError: failed to connect")
    msg_match = RE_EXCEPTION_LINE.match(message)
    if msg_match:
        return msg_match.group("exc_type").split(".")[-1]

    return "GenericError"
