"""Live isolated-QA admin login regression check.

Passwords are read from environment variables only and are never printed.
"""
from __future__ import annotations

import os
import sys
import json
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100").rstrip("/")
TIMEOUT = 15


class CheckFailure(AssertionError):
    pass


class Response:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self) -> dict:
        return json.loads(self.text)


def request(method: str, path: str, *, json_body: dict | None = None, headers: dict | None = None) -> Response:
    data = None
    request_headers = headers.copy() if headers else {}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return Response(response.status, response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return Response(exc.code, exc.read().decode("utf-8"))


def require_status(response: requests.Response, expected: set[int], label: str) -> None:
    if response.status_code not in expected:
        raise CheckFailure(f"{label}: expected {sorted(expected)}, got {response.status_code}: {response.text[:300]}")


def login(identifier: str, password_env: str) -> tuple[str, dict]:
    password = os.environ.get(password_env)
    if not password:
        raise CheckFailure(f"Missing required password env var: {password_env}")
    response = request("POST", "/api/auth/login", json_body={"username": identifier, "password": password})
    require_status(response, {200}, f"login {identifier}")
    token = response.json().get("access_token")
    if not token:
        raise CheckFailure(f"login {identifier}: access_token missing")
    me = request("GET", "/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    require_status(me, {200}, f"/me {identifier}")
    return token, me.json()


def main() -> int:
    guard_or_exit()

    admin_token, admin_profile = login("qa_admin", "QA_ADMIN_PASSWORD")
    if admin_profile.get("role") != "admin":
        raise CheckFailure(f"qa_admin role mismatch: {admin_profile.get('role')}")

    _, admin_email_profile = login("qa-admin@example.test", "QA_ADMIN_PASSWORD")
    if admin_email_profile.get("username") != "qa_admin":
        raise CheckFailure("admin email login did not resolve to qa_admin")

    wrong_password = request(
        "POST",
        "/api/auth/login",
        json_body={"username": "qa_admin", "password": "definitely-wrong-but-complex-1A"},
    )
    require_status(wrong_password, {401}, "wrong admin password")

    _, user_profile = login("qa_user_a", "QA_USER_A_PASSWORD")
    user_token = request(
        "POST",
        "/api/auth/login",
        json_body={"username": "qa_user_a", "password": os.environ["QA_USER_A_PASSWORD"]},
    ).json()["access_token"]

    admin_users = request("GET", "/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    require_status(admin_users, {200}, "admin lists users")

    user_admin_users = request("GET", "/api/admin/users", headers={"Authorization": f"Bearer {user_token}"})
    require_status(user_admin_users, {403}, "regular user blocked from admin users")

    disabled_login = request(
        "POST",
        "/api/auth/login",
        json_body={"username": "qa_disabled", "password": os.environ["QA_DISABLED_PASSWORD"]},
    )
    require_status(disabled_login, {401, 403}, "disabled user blocked from login")

    disable_user = request(
        "PUT",
        f"/api/admin/users/{user_profile['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json_body={"is_active": False},
    )
    require_status(disable_user, {200}, "admin disables regular user")

    stale_me = request("GET", "/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    require_status(stale_me, {403}, "stale user token rejected after disable")

    enable_user = request(
        "PUT",
        f"/api/admin/users/{user_profile['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json_body={"is_active": True},
    )
    require_status(enable_user, {200}, "admin restores regular user")

    print("QA admin login check PASS")
    print("- username login, email login, /me, admin authorization, wrong password, inactive user, stale token checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"QA admin login check FAIL: {exc}")
        raise SystemExit(1) from exc
