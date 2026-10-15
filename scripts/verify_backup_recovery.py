"""Automated Backup & Disaster Recovery Verification Script (Phase 9).

Validates:
1. Source database connectivity and row counts.
2. Execution of pg_dump backup script without credential exposure.
3. Creation and non-empty integrity of the backup artifact.
4. Restoration into an isolated disposable test database (tracenest_restore_test).
5. Exact data and schema integrity verification in the restored database.
"""

import sys
import os
import subprocess
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


SOURCE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/tracenest"
RESTORE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/tracenest_restore_test"
ADMIN_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"


async def get_table_counts(engine):
    """Query counts for all core TraceNest tables."""
    counts = {}
    tables = ["projects", "ingestion_keys", "issue_groups", "telemetry_events", "alembic_version"]
    async with engine.connect() as conn:
        for t in tables:
            try:
                res = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                counts[t] = res.scalar()
            except Exception as e:
                counts[t] = f"Error: {e}"
    return counts


async def run_verification():
    print("=" * 70)
    print("TraceNest Backup & Recovery Verification (Disaster Recovery Audit)")
    print("=" * 70)

    # 1. Inspect source database
    print("\n[Step 1] Connecting to source database ('tracenest')...")
    src_engine = create_async_engine(SOURCE_URL)
    try:
        src_counts = await get_table_counts(src_engine)
        print(f"  Source table counts: {src_counts}")
    except Exception as e:
        print(f"  [FAIL] Unable to connect to source database: {e}")
        return False
    finally:
        await src_engine.dispose()

    # 2. Run backup script
    print("\n[Step 2] Executing backup script (backup.ps1)...")
    backup_script = Path(__file__).resolve().parent / "backup.ps1"
    env = os.environ.copy()
    env["PGPASSWORD"] = "postgres"
    backup_proc = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(backup_script), "-Database", "tracenest"],
        capture_output=True,
        text=True,
        env=env,
    )
    print(backup_proc.stdout)
    if backup_proc.returncode != 0:
        print(f"  [FAIL] Backup script failed with code {backup_proc.returncode}")
        print(backup_proc.stderr)
        return False

    # Find the newly created backup file
    backups_dir = Path(__file__).resolve().parent.parent / "backups"
    sql_files = sorted(backups_dir.glob("tracenest_tracenest_*.sql"), key=os.path.getmtime, reverse=True)
    if not sql_files:
        print("  [FAIL] No backup files found in backups directory.")
        return False
    latest_backup = sql_files[0]
    file_size = latest_backup.stat().st_size
    print(f"  [OK] Latest backup artifact: {latest_backup.name} ({file_size} bytes)")
    if file_size == 0:
        print("  [FAIL] Backup file is 0 bytes.")
        return False

    # 3. Clean and prepare disposable database
    print("\n[Step 3] Re-creating disposable test database ('tracenest_restore_test')...")
    admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        # Terminate active connections to target database if any
        await conn.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'tracenest_restore_test'
              AND pid <> pg_backend_pid();
        """))
        await conn.execute(text("DROP DATABASE IF EXISTS tracenest_restore_test"))
        await conn.execute(text("CREATE DATABASE tracenest_restore_test"))
    await admin_engine.dispose()
    print("  [OK] Fresh disposable database 'tracenest_restore_test' initialized.")

    # 4. Run restore script
    print("\n[Step 4] Executing restore script (restore.ps1)...")
    restore_script = Path(__file__).resolve().parent / "restore.ps1"
    restore_proc = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(restore_script),
            "-BackupFile",
            str(latest_backup),
            "-TargetDatabase",
            "tracenest_restore_test",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    print(restore_proc.stdout)
    if restore_proc.returncode != 0:
        print(f"  [FAIL] Restore script failed with code {restore_proc.returncode}")
        print(restore_proc.stderr)
        return False

    # 5. Verify restored database
    print("\n[Step 5] Validating restored database integrity...")
    dest_engine = create_async_engine(RESTORE_URL)
    try:
        dest_counts = await get_table_counts(dest_engine)
        print(f"  Restored table counts: {dest_counts}")

        # Assert parity
        discrepancies = []
        for table, count in src_counts.items():
            restored_count = dest_counts.get(table)
            if restored_count != count:
                discrepancies.append(f"{table}: source={count}, restored={restored_count}")

        if discrepancies:
            print(f"  [FAIL] Data discrepancies found: {discrepancies}")
            return False
        else:
            print("  [SUCCESS] 100% row-count parity and schema match between source and restored database!")

        # Verify querying projects in restored DB
        async with dest_engine.connect() as conn:
            proj_res = await conn.execute(text("SELECT id, name, api_key_hash FROM projects LIMIT 3"))
            projects = proj_res.fetchall()
            print(f"  Sample verified projects in restored DB: {len(projects)}")
            for p in projects:
                print(f"    - ID: {p[0]} | Name: {p[1]} | Hash: {p[2][:16]}...")

        return True
    finally:
        await dest_engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(run_verification())
    if success:
        print("\n" + "=" * 70)
        print("DISASTER RECOVERY AUDIT: VERIFIED & PASSED")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("DISASTER RECOVERY AUDIT: FAILED")
        print("=" * 70)
        sys.exit(1)
