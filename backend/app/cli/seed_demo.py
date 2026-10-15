"""Deterministic Demo Data Seeding Script for TraceNest.

Seeds a realistic production portfolio scenario:
- Creates an 'Acme Payments Platform' project.
- Ingests multiple realistic error incidents across critical, error, warning, and info severities.
- Includes rich stack traces, API metrics, and an insufficient-evidence scenario.
- Strictly disabled in production environment (ENVIRONMENT == 'production').

Usage:
    python -m app.cli.seed_demo
"""

import sys
import asyncio
from datetime import datetime, timezone, timedelta
import logging

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.schemas.project import ProjectCreate
from app.schemas.telemetry import TelemetryEventCreate
from app.services.project_service import create_project
from app.services.telemetry_service import ingest_event

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed_demo")


CRITICAL_STACK_TRACE = """Traceback (most recent call last):
  File "/app/services/payment_service.py", line 142, in process_charge
    conn = await db_pool.acquire(timeout=5.0)
  File "/usr/local/lib/python3.12/site-packages/asyncpg/pool.py", line 612, in acquire
    return await asyncio.wait_for(self._acquire(timeout), timeout)
  File "/usr/local/lib/python3.12/asyncio/tasks.py", line 475, in wait_for
    raise exceptions.TimeoutError()
asyncio.exceptions.TimeoutError: Connection pool exhausted (max 20 connections in use) during payment checkout at 0x7f8b9a12c0
"""

GATEWAY_STACK_TRACE = """Traceback (most recent call last):
  File "/app/gateways/stripe_client.py", line 89, in post_invoice
    response = await self.client.post("/v1/invoices", json=payload)
  File "/usr/local/lib/python3.12/site-packages/httpx/_client.py", line 1540, in post
    return await self.request("POST", url, json=json)
httpx.HTTPStatusError: Server returned 429 Too Many Requests: Rate limit exceeded for organization acme_corp
"""

WARNING_STACK_TRACE = """Warning (SlowQueryWarning): Query duration 2750ms exceeded threshold of 2000ms.
  File "/app/db/repositories/users.py", line 58, in search_users_by_email
    query = select(User).where(User.email.ilike(f"%{pattern}%"))
  Sequential scan executed on table 'users' with 850,000 rows. Missing index on lower(email).
"""


async def seed():
    """Execute demo seeding procedure."""
    # --------------------------------------------------------------------------
    # Production Safety Guard
    # --------------------------------------------------------------------------
    if settings.ENVIRONMENT.lower() == "production":
        logger.error("\n[ABORTED] Demo data seeding is strictly prohibited in PRODUCTION environment.")
        logger.error("Current ENVIRONMENT is set to 'production'. Exiting immediately.\n")
        sys.exit(1)

    print("=" * 70)
    print("TraceNest - Demo Data Seeding Engine")
    print(f"Target Database: {settings.POSTGRES_DB} @ {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
    print(f"Environment:     {settings.ENVIRONMENT}")
    print("=" * 70)

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # 1. Register Demo Project
        project_name = "Acme Payments Platform"
        project_in = ProjectCreate(name=project_name)
        project, raw_mgmt_key, raw_ingest_key = await create_project(session, project_in)
        print(f"\n[+] Created Demo Project: '{project.name}'")
        print(f"    Project ID:     {project.id}")
        print(f"    Management Key: {raw_mgmt_key}")
        print(f"    Ingestion Key:  {raw_ingest_key}")
        print("    (Use Management Key for Dashboard UI; Ingestion Key for client SDKs)")

        # 2. Ingest Scenario 1: Critical Database Connection Pool Exhaustion (High occurrence)
        print("\n[*] Ingesting Incident 1: Critical DB Connection Pool Exhaustion (8 events)...")
        for i in range(8):
            event_time = now - timedelta(minutes=45 - i * 5)
            await ingest_event(
                session,
                project,
                TelemetryEventCreate(
                    event_type="error",
                    severity="critical",
                    message="asyncio.exceptions.TimeoutError: Connection pool exhausted (max 20 connections in use) during payment checkout at 0x7f8b9a12c0",
                    stack_trace=CRITICAL_STACK_TRACE,
                    endpoint="/api/v1/payments/charge",
                    http_status=500,
                    duration_ms=5012,
                    metadata_json={
                        "user_id": f"usr_pay_{1000 + i}",
                        "active_connections": 20,
                        "max_pool_size": 20,
                        "currency": "USD",
                    },
                    timestamp=event_time,
                ),
            )

        # 3. Ingest Scenario 2: Payment Gateway Rate Limit (Medium occurrence)
        print("[*] Ingesting Incident 2: Gateway 429 Rate Limit (5 events)...")
        for i in range(5):
            event_time = now - timedelta(hours=2, minutes=30 - i * 4)
            await ingest_event(
                session,
                project,
                TelemetryEventCreate(
                    event_type="error",
                    severity="error",
                    message="httpx.HTTPStatusError: Server returned 429 Too Many Requests: Rate limit exceeded for organization acme_corp",
                    stack_trace=GATEWAY_STACK_TRACE,
                    endpoint="/api/v1/invoices/process",
                    http_status=502,
                    duration_ms=850,
                    metadata_json={
                        "retry_count": i + 1,
                        "external_service": "stripe",
                        "batch_id": "batch_9921",
                    },
                    timestamp=event_time,
                ),
            )

        # 4. Ingest Scenario 3: Performance Degradation Slow Query Warning (Low occurrence)
        print("[*] Ingesting Incident 3: Slow Query Warning (3 events)...")
        for i in range(3):
            event_time = now - timedelta(hours=6, minutes=10 * i)
            await ingest_event(
                session,
                project,
                TelemetryEventCreate(
                    event_type="warning",
                    severity="warning",
                    message="Warning (SlowQueryWarning): Query duration 2750ms exceeded threshold of 2000ms.",
                    stack_trace=WARNING_STACK_TRACE,
                    endpoint="/api/v1/users/search",
                    http_status=200,
                    duration_ms=2750 + (i * 120),
                    metadata_json={
                        "query_table": "users",
                        "scan_type": "Seq Scan",
                        "rows_scanned": 850000,
                    },
                    timestamp=event_time,
                ),
            )

        # 5. Ingest Scenario 4: Insufficient Evidence Info Event (1 event, no stack trace)
        print("[*] Ingesting Incident 4: Transient Network Flake (Insufficient Evidence scenario)...")
        await ingest_event(
            session,
            project,
            TelemetryEventCreate(
                event_type="info",
                severity="info",
                message="Transient DNS lookup timeout on internal consul resolver",
                stack_trace=None,
                endpoint="/internal/health/upstream",
                http_status=200,
                duration_ms=105,
                metadata_json={"resolver": "127.0.0.1:8600", "attempt": 1},
                timestamp=now - timedelta(hours=12),
            ),
        )

    print("\n" + "=" * 70)
    print("SUCCESS: Demo dataset seeded successfully!")
    print(f"Total Incidents Created: 4 distinct fingerprinted issue groups")
    print(f"Total Telemetry Events:  17 structured events ingested")
    print(f"\nTo inspect the demo data in the UI:")
    print(f"  1. Launch frontend: npm.cmd run dev (http://localhost:3000)")
    print(f"  2. Paste the Demo Project Management Key in the UI settings:")
    print(f"     Management Key: {raw_mgmt_key}")
    print(f"  3. Configure client SDKs with the Scoped Ingestion Key:")
    print(f"     Ingestion Key:  {raw_ingest_key}")
    print("=" * 70 + "\n")


def main():
    """CLI entrypoint."""
    asyncio.run(seed())


if __name__ == "__main__":
    main()
