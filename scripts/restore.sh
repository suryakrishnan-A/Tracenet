#!/usr/bin/env bash
# TraceNest Linux/Docker Production Restore Script
# Usage: ./scripts/restore.sh <backup_file> [target_database]

set -euo pipefail

BACKUP_FILE="${1:-}"
TARGET_DB="${2:-tracenest_restore_test}"
HOST="${PGHOST:-localhost}"
PORT="${PGPORT:-5432}"
USER="${PGUSER:-postgres}"

if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
    echo "[ERROR] Please specify a valid backup file path." >&2
    exit 1
fi

# Safeguard against accidental overwrite of production
if [[ "${TARGET_DB}" == "tracenest" && "${FORCE:-0}" != "1" ]]; then
    echo "[CAUTION] Overwriting production database requires FORCE=1 environment variable." >&2
    exit 1
fi

echo "[INFO] Restoring to database '${TARGET_DB}' from '${BACKUP_FILE}'..."

# Create database if it does not exist
psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'" | grep -q 1 || \
    psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";"

# Restore based on file extension
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    gunzip -c "${BACKUP_FILE}" | psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d "${TARGET_DB}"
else
    psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d "${TARGET_DB}" < "${BACKUP_FILE}"
fi

echo "[SUCCESS] Restore to '${TARGET_DB}' completed successfully."
