"""Unit tests for Stack Trace Normalization and Deterministic Fingerprinting."""

import uuid
from app.services.normalization_service import (
    normalize_whitespace,
    normalize_volatile_tokens,
    normalize_stack_trace,
    normalize_error_message,
    extract_top_frames,
    extract_exception_type,
)
from app.services.fingerprint_service import compute_fingerprint, generate_issue_title


def test_normalize_whitespace_and_line_endings():
    """Test standardizing CRLF, CR, trailing whitespace, and excessive blank lines."""
    raw = "Line 1   \r\n\r\n\r\nLine 2 \rLine 3   "
    normalized = normalize_whitespace(raw)
    assert "\r" not in normalized
    assert normalized == "Line 1\n\nLine 2\nLine 3"


def test_normalize_volatile_memory_addresses_and_objects():
    """Test replacement of volatile memory addresses and object pointers."""
    raw = "Error in <app.services.PaymentGateway object at 0x7fa28c0019a0> at memory address 0x000002EE59C986B0"
    normalized = normalize_volatile_tokens(raw)
    assert "0x7fa28c0019a0" not in normalized
    assert "0x000002EE59C986B0" not in normalized
    assert "<app.services.PaymentGateway object at <address>>" in normalized
    assert "at memory address <address>" in normalized


def test_normalize_uuids_and_timestamps():
    """Test replacement of ephemeral UUIDs and timestamps."""
    raw = (
        "Failed processing transaction 550e8400-e29b-41d4-a716-446655440000 "
        "at 2026-10-14T21:56:23.123456Z on Thread-4"
    )
    normalized = normalize_volatile_tokens(raw)
    assert "550e8400-e29b-41d4-a716-446655440000" not in normalized
    assert "2026-10-14T21:56:23.123456Z" not in normalized
    assert "<uuid>" in normalized
    assert "<timestamp>" in normalized
    assert "<worker_id>" in normalized


def test_preserve_code_structure_and_line_numbers():
    """Verify that file names, function names, and frame line numbers are retained."""
    trace = (
        'Traceback (most recent call last):\n'
        '  File "/var/app/services/checkout.py", line 142, in process_payment\n'
        '    result = gateway.charge(amount)\n'
        '  File "/var/app/core/gateway.py", line 58, in charge\n'
        '    raise ConnectionError("Connection refused to 0x7f99a1b0")\n'
    )
    norm = normalize_stack_trace(trace)
    assert "process_payment" in norm
    assert "charge" in norm
    assert "checkout.py" in norm
    assert "gateway.py" in norm
    assert "line 142" in norm
    assert "line 58" in norm
    assert "0x7f99a1b0" not in norm
    assert "<address>" in norm


def test_extract_top_frames_bottom_up():
    """Test extracting top relevant frames closest to failure site."""
    trace = (
        'Traceback (most recent call last):\n'
        '  File "main.py", line 10, in root\n'
        '  File "router.py", line 25, in handle\n'
        '  File "service.py", line 99, in compute\n'
    )
    frames = extract_top_frames(trace, max_frames=2)
    assert len(frames) == 2
    # Bottom frame first
    assert frames[0] == ("service.py", "compute")
    assert frames[1] == ("router.py", "handle")


def test_equivalent_stack_traces_produce_same_fingerprint():
    """Two stack traces differing only by memory address and UUID produce identical fingerprints."""
    project_id = uuid.uuid4()
    trace1 = (
        'Traceback (most recent call last):\n'
        '  File "worker.py", line 45, in execute\n'
        '    obj = <Handler object at 0x7fa1203001a0>\n'
        'ValueError: Invalid session 11111111-2222-3333-4444-555555555555\n'
    )
    trace2 = (
        'Traceback (most recent call last):\r\n'
        '  File "worker.py", line 45, in execute  \r\n'
        '    obj = <Handler object at 0x000002EE59C986B0>\r\n'
        'ValueError: Invalid session 99999999-8888-7777-6666-555555555555\r\n'
    )

    fp1, title1 = compute_fingerprint(
        project_id,
        message="Invalid session 11111111-2222-3333-4444-555555555555",
        stack_trace=trace1,
    )
    fp2, title2 = compute_fingerprint(
        project_id,
        message="Invalid session 99999999-8888-7777-6666-555555555555",
        stack_trace=trace2,
    )

    assert fp1 == fp2
    assert title1 == title2
    assert title1 == "ValueError: Invalid session <uuid>"


def test_distinct_stack_traces_produce_different_fingerprints():
    """Meaningfully different stack traces produce different fingerprints."""
    project_id = uuid.uuid4()
    trace_a = (
        'Traceback (most recent call last):\n'
        '  File "auth.py", line 30, in verify_token\n'
        'PermissionError: Token expired\n'
    )
    trace_b = (
        'Traceback (most recent call last):\n'
        '  File "database.py", line 120, in connect\n'
        'TimeoutError: Database pool exhausted\n'
    )

    fp_a, _ = compute_fingerprint(project_id, message="Token expired", stack_trace=trace_a)
    fp_b, _ = compute_fingerprint(project_id, message="Database pool exhausted", stack_trace=trace_b)

    assert fp_a != fp_b


def test_different_projects_produce_different_fingerprints():
    """Identical errors from different projects must never share a fingerprint."""
    proj_a = uuid.uuid4()
    proj_b = uuid.uuid4()
    trace = (
        'Traceback (most recent call last):\n'
        '  File "api.py", line 10, in endpoint\n'
        'KeyError: "user_id"\n'
    )

    fp_a, _ = compute_fingerprint(proj_a, message="KeyError: user_id", stack_trace=trace)
    fp_b, _ = compute_fingerprint(proj_b, message="KeyError: user_id", stack_trace=trace)

    assert fp_a != fp_b


def test_missing_stack_trace_fallback_fingerprint():
    """Errors without stack traces group consistently by project, error_type, endpoint, and message."""
    project_id = uuid.uuid4()
    fp1, title1 = compute_fingerprint(
        project_id=project_id,
        message="HTTP 502 Bad Gateway from upstream",
        stack_trace=None,
        endpoint="/api/v1/orders",
        http_status=502,
    )
    fp2, title2 = compute_fingerprint(
        project_id=project_id,
        message="HTTP 502 Bad Gateway from upstream",
        stack_trace=None,
        endpoint="/api/v1/orders",
        http_status=502,
    )
    fp3, _ = compute_fingerprint(
        project_id=project_id,
        message="HTTP 504 Gateway Timeout",
        stack_trace=None,
        endpoint="/api/v1/orders",
        http_status=504,
    )

    assert fp1 == fp2
    assert fp1 != fp3
    assert title1 == "[/api/v1/orders] GenericError: HTTP 502 Bad Gateway from upstream"
