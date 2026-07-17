"""Live admin mutation boundary checks against an isolated QA backend."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 15


@dataclass
class Session:
    username: str
    token: str
    user_id: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class CheckFailure(AssertionError):
    pass


def request(method: str, path: str, *, session: Session | None = None, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if session:
        headers = {**headers, **session.headers}
    return requests.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=TIMEOUT, **kwargs)


def require_status(response: requests.Response, expected: set[int], label: str) -> None:
    if response.status_code not in expected:
        raise CheckFailure(f"{label}: expected {sorted(expected)}, got {response.status_code}: {response.text[:300]}")


def login(username: str, password_env: str) -> Session:
    password = os.environ.get(password_env)
    if not password:
        raise CheckFailure(f"Missing required password env var: {password_env}")
    response = request("POST", "/api/auth/login", json={"username": username, "password": password})
    require_status(response, {200}, f"login {username}")
    token = response.json()["access_token"]
    me = request("GET", "/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    require_status(me, {200}, f"/me {username}")
    return Session(username=username, token=token, user_id=me.json()["id"])


def expect_login_blocked(username: str, password_env: str, label: str) -> None:
    password = os.environ.get(password_env)
    if not password:
        raise CheckFailure(f"Missing required password env var: {password_env}")
    response = request("POST", "/api/auth/login", json={"username": username, "password": password})
    require_status(response, {401, 403}, label)


def update_status(admin: Session, user_id: str, active: bool, expected: set[int], label: str) -> requests.Response:
    response = request("PUT", f"/api/admin/users/{user_id}/status", session=admin, json={"is_active": active})
    require_status(response, expected, label)
    return response


def update_role(admin: Session, user_id: str, role: str, expected: set[int], label: str) -> requests.Response:
    response = request("PUT", f"/api/admin/users/{user_id}/role", session=admin, json={"role": role})
    require_status(response, expected, label)
    return response


def assert_user_role(session: Session, expected_role: str, label: str) -> None:
    me = request("GET", "/api/auth/me", session=session)
    require_status(me, {200}, label)
    role = me.json().get("role")
    if role != expected_role:
        raise CheckFailure(f"{label}: expected role {expected_role}, got {role}")


def query_admin_audit_log(target_user_id: str) -> list[dict[str, Any]]:
    container = os.environ.get("QA_POSTGRES_CONTAINER", "cybersec-postgres-qa")
    db_name = os.environ.get("DB_NAME", "cybersec_qa")
    db_user = os.environ.get("DB_USER", "postgres")
    sql = f"""
        SELECT action_type, target_id, action_details
        FROM public.admin_audit_log
        WHERE target_id = '{target_user_id.replace("'", "''")}'
          AND action_type IN ('user_role_change', 'user_activate', 'user_ban')
        ORDER BY timestamp DESC
        LIMIT 20;
    """
    result = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", db_user, "-d", db_name, "-X", "-q", "-t", "-A", "-F", "\t"],
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    records: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        action_type, target_id, action_details = line.split("\t", 2)
        records.append({"action_type": action_type, "target_id": target_id, "action_details": json.loads(action_details)})
    return records


def reset_qa_fixtures() -> None:
    script = os.path.join(ROOT, "testing", "scripts", "seed_qa_users.py")
    subprocess.run([sys.executable, script], check=True)


def main() -> int:
    guard_or_exit()
    reset_qa_fixtures()

    evidence: list[str] = []
    admin = login("qa_admin", "QA_ADMIN_PASSWORD")
    superadmin = login("qa_superadmin", "QA_SUPERADMIN_PASSWORD")
    user_a = login("qa_user_a", "QA_USER_A_PASSWORD")

    update_status(admin, user_a.user_id, False, {200}, "admin disables regular user")
    evidence.append("admin disables regular user -> 200")
    expect_login_blocked("qa_user_a", "QA_USER_A_PASSWORD", "disabled user cannot login")
    evidence.append("disabled user login -> blocked")

    stale_me = request("GET", "/api/auth/me", session=user_a)
    require_status(stale_me, {403}, "previous token rejected after disable")
    evidence.append("previous token rejected after disable -> 403")

    update_status(admin, user_a.user_id, True, {200}, "admin enables regular user")
    evidence.append("admin enables regular user -> 200")
    user_a = login("qa_user_a", "QA_USER_A_PASSWORD")

    update_role(admin, user_a.user_id, "security_analyst", {200}, "admin grants analyst role")
    evidence.append("admin grants analyst role -> 200")
    user_a = login("qa_user_a", "QA_USER_A_PASSWORD")
    assert_user_role(user_a, "security_analyst", "qa_user_a role after analyst promotion")
    require_status(request("GET", "/api/admin/system/cache", session=user_a), {200}, "analyst can read cache")
    require_status(request("GET", "/api/admin/users", session=user_a), {403}, "analyst cannot list users")
    evidence.append("analyst can read cache but cannot list users -> PASS")

    update_role(admin, user_a.user_id, "user", {200}, "admin restores user role")
    evidence.append("admin restores user role -> 200")
    user_a = login("qa_user_a", "QA_USER_A_PASSWORD")
    assert_user_role(user_a, "user", "qa_user_a role after restore")

    update_role(admin, user_a.user_id, "super_admin", {403}, "ordinary admin cannot grant super_admin")
    evidence.append("ordinary admin cannot grant super_admin -> 403")
    update_role(admin, admin.user_id, "user", {400}, "admin cannot change own role")
    evidence.append("admin cannot change own role -> 400")
    update_status(admin, superadmin.user_id, False, {403}, "ordinary admin cannot disable super admin")
    evidence.append("ordinary admin cannot disable super admin -> 403")

    update_role(superadmin, user_a.user_id, "admin", {200}, "super admin grants admin role")
    evidence.append("super admin grants admin role -> 200")
    update_role(superadmin, user_a.user_id, "user", {200}, "super admin restores user role")
    evidence.append("super admin restores user role -> 200")
    update_status(superadmin, superadmin.user_id, False, {400}, "last super admin cannot be deactivated")
    evidence.append("last super admin cannot be deactivated -> 400")
    update_role(superadmin, superadmin.user_id, "admin", {400}, "super admin cannot change own role")
    evidence.append("super admin cannot change own role -> 400")

    audit_records = query_admin_audit_log(user_a.user_id)
    action_types = {record["action_type"] for record in audit_records}
    expected_actions = {"user_role_change", "user_activate", "user_ban"}
    missing_actions = expected_actions - action_types
    if missing_actions:
        raise CheckFailure(f"admin audit log missing actions: {sorted(missing_actions)}")
    evidence.append("admin_audit_log contains role/status entries -> PASS")

    reset_qa_fixtures()

    print("Admin mutation matrix PASS")
    for line in evidence:
        print(f"- {line}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"Admin mutation matrix FAIL: {exc}")
        raise SystemExit(1) from exc
