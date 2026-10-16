"""Production Middlewares for TraceNest.

Provides:
- Request Tracing and structured logging with X-Request-ID.
- OWASP Security Headers (CSP, HSTS, X-Frame-Options, etc.).
- In-memory sliding-window Rate Limiting for sensitive endpoints (/investigate, /telemetry).
- Maximum request payload size enforcement.
"""

import time
import uuid
import re
import logging
import hashlib
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette import status

from app.core.config import settings

logger = logging.getLogger("tracenest.middleware")

# Pattern to validate incoming X-Request-ID headers (alphanumeric, hyphens, underscores up to 64 chars)
SAFE_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request-id generation/propagation and structured access logging."""

    async def dispatch(self, request: Request, call_next) -> Response:
        raw_req_id = request.headers.get("x-request-id")
        if raw_req_id and SAFE_REQUEST_ID_REGEX.match(raw_req_id):
            req_id = raw_req_id
        else:
            req_id = uuid.uuid4().hex

        request.state.request_id = req_id
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled exception: method={request.method} path={request.url.path} "
                f"req_id={req_id} duration_ms={duration_ms}"
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        client_host = request.client.host if request.client else "unknown"
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} "
            f"[{duration_ms}ms] client={client_host} req_id={req_id}"
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to inject standard production security headers on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Standard OWASP security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        if settings.ENVIRONMENT.lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects request bodies exceeding maximum payload size limit."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length_int = int(content_length)
                if length_int > settings.MAX_REQUEST_SIZE_BYTES:
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={
                            "detail": (
                                f"Payload size ({length_int} bytes) exceeds maximum "
                                f"allowed limit ({settings.MAX_REQUEST_SIZE_BYTES} bytes)."
                            )
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


class RateLimiter:
    """Sliding-window in-memory rate limiter."""

    def __init__(self):
        self.history: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int, int]:
        """Check if request is allowed under the sliding window.

        Returns:
            (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        cutoff = now - window_seconds

        # Clean old timestamps
        valid_timestamps = [ts for ts in self.history[key] if ts > cutoff]
        self.history[key] = valid_timestamps

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            return False, 0, retry_after

        # Record this request
        valid_timestamps.append(now)
        remaining = max_requests - len(valid_timestamps)
        return True, remaining, 0

    @staticmethod
    def compute_effective_worker_limit(configured_limit: int, workers: int = 1) -> int:
        """Compute per-worker rate limit allocation to preserve aggregate cluster ceiling.

        In multi-worker deployments (e.g. Uvicorn with 2+ workers), each OS process
        maintains its own isolated memory heap. Partitioning the ceiling prevents
        cluster-wide aggregate request bursts from exceeding the target ceiling without
        introducing an external caching tier.
        """
        if workers <= 1:
            return configured_limit
        return max(1, configured_limit // workers)

    def reset(self):
        """Clear all rate limit history (useful for test suites)."""
        self.history.clear()


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce rate limits on high-traffic or resource-intensive endpoints."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path

        # Determine rate limit configuration for the endpoint
        limit = None
        rate_key_prefix = None

        if path.endswith("/investigate") and request.method == "POST":
            limit = settings.RATE_LIMIT_INVESTIGATE_PER_MINUTE
            rate_key_prefix = "investigate"
        elif path.endswith("/telemetry") and request.method == "POST":
            limit = settings.RATE_LIMIT_TELEMETRY_PER_MINUTE
            rate_key_prefix = "telemetry"
        elif path.endswith("/projects") and request.method == "POST":
            limit = settings.RATE_LIMIT_PROJECT_CREATE_PER_MINUTE
            rate_key_prefix = "project_create"

        if limit is not None:
            # Multi-worker partitioning: allocate per-process share of configured ceiling
            workers_count = max(1, settings.WORKERS)
            effective_limit = RateLimiter.compute_effective_worker_limit(limit, workers_count)

            # Use authenticated API key hash or client IP as rate limit identity
            api_key = request.headers.get("x-api-key") or request.headers.get("authorization") or ""

            # Extract client IP, prioritizing X-Forwarded-For if deployed behind reverse proxy
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else "unknown"

            # Stable, non-reversible keyed identity using SHA-256 (replaces process-salted hash())
            if api_key:
                clean_key = api_key.strip()
                if clean_key.lower().startswith("bearer "):
                    clean_key = clean_key[7:].strip()
                stable_key_hash = hashlib.sha256(clean_key.encode("utf-8")).hexdigest()[:16]
                identity = f"{rate_key_prefix}:{stable_key_hash}"
            else:
                identity = f"{rate_key_prefix}:{client_ip}"

            allowed, remaining, retry_after = rate_limiter.is_allowed(identity, effective_limit, window_seconds=60)

            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded for {path}. Try again in {retry_after} seconds.",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(effective_limit),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        return await call_next(request)
