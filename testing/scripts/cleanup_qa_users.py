"""Delete only the QA users created by seed_qa_users.py from an isolated QA DB."""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


QA_USERNAMES = (
    "qa_user_a",
    "qa_user_b",
    "qa_analyst",
    "qa_admin",
    "qa_superadmin",
    "qa_disabled",
)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_psql(sql: str) -> str:
    container = os.environ.get("QA_POSTGRES_CONTAINER", "cybersec-postgres-qa")
    db_name = os.environ.get("DB_NAME", "cybersec_qa")
    db_user = os.environ.get("DB_USER", "postgres")
    result = subprocess.run(
        [
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
        ],
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    return result.stdout


def main() -> int:
    guard_or_exit()
    names = ", ".join(sql_literal(name) for name in QA_USERNAMES)
    output = run_psql(
        f"""
        \\pset tuples_only on
        \\pset format unaligned
        WITH deleted AS (
            DELETE FROM public.users
            WHERE username IN ({names})
            RETURNING 1
        )
        SELECT count(*) FROM deleted;
        """
    )
    deleted = output.strip().splitlines()[-1].strip() if output.strip() else "0"
    print(f"Deleted QA users: {deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
