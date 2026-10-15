"""Unit Tests for TraceNest Python SDK."""

import os
import pytest
import httpx
from tracenest import (
    TraceNest,
    AsyncTraceNest,
    TraceNestConfigError,
    TraceNestDeliveryError,
    TraceNestRateLimitError,
)
from tracenest.serializer import (
    format_exception_message,
    format_stack_trace,
    sanitize_metadata,
)


def test_init_missing_key_raises_config_error(monkeypatch):
    """Verify initialization fails cleanly if no API key is provided."""
    monkeypatch.delenv("TRACENEST_API_KEY", raising=False)
    with pytest.raises(TraceNestConfigError) as exc_info:
        TraceNest()
    assert "API key is required" in str(exc_info.value)


def test_init_env_var_fallback(monkeypatch):
    """Verify initialization falls back to TRACENEST_API_KEY and TRACENEST_ENDPOINT."""
    monkeypatch.setenv("TRACENEST_API_KEY", "tn_live_env_test_key")
    monkeypatch.setenv("TRACENEST_ENDPOINT", "http://telemetry.internal:9000/api/v1/")

    client = TraceNest()
    assert client.api_key == "tn_live_env_test_key"
    assert client.endpoint == "http://telemetry.internal:9000"
    client.close()


def test_exception_serialization():
    """Verify exception type, message, and stack trace formatting."""
    try:
        raise ValueError("Payment amount must be greater than zero")
    except ValueError as err:
        msg = format_exception_message(err)
        trace = format_stack_trace(err)

    assert "ValueError: Payment amount must be greater than zero" in msg
    assert "Traceback (most recent call last):" in trace
    assert "test_exception_serialization" in trace


def test_metadata_sanitization_and_redaction():
    """Verify sensitive keys are scrubbed and oversized payloads are bounded."""
    dirty_metadata = {
        "user_id": 1042,
        "customer_password": "super_secret_plain_password",
        "api_key": "raw_secret_value",
        "oauth_token": "bearer_token_abc",
        "safe_context": "checkout_v2",
    }
    sanitized = sanitize_metadata(dirty_metadata)

    assert sanitized["user_id"] == 1042
    assert sanitized["safe_context"] == "checkout_v2"
    assert sanitized["customer_password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["oauth_token"] == "[REDACTED]"

    # Test size bounding
    huge_metadata = {f"key_{i}": "x" * 1000 for i in range(50)}
    bounded = sanitize_metadata(huge_metadata, max_bytes=2048)
    assert "_warning" in bounded


def test_capture_exception_mocked_201_success():
    """Verify successful delivery response mapping."""
    def mock_handler(request: httpx.Request):
        assert request.headers["x-api-key"] == "tn_live_unit_key"
        assert request.headers["x-request-id"] == "req_unit_123"
        return httpx.Response(
            201,
            json={
                "status": "received",
                "event_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "issue_id": "8b1e4412-12aa-4db0-8f20-e3f5f16fb111",
                "fingerprint": "abc123sha256fingerprint",
                "received_at": "2026-10-14T10:00:00Z",
            },
        )

    transport = httpx.MockTransport(mock_handler)
    mock_http_client = httpx.Client(transport=transport)

    with TraceNest(api_key="tn_live_unit_key", client=mock_http_client) as client:
        try:
            raise KeyError("missing_field_order_id")
        except KeyError as exc:
            result = client.capture_exception(
                exc,
                endpoint="/api/v1/orders",
                http_status=400,
                duration_ms=45.2,
                request_id="req_unit_123",
                metadata={"cart_size": 3},
            )

    assert result.success is True
    assert result.status_code == 201
    assert result.event_id == "7c9e6679-7425-40de-944b-e07fc1f90ae7"
    assert result.issue_id == "8b1e4412-12aa-4db0-8f20-e3f5f16fb111"
    assert result.fingerprint == "abc123sha256fingerprint"


def test_capture_exception_401_default_silent():
    """Verify 401 delivery failure does NOT raise an exception by default."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(401, text="Invalid API key")

    transport = httpx.MockTransport(mock_handler)
    client = TraceNest(api_key="tn_live_bad_key", client=httpx.Client(transport=transport))

    try:
        raise RuntimeError("App runtime issue")
    except RuntimeError as exc:
        res = client.capture_exception(exc)

    assert res.success is False
    assert res.status_code == 401
    assert "rejected telemetry with HTTP 401" in res.error
    client.close()


def test_capture_exception_401_raise_on_error():
    """Verify raise_on_delivery_error raises TraceNestDeliveryError."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(401, text="Invalid API key")

    transport = httpx.MockTransport(mock_handler)
    client = TraceNest(
        api_key="tn_live_bad_key",
        raise_on_delivery_error=True,
        client=httpx.Client(transport=transport),
    )

    with pytest.raises(TraceNestDeliveryError) as exc_info:
        client.capture_event("System error")
    assert exc_info.value.status_code == 401
    client.close()


def test_capture_exception_429_rate_limiting():
    """Verify 429 response maps retry_after correctly and raises TraceNestRateLimitError if configured."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(429, headers={"Retry-After": "4"}, text="Rate limit exceeded")

    transport = httpx.MockTransport(mock_handler)

    # 1. Non-raising client
    client = TraceNest(api_key="tn_live_key", client=httpx.Client(transport=transport))
    res = client.capture_event("Throttled event")
    assert res.success is False
    assert res.status_code == 429
    assert res.retry_after == 4
    client.close()

    # 2. Raising client
    client_raise = TraceNest(
        api_key="tn_live_key",
        raise_on_delivery_error=True,
        client=httpx.Client(transport=transport),
    )
    with pytest.raises(TraceNestRateLimitError) as exc_info:
        client_raise.capture_event("Throttled event")
    assert exc_info.value.retry_after == 4
    client_raise.close()


def test_network_connection_error_preserves_app_exception():
    """Verify host application exception is completely preserved even if network crashes."""
    captured_callback = {}

    def on_error(err, payload):
        captured_callback["error"] = err
        captured_callback["payload"] = payload

    def mock_handler(request: httpx.Request):
        raise httpx.ConnectError("Network unreachable: DNS resolution failed")

    transport = httpx.MockTransport(mock_handler)
    client = TraceNest(
        api_key="tn_live_key",
        on_delivery_error=on_error,
        client=httpx.Client(transport=transport),
    )

    original_exception_raised = False
    try:
        try:
            raise ArithmeticError("Original application business logic failure")
        except ArithmeticError as host_exc:
            delivery_res = client.capture_exception(host_exc)
            assert delivery_res.success is False
            assert "DNS resolution failed" in delivery_res.error
            raise host_exc
    except ArithmeticError as caught:
        original_exception_raised = True
        assert str(caught) == "Original application business logic failure"

    assert original_exception_raised is True
    assert "DNS resolution failed" in str(captured_callback["error"])
    client.close()


@pytest.mark.asyncio
async def test_async_tracenest_client():
    """Verify AsyncTraceNest works with async/await and mock async transport."""
    def mock_handler(request: httpx.Request):
        return httpx.Response(
            201,
            json={
                "status": "received",
                "event_id": "99999999-9999-9999-9999-999999999999",
                "project_id": "11111111-1111-1111-1111-111111111111",
                "received_at": "2026-10-14T10:00:00Z",
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async_http = httpx.AsyncClient(transport=transport)

    async with AsyncTraceNest(api_key="tn_live_key", client=async_http) as client:
        try:
            raise IndexError("List index out of range")
        except IndexError as exc:
            res = await client.capture_exception(exc, endpoint="/async/test")

    assert res.success is True
    assert res.event_id == "99999999-9999-9999-9999-999999999999"
