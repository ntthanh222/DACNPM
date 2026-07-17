"""Run database migrations against an explicitly isolated QA PostgreSQL database."""
from __future__ import annotations

import os
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


MIGRATIONS_DIR = ROOT / "backend" / "database" / "migrations"
MIGRATION_RE = re.compile(r"^(\d{3})_.*\.sql$")
REQUIRED_TABLES = {
    "users",
    "profiles",
    "chat_history",
    "notifications",
    "news_articles",
    "cve_records",
    "cve_lookups",
    "cve_watchlist",
    "assets",
    "incidents",
    "audit_logs",
    "security_alerts",
}


def run_psql(sql: str, *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    container = os.environ.get("QA_POSTGRES_CONTAINER", "cybersec-postgres-qa")
    db_name = os.environ.get("DB_NAME", "cybersec_qa")
    db_user = os.environ.get("DB_USER", "postgres")
    command = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-v",
        "ON_ERROR_STOP=1",
        "-X",
        "-q",
    ]
    return subprocess.run(
        command,
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=capture,
        check=True,
    )


def ordered_migrations() -> list[Path]:
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    seen: dict[str, Path] = {}
    for migration in migrations:
        match = MIGRATION_RE.match(migration.name)
        if not match:
            raise RuntimeError(f"Unexpected migration filename: {migration.name}")
        prefix = match.group(1)
        if prefix in seen:
            raise RuntimeError(
                f"Duplicate migration prefix {prefix}: {seen[prefix].name}, {migration.name}"
            )
        seen[prefix] = migration
    return migrations


def bootstrap_supabase_compat() -> None:
    run_psql(
        """
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE SCHEMA IF NOT EXISTS auth;
        CREATE OR REPLACE FUNCTION auth.role()
        RETURNS text
        LANGUAGE sql
        STABLE
        AS $$
            SELECT 'service_role'::text;
        $$;
        """
    )


def verify_required_tables() -> None:
    result = run_psql(
        """
        \\pset tuples_only on
        \\pset format unaligned
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """,
        capture=True,
    )
    present = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    missing = sorted(REQUIRED_TABLES - present)
    if missing:
        raise RuntimeError("Missing required tables after migration: " + ", ".join(missing))


def main() -> int:
    guard_or_exit()
    migrations = ordered_migrations()

    bootstrap_supabase_compat()
    for migration in migrations:
        sql = migration.read_text(encoding="utf-8")
        run_psql(sql)
        print(f"Applied migration: {migration.name}")
    verify_required_tables()

    print(f"QA migrations completed: {len(migrations)} files applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
