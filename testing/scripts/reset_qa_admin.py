"""Guarded, idempotent reset for the isolated QA admin account.

The password is read only from QA_ADMIN_PASSWORD and is never printed.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.security import hash_password  # noqa: E402
from testing.scripts.qa_guard import guard_or_exit  # noqa: E402
from testing.scripts.seed_qa_users import sql_literal  # noqa: E402


QA_ADMIN_USERNAME = "qa_admin"
QA_ADMIN_EMAIL = "qa-admin@example.test"


def run_psql(sql: str) -> None:
    container = os.environ.get("QA_POSTGRES_CONTAINER", "cybersec-postgres-qa")
    db_name = os.environ.get("DB_NAME", "cybersec_qa")
    db_user = os.environ.get("DB_USER", "postgres")
    subprocess.run(
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
        check=True,
    )


def main() -> int:
    guard_or_exit()

    password = os.getenv("QA_ADMIN_PASSWORD")
    if not password:
        print("Refusing to reset QA admin: QA_ADMIN_PASSWORD is required.")
        return 2

    password_hash = hash_password(password)
    sql = f"""
        INSERT INTO public.users (username, email, full_name, role, is_active, password_hash)
        VALUES (
            {sql_literal(QA_ADMIN_USERNAME)},
            {sql_literal(QA_ADMIN_EMAIL)},
            {sql_literal(QA_ADMIN_USERNAME)},
            'admin',
            TRUE,
            {sql_literal(password_hash)}
        )
        ON CONFLICT (username) DO UPDATE
        SET email = EXCLUDED.email,
            full_name = EXCLUDED.full_name,
            role = 'admin',
            is_active = TRUE,
            password_hash = EXCLUDED.password_hash,
            updated_at = NOW();
    """
    run_psql(sql)
    print(f"QA admin reset completed for username {QA_ADMIN_USERNAME} and email {QA_ADMIN_EMAIL}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
