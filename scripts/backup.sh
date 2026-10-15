#!/usr/bin/env bash
# TraceNest Linux/Docker Production Backup Script
# Usage: ./scripts/backup.sh [database] [output_dir] [retention_days]

set -euo pipefail

DATABASE="${1:-tracenest}"
HOST="${PGHOST:-localhost}"
PORT="${PGPORT:-5432}"
USER="${PGUSER:-postgres}"
OUTPUT_DIR="${2:-./backups}"
RETENTION_DAYS="${3:-14}"

mkdir -p "${OUTPUT_DIR}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${OUTPUT_DIR}/tracenest_${DATABASE}_${TIMESTAMP}.sql.gz"

echo "[INFO] Starting compressed backup of database '${DATABASE}'..."
echo "[INFO] Output target: ${BACKUP_FILE}"

# Dump and compress without exposing credentials
pg_dump -h "${HOST}" -p "${PORT}" -U "${USER}" -F p "${DATABASE}" | gzip > "${BACKUP_FILE}"

if [[ -s "${BACKUP_FILE}" ]]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[SUCCESS] Backup completed successfully (${SIZE}): ${BACKUP_FILE}"
else
    echo "[ERROR] Backup failed or file is empty" >&2
    exit 1
fi

# Retention policy: remove backups older than RETENTION_DAYS
find "${OUTPUT_DIR}" -name "tracenest_${DATABASE}_*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete
echo "[INFO] Retention check completed (keeping ${RETENTION_DAYS} days)."
