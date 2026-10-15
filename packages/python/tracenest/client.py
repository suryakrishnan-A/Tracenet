"""TraceNest Python Developer SDK Client."""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
import httpx

from tracenest.exceptions import (
    TraceNestConfigError,
    TraceNestDeliveryError,
    TraceNestRateLimitError,
)
from tracenest.models import DeliveryResult, EventPayload
from tracenest.serializer import (
    format_exception_message,
    format_stack_trace,
    sanitize_metadata,
)

logger = logging.getLogger("tracenest.sdk")


class TraceNest:
    """Synchronous TraceNest Telemetry Client for Python applications."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: float = 5.0,
        raise_on_delivery_error: bool = False,
        on_delivery_error: Optional[Callable[[Exception, Dict[str, Any]], None]] = None,
        max_metadata_bytes: int = 32768,
        client: Optional[httpx.Client] = None,
    ):
        raw_key = api_key or os.getenv("TRACENEST_API_KEY")
        if not raw_key or not raw_key.strip():
            raise TraceNestConfigError(
                "TraceNest API key is required. Supply via 'api_key' argument or "
                "set the 'TRACENEST_API_KEY' environment variable."
            )
        self.api_key = raw_key.strip()

        raw_endpoint = endpoint or os.getenv("TRACENEST_ENDPOINT", "http://localhost:8000")
        self.endpoint = raw_endpoint.rstrip("/")
        if self.endpoint.endswith("/api/v1"):
            self.endpoint = self.endpoint[:-7]

        self.timeout = timeout
        self.raise_on_delivery_error = raise_on_delivery_error
        self.on_delivery_error = on_delivery_error
        self.max_metadata_bytes = max_metadata_bytes

        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=self.timeout)

    def capture_exception(
        self,
        exception: BaseException,
        *,
        endpoint: Optional[str] = None,
        http_status: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        severity: str = "error",
    ) -> DeliveryResult:
        """Capture an exception and transmit telemetry to TraceNest.

        The original exception is never modified or suppressed.
        """
        message = format_exception_message(exception)
        stack_trace = format_stack_trace(exception)

        payload = EventPayload(
            event_type="exception",
            severity=severity,
            message=message,
            stack_trace=stack_trace,
            endpoint=endpoint,
            http_status=http_status,
            duration_ms=duration_ms,
            metadata=sanitize_metadata(metadata, max_bytes=self.max_metadata_bytes),
            timestamp=datetime.now(timezone.utc),
        )
        return self._send_payload(payload, request_id=request_id)

    def capture_event(
        self,
        message: str,
        *,
        event_type: str = "error",
        severity: str = "error",
        stack_trace: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_status: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> DeliveryResult:
        """Manually report an operational error or telemetry event."""
        payload = EventPayload(
            event_type=event_type,
            severity=severity,
            message=message.strip(),
            stack_trace=stack_trace,
            endpoint=endpoint,
            http_status=http_status,
            duration_ms=duration_ms,
            metadata=sanitize_metadata(metadata, max_bytes=self.max_metadata_bytes),
            timestamp=datetime.now(timezone.utc),
        )
        return self._send_payload(payload, request_id=request_id)

    def _send_payload(self, payload: EventPayload, request_id: Optional[str]) -> DeliveryResult:
        """Deliver payload to backend via synchronous HTTP POST."""
        url = f"{self.endpoint}/api/v1/telemetry"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "tracenest-python-sdk/0.1.0",
        }
        if request_id:
            headers["X-Request-ID"] = request_id

        payload_dict = payload.to_dict()

        try:
            res = self._client.post(url, json=payload_dict, headers=headers)
        except Exception as e:
            delivery_err = TraceNestDeliveryError(
                f"Failed to connect to TraceNest backend at '{self.endpoint}': {type(e).__name__}: {e}"
            )
            return self._handle_failure(delivery_err, payload_dict)

        if res.status_code == 201:
            try:
                data = res.json()
                return DeliveryResult(
                    success=True,
                    status_code=res.status_code,
                    event_id=str(data.get("event_id")),
                    project_id=str(data.get("project_id")),
                    issue_id=str(data.get("issue_id")) if data.get("issue_id") else None,
                    fingerprint=data.get("fingerprint"),
                )
            except Exception:
                return DeliveryResult(success=True, status_code=201)

        # Handle rate limiting (429)
        if res.status_code == 429:
            retry_header = res.headers.get("Retry-After")
            retry_seconds = int(retry_header) if retry_header and retry_header.isdigit() else 1
            rate_err = TraceNestRateLimitError(
                f"TraceNest rate limit exceeded. Retry after {retry_seconds}s.",
                status_code=429,
                response_body=res.text,
                retry_after=retry_seconds,
            )
            return self._handle_failure(rate_err, payload_dict, status_code=429, retry_after=retry_seconds)

        # Handle other HTTP error responses
        delivery_err = TraceNestDeliveryError(
            f"TraceNest rejected telemetry with HTTP {res.status_code}: {res.text}",
            status_code=res.status_code,
            response_body=res.text,
        )
        return self._handle_failure(delivery_err, payload_dict, status_code=res.status_code)

    def _handle_failure(
        self,
        err: Exception,
        payload: Dict[str, Any],
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
    ) -> DeliveryResult:
        """Route delivery failure according to error policy."""
        if self.on_delivery_error:
            try:
                self.on_delivery_error(err, payload)
            except Exception as callback_err:
                logger.warning(f"Error in on_delivery_error callback: {callback_err}")

        if self.raise_on_delivery_error:
            raise err

        logger.debug(f"TraceNest telemetry delivery unsuccessful: {err}")
        return DeliveryResult(
            success=False,
            status_code=status_code,
            error=str(err),
            retry_after=retry_after,
        )

    def close(self):
        """Close HTTP connection pool."""
        if self._owns_client and hasattr(self, "_client"):
            self._client.close()

    def __enter__(self) -> "TraceNest":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncTraceNest:
    """Asynchronous TraceNest Telemetry Client for async frameworks (FastAPI, Starlette, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: float = 5.0,
        raise_on_delivery_error: bool = False,
        on_delivery_error: Optional[Callable[[Exception, Dict[str, Any]], None]] = None,
        max_metadata_bytes: int = 32768,
        client: Optional[httpx.AsyncClient] = None,
    ):
        raw_key = api_key or os.getenv("TRACENEST_API_KEY")
        if not raw_key or not raw_key.strip():
            raise TraceNestConfigError(
                "TraceNest API key is required. Supply via 'api_key' argument or "
                "set the 'TRACENEST_API_KEY' environment variable."
            )
        self.api_key = raw_key.strip()

        raw_endpoint = endpoint or os.getenv("TRACENEST_ENDPOINT", "http://localhost:8000")
        self.endpoint = raw_endpoint.rstrip("/")
        if self.endpoint.endswith("/api/v1"):
            self.endpoint = self.endpoint[:-7]

        self.timeout = timeout
        self.raise_on_delivery_error = raise_on_delivery_error
        self.on_delivery_error = on_delivery_error
        self.max_metadata_bytes = max_metadata_bytes

        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=self.timeout)

    async def capture_exception(
        self,
        exception: BaseException,
        *,
        endpoint: Optional[str] = None,
        http_status: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        severity: str = "error",
    ) -> DeliveryResult:
        """Capture an exception asynchronously."""
        message = format_exception_message(exception)
        stack_trace = format_stack_trace(exception)

        payload = EventPayload(
            event_type="exception",
            severity=severity,
            message=message,
            stack_trace=stack_trace,
            endpoint=endpoint,
            http_status=http_status,
            duration_ms=duration_ms,
            metadata=sanitize_metadata(metadata, max_bytes=self.max_metadata_bytes),
            timestamp=datetime.now(timezone.utc),
        )
        return await self._send_payload(payload, request_id=request_id)

    async def capture_event(
        self,
        message: str,
        *,
        event_type: str = "error",
        severity: str = "error",
        stack_trace: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_status: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> DeliveryResult:
        """Manually report an operational error or telemetry event asynchronously."""
        payload = EventPayload(
            event_type=event_type,
            severity=severity,
            message=message.strip(),
            stack_trace=stack_trace,
            endpoint=endpoint,
            http_status=http_status,
            duration_ms=duration_ms,
            metadata=sanitize_metadata(metadata, max_bytes=self.max_metadata_bytes),
            timestamp=datetime.now(timezone.utc),
        )
        return await self._send_payload(payload, request_id=request_id)

    async def _send_payload(self, payload: EventPayload, request_id: Optional[str]) -> DeliveryResult:
        """Deliver payload to backend via async HTTP POST."""
        url = f"{self.endpoint}/api/v1/telemetry"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "tracenest-python-sdk/0.1.0",
        }
        if request_id:
            headers["X-Request-ID"] = request_id

        payload_dict = payload.to_dict()

        try:
            res = await self._client.post(url, json=payload_dict, headers=headers)
        except Exception as e:
            delivery_err = TraceNestDeliveryError(
                f"Failed to connect to TraceNest backend at '{self.endpoint}': {type(e).__name__}: {e}"
            )
            return self._handle_failure(delivery_err, payload_dict)

        if res.status_code == 201:
            try:
                data = res.json()
                return DeliveryResult(
                    success=True,
                    status_code=res.status_code,
                    event_id=str(data.get("event_id")),
                    project_id=str(data.get("project_id")),
                    issue_id=str(data.get("issue_id")) if data.get("issue_id") else None,
                    fingerprint=data.get("fingerprint"),
                )
            except Exception:
                return DeliveryResult(success=True, status_code=201)

        if res.status_code == 429:
            retry_header = res.headers.get("Retry-After")
            retry_seconds = int(retry_header) if retry_header and retry_header.isdigit() else 1
            rate_err = TraceNestRateLimitError(
                f"TraceNest rate limit exceeded. Retry after {retry_seconds}s.",
                status_code=429,
                response_body=res.text,
                retry_after=retry_seconds,
            )
            return self._handle_failure(rate_err, payload_dict, status_code=429, retry_after=retry_seconds)

        delivery_err = TraceNestDeliveryError(
            f"TraceNest rejected telemetry with HTTP {res.status_code}: {res.text}",
            status_code=res.status_code,
            response_body=res.text,
        )
        return self._handle_failure(delivery_err, payload_dict, status_code=res.status_code)

    def _handle_failure(
        self,
        err: Exception,
        payload: Dict[str, Any],
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
    ) -> DeliveryResult:
        if self.on_delivery_error:
            try:
                self.on_delivery_error(err, payload)
            except Exception as callback_err:
                logger.warning(f"Error in on_delivery_error callback: {callback_err}")

        if self.raise_on_delivery_error:
            raise err

        logger.debug(f"TraceNest telemetry delivery unsuccessful: {err}")
        return DeliveryResult(
            success=False,
            status_code=status_code,
            error=str(err),
            retry_after=retry_after,
        )

    async def aclose(self):
        """Close asynchronous HTTP client pool."""
        if self._owns_client and hasattr(self, "_client"):
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncTraceNest":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
