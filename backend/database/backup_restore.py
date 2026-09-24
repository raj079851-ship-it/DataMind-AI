# -*- coding: utf-8 -*-
"""
Database Backup and Restoration Utility for PostgreSQL 18.
Provides automated schema and data dumps using `pg_dump` and restores using `psql`.

Usage:
    python backend/database/backup_restore.py --backup
    python backend/database/backup_restore.py --list
    python backend/database/backup_restore.py --restore backups/analytics_platform_backup_20260924_174500.sql
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

# Load environment configuration
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.database.connection import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backups"))
os.makedirs(BACKUP_DIR, exist_ok=True)

# Locate pg_dump / psql binaries
POSSIBLE_BIN_DIRS = [
    r"C:\Program Files\PostgreSQL\18\bin",
    r"C:\Program Files\PostgreSQL\17\bin",
    r"C:\Program Files\PostgreSQL\16\bin",
    r"C:\Program Files\PostgreSQL\15\bin"
]

PG_DUMP_PATH = "pg_dump"
PSQL_PATH = "psql"

for b_dir in POSSIBLE_BIN_DIRS:
    dump_candidate = os.path.join(b_dir, "pg_dump.exe")
    psql_candidate = os.path.join(b_dir, "psql.exe")
    if os.path.exists(dump_candidate):
        PG_DUMP_PATH = dump_candidate
        PSQL_PATH = psql_candidate
        break


def perform_backup() -> str:
    """Executes pg_dump and saves a complete SQL snapshot in the backups directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{DB_NAME.replace(' ', '_')}_backup_{timestamp}.sql"
    target_file = os.path.join(BACKUP_DIR, backup_filename)

    print(f"[+] Starting PostgreSQL backup for database '{DB_NAME}'...")
    print(f"    Target: {target_file}")

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        PG_DUMP_PATH,
        "-h", DB_HOST,
        "-p", str(DB_PORT),
        "-U", DB_USER,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "-f", target_file,
        DB_NAME
    ]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        size_kb = round(os.path.getsize(target_file) / 1024, 2)
        print(f"[SUCCESS] Backup successfully created ({size_kb} KB): {target_file}")
        return target_file
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Backup failed: {e.stderr}")
        raise


def perform_restore(backup_file: str) -> bool:
    """Restores database state from a specified SQL snapshot file."""
    if not os.path.exists(backup_file):
        print(f"[ERROR] Specified backup file does not exist: {backup_file}")
        return False

    print(f"[!] Restoring database '{DB_NAME}' from: {backup_file}...")
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        PSQL_PATH,
        "-h", DB_HOST,
        "-p", str(DB_PORT),
        "-U", DB_USER,
        "-d", DB_NAME,
        "-f", backup_file
    ]

    try:
        subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print(f"[SUCCESS] Database '{DB_NAME}' successfully restored from {backup_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Restore failed: {e.stderr}")
        return False


def list_backups():
    """Lists all available snapshots in the backup repository."""
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")]
    if not files:
        print("[i] No backup files located in directory.")
        return

    print("=" * 70)
    print(f" Available PostgreSQL Backups ({len(files)} total):")
    print("=" * 70)
    for fname in sorted(files, reverse=True):
        full_path = os.path.join(BACKUP_DIR, fname)
        size_kb = round(os.path.getsize(full_path) / 1024, 2)
        mtime = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M:%S")
        print(f" * {fname}  [{size_kb} KB]  (Created: {mtime})")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="DataMind AI - PostgreSQL Backup and Restore Utility")
    parser.add_argument("--backup", action="store_true", help="Execute full database backup")
    parser.add_argument("--restore", type=str, help="Path to SQL snapshot file to restore")
    parser.add_argument("--list", action="store_true", help="List all generated backup files")

    args = parser.parse_args()

    if args.backup:
        perform_backup()
    elif args.restore:
        perform_restore(args.restore)
    elif args.list:
        list_backups()
    else:
        # Default behavior: run backup and show list
        perform_backup()
        list_backups()


if __name__ == "__main__":
    main()
