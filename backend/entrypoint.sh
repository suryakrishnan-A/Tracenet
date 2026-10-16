#!/bin/sh
# TraceNest Production Container Entrypoint
# Executes pending Alembic migrations before starting multi-worker Uvicorn.
set -e

echo "[TraceNest] Checking and applying database migrations (alembic upgrade head)..."
alembic upgrade head
echo "[TraceNest] Database migrations successfully applied."

echo "[TraceNest] Launching production server..."
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --workers "${WORKERS:-2}" --proxy-headers --forwarded-allow-ips "*"
