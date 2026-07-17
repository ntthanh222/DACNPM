"""Guarded, idempotent QA fixture seeder for the application's public.users table."""
from __future__ import annotations

import os
import sys
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.security import hash_password  # noqa: E402
from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


@dataclass(frozen=True)
class Fixture:
    key: str
    username: str
    email: str
    role: str
    active: bool = True


FIXTURES = (
    Fixture("USER_A", "qa_user_a", "qa_user_a@cybersec.local", "user"),
    Fixture("USER_B", "qa_user_b", "qa_user_b@cybersec.local", "user"),
    Fixture("ANALYST", "qa_analyst", "qa_analyst@cybersec.local", "security_analyst"),
    Fixture("ADMIN", "qa_admin", "qa-admin@example.test", "admin"),
    Fixture("SUPERADMIN", "qa_superadmin", "qa_superadmin@cybersec.local", "super_admin"),
    Fixture("DISABLED", "qa_disabled", "qa_disabled@cybersec.local", "user", False),
)


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


def required_password_envs() -> list[str]:
    return [f"QA_{fixture.key}_PASSWORD" for fixture in FIXTURES]


def main() -> int:
    guard_or_exit()

    missing = [name for name in required_password_envs() if not os.getenv(name)]
    if missing:
        print("Refusing to seed: missing password environment variables: " + ", ".join(missing))
        return 2

    statements = []
    for fixture in FIXTURES:
        password_hash = hash_password(os.environ[f"QA_{fixture.key}_PASSWORD"])
        statements.append(
            f"""
                    INSERT INTO public.users (username, email, full_name, role, is_active, password_hash)
                    VALUES (
                        {sql_literal(fixture.username)},
                        {sql_literal(fixture.email)},
                        {sql_literal(fixture.username)},
                        {sql_literal(fixture.role)},
                        {'TRUE' if fixture.active else 'FALSE'},
                        {sql_literal(password_hash)}
                    )
                    ON CONFLICT (username) DO UPDATE
                    SET email = EXCLUDED.email,
                        full_name = EXCLUDED.full_name,
                        role = EXCLUDED.role,
                        is_active = EXCLUDED.is_active,
                        password_hash = EXCLUDED.password_hash,
                        updated_at = NOW();
            """
        )

    run_psql("\n".join(statements))
    print(f"QA fixture synchronization completed: {len(FIXTURES)} users processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
