#!/bin/sh
# TraceNest Production Container Entrypoint
# Dispatches custom commands (e.g. alembic upgrade head) or launches Uvicorn.
set -e

# If arguments are supplied, execute them directly
if [ "$#" -gt 0 ]; then
    echo "[TraceNest] Executing custom command: $@"
    exec "$@"
fi

# Default server networking and worker parameters
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"

echo "[TraceNest] Starting TraceNest API server on ${HOST}:${PORT} (workers: ${WORKERS})..."
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}" --workers "${WORKERS}" --proxy-headers --forwarded-allow-ips "*"
