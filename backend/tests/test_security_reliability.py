"""Tests for TraceNest Phase 6: Production Security, Key Rotation, Middlewares & Reliability."""

import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.core.middleware import rate_limiter
from app.cli.seed_demo import seed


@pytest.mark.asyncio
async def test_project_api_key_rotation_lifecycle(async_client: AsyncClient):
    """Verify API key rotation immediately invalidates the old key and activates the new key."""
    # 1. Register project
    create_res = await async_client.post(
        "/api/v1/projects",
        json={"name": "Rotation Test Service"},
    )
    assert create_res.status_code == 201
    initial_data = create_res.json()
    project_id = initial_data["id"]
    old_api_key = initial_data["api_key"]

    # 2. Authenticate with initial key
    me_res = await async_client.get(
        "/api/v1/projects/me",
        headers={"X-API-Key": old_api_key},
    )
    assert me_res.status_code == 200
    assert me_res.json()["id"] == project_id
    assert me_res.json()["name"] == "Rotation Test Service"

    # 3. Rotate key using the current valid key
    rotate_res = await async_client.post(
        "/api/v1/projects/rotate-key",
        headers={"X-API-Key": old_api_key},
    )
    assert rotate_res.status_code == 200
    rotate_data = rotate_res.json()
    new_api_key = rotate_data["api_key"]
    assert new_api_key != old_api_key
    assert "rotated successfully" in rotate_data["message"]

    # 4. Old key MUST now be immediately rejected
    old_key_check = await async_client.get(
        "/api/v1/projects/me",
        headers={"X-API-Key": old_api_key},
    )
    assert old_key_check.status_code == 401

    # 5. New key MUST authenticate successfully
    new_key_check = await async_client.get(
        "/api/v1/projects/me",
        headers={"X-API-Key": new_api_key},
    )
    assert new_key_check.status_code == 200
    assert new_key_check.json()["id"] == project_id


@pytest.mark.asyncio
async def test_rotate_key_unauthorized(async_client: AsyncClient):
    """Verify unauthorized or missing credentials cannot rotate keys."""
    res_no_auth = await async_client.post("/api/v1/projects/rotate-key")
    assert res_no_auth.status_code == 401

    res_bad_auth = await async_client.post(
        "/api/v1/projects/rotate-key",
        headers={"X-API-Key": "tn_live_invalidkey1234567890"},
    )
    assert res_bad_auth.status_code == 401


@pytest.mark.asyncio
async def test_security_headers_injected(async_client: AsyncClient):
    """Verify all standard OWASP security headers are present on responses."""
    res = await async_client.get("/health")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in headers.get("Content-Security-Policy", "")
    assert "geolocation=()" in headers.get("Permissions-Policy", "")


@pytest.mark.asyncio
async def test_request_id_generation_and_propagation(async_client: AsyncClient):
    """Verify X-Request-ID is generated when absent and preserved when provided."""
    # Absent: should be generated
    res_gen = await async_client.get("/health")
    req_id = res_gen.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16

    # Provided: should be echoed back
    custom_id = "tracenest-custom-trace-id-42"
    res_echo = await async_client.get(
        "/health",
        headers={"X-Request-ID": custom_id},
    )
    assert res_echo.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_rate_limiter_unit_logic():
    """Verify the sliding window rate limiter state transition and retry-after calculation."""
    rate_limiter.reset()
    test_key = "unit_test_client_key"

    # Limit = 2
    ok1, rem1, retry1 = rate_limiter.is_allowed(test_key, max_requests=2, window_seconds=60)
    assert ok1 is True
    assert rem1 == 1
    assert retry1 == 0

    ok2, rem2, retry2 = rate_limiter.is_allowed(test_key, max_requests=2, window_seconds=60)
    assert ok2 is True
    assert rem2 == 0
    assert retry2 == 0

    # 3rd request should be blocked
    ok3, rem3, retry3 = rate_limiter.is_allowed(test_key, max_requests=2, window_seconds=60)
    assert ok3 is False
    assert rem3 == 0
    assert retry3 > 0

    rate_limiter.reset()


@pytest.mark.asyncio
async def test_rate_limiter_endpoint_throttling(async_client: AsyncClient):
    """Verify HTTP 429 response when endpoint threshold is exceeded."""
    rate_limiter.reset()
    original_limit = settings.RATE_LIMIT_TELEMETRY_PER_MINUTE
    settings.RATE_LIMIT_TELEMETRY_PER_MINUTE = 2
    settings.RATE_LIMIT_ENABLED = True

    try:
        # Create a project
        proj_res = await async_client.post("/api/v1/projects", json={"name": "Rate Limit Test"})
        api_key = proj_res.json()["api_key"]

        event_payload = {
            "event_type": "error",
            "severity": "error",
            "message": "Testing rate limit",
            "timestamp": "2026-10-14T10:00:00Z",
        }

        # 1st request -> 201
        res1 = await async_client.post(
            "/api/v1/telemetry",
            json=event_payload,
            headers={"X-API-Key": api_key},
        )
        assert res1.status_code == 201

        # 2nd request -> 201
        res2 = await async_client.post(
            "/api/v1/telemetry",
            json=event_payload,
            headers={"X-API-Key": api_key},
        )
        assert res2.status_code == 201

        # 3rd request -> 429 Too Many Requests
        res3 = await async_client.post(
            "/api/v1/telemetry",
            json=event_payload,
            headers={"X-API-Key": api_key},
        )
        assert res3.status_code == 429
        assert "Retry-After" in res3.headers
        assert res3.headers.get("X-RateLimit-Remaining") == "0"
        assert "Rate limit exceeded" in res3.json()["detail"]
    finally:
        settings.RATE_LIMIT_TELEMETRY_PER_MINUTE = original_limit
        rate_limiter.reset()


@pytest.mark.asyncio
async def test_payload_size_limit_rejection(async_client: AsyncClient):
    """Verify requests with Content-Length exceeding the limit are rejected with 413."""
    oversized_length = str(settings.MAX_REQUEST_SIZE_BYTES + 500)
    res = await async_client.post(
        "/api/v1/telemetry",
        json={"event_type": "error", "severity": "error", "message": "oversized"},
        headers={"Content-Length": oversized_length},
    )
    assert res.status_code == 413
    assert "exceeds maximum allowed limit" in res.json()["detail"]


@pytest.mark.asyncio
async def test_demo_seed_production_guard():
    """Verify demo data seeder refuses to execute in production environment."""
    original_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"

    try:
        with pytest.raises(SystemExit) as exc_info:
            await seed()
        assert exc_info.value.code == 1
    finally:
        settings.ENVIRONMENT = original_env


@pytest.mark.asyncio
async def test_rate_limiter_multi_worker_partitioning(async_client: AsyncClient):
    """Verify rate limit partitioning across multi-worker deployments and process isolation."""
    from app.core.middleware import RateLimiter

    # 1. Mathematical allocation verification
    assert RateLimiter.compute_effective_worker_limit(120, workers=1) == 120
    assert RateLimiter.compute_effective_worker_limit(120, workers=2) == 60
    assert RateLimiter.compute_effective_worker_limit(120, workers=4) == 30
    assert RateLimiter.compute_effective_worker_limit(15, workers=2) == 7

    # 2. Process memory isolation simulation: Two distinct worker instances
    worker_a = RateLimiter()
    worker_b = RateLimiter()
    client_key = "worker_isolation_test_client"

    # Worker A receives a request
    ok_a, rem_a, _ = worker_a.is_allowed(client_key, max_requests=1, window_seconds=60)
    assert ok_a is True
    assert rem_a == 0

    # Worker B's memory is isolated and unaffected by Worker A's traffic
    ok_b, rem_b, _ = worker_b.is_allowed(client_key, max_requests=1, window_seconds=60)
    assert ok_b is True
    assert rem_b == 0

    # 3. Middleware integration with WORKERS=2
    rate_limiter.reset()
    original_workers = settings.WORKERS
    original_limit = settings.RATE_LIMIT_TELEMETRY_PER_MINUTE
    settings.WORKERS = 2
    settings.RATE_LIMIT_TELEMETRY_PER_MINUTE = 2  # effective worker limit = 2 // 2 = 1
    settings.RATE_LIMIT_ENABLED = True

    try:
        proj_res = await async_client.post("/api/v1/projects", json={"name": "Worker Partition Test"})
        api_key = proj_res.json()["api_key"]
        payload = {
            "event_type": "error",
            "severity": "error",
            "message": "Testing worker partition",
            "timestamp": "2026-10-14T10:00:00Z",
        }

        # 1st request -> 201 (effective worker limit = 1)
        res1 = await async_client.post("/api/v1/telemetry", json=payload, headers={"X-API-Key": api_key})
        assert res1.status_code == 201

        # 2nd request to same worker -> 429
        res2 = await async_client.post("/api/v1/telemetry", json=payload, headers={"X-API-Key": api_key})
        assert res2.status_code == 429
        assert res2.headers.get("X-RateLimit-Limit") == "1"
    finally:
        settings.WORKERS = original_workers
        settings.RATE_LIMIT_TELEMETRY_PER_MINUTE = original_limit
        rate_limiter.reset()
