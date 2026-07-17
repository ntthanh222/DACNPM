"""Live IDOR matrix checks against an isolated QA backend."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

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


def ensure_no_sensitive_leak(response: requests.Response, forbidden_values: list[str], label: str) -> None:
    body = response.text
    leaked = [value for value in forbidden_values if value and value in body]
    if leaked:
        raise CheckFailure(f"{label}: response leaked forbidden owner data")


def psql(sql: str) -> str:
    container = os.environ.get("QA_POSTGRES_CONTAINER", "cybersec-postgres-qa")
    db_name = os.environ.get("DB_NAME", "cybersec_qa")
    db_user = os.environ.get("DB_USER", "postgres")
    result = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", db_user, "-d", db_name, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-t", "-A"],
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def check_profile_idor(user_a: Session, user_b: Session) -> list[str]:
    evidence = []
    forbidden = [user_b.user_id, user_b.username]

    for method, path, kwargs, expected in [
        ("GET", f"/api/profiles/{user_b.user_id}", {}, {403}),
        ("PUT", f"/api/profiles/{user_b.user_id}", {"json": {"full_name": "IDOR overwrite"}}, {403}),
        ("DELETE", f"/api/profiles/{user_b.user_id}", {}, {403}),
    ]:
        response = request(method, path, session=user_a, **kwargs)
        require_status(response, expected, f"profile {method} foreign profile")
        ensure_no_sensitive_leak(response, forbidden, f"profile {method} foreign profile")
        evidence.append(f"profile {method} foreign profile -> {response.status_code}")
    return evidence


def check_chat_idor(user_a: Session, user_b: Session) -> list[str]:
    evidence = []

    create_b = request(
        "POST",
        "/api/chat/",
        session=user_b,
        json={
            "user_id": user_b.user_id,
            "user_message": "qa-user-b-private-message",
            "bot_response": "qa-user-b-private-response",
            "intent": "qa_idor",
        },
    )
    require_status(create_b, {201}, "user B create chat")
    message_id = create_b.json()["id"]

    create_foreign = request(
        "POST",
        "/api/chat/",
        session=user_a,
        json={
            "user_id": user_b.user_id,
            "user_message": "qa-user-a-forged-message",
            "bot_response": "qa-user-a-forged-response",
            "intent": "qa_idor",
        },
    )
    require_status(create_foreign, {403}, "user A create chat for user B")
    evidence.append(f"chat POST forged owner -> {create_foreign.status_code}")

    for method, path, expected in [
        ("GET", f"/api/chat/user/{user_b.user_id}", {403}),
        ("GET", f"/api/chat/{message_id}", {403}),
        ("DELETE", f"/api/chat/{message_id}", {403}),
        ("DELETE", f"/api/chat/user/{user_b.user_id}", {403}),
    ]:
        response = request(method, path, session=user_a)
        require_status(response, expected, f"chat {method} foreign resource")
        ensure_no_sensitive_leak(response, ["qa-user-b-private-message", "qa-user-b-private-response"], f"chat {method}")
        evidence.append(f"chat {method} foreign resource -> {response.status_code}")

    owner_read = request("GET", f"/api/chat/{message_id}", session=user_b)
    require_status(owner_read, {200}, "user B chat remains readable")
    if owner_read.json().get("user_message") != "qa-user-b-private-message":
        raise CheckFailure("chat integrity: user B message changed unexpectedly")
    evidence.append("chat owner integrity -> PASS")
    return evidence


def check_watchlist_idor(user_a: Session, user_b: Session) -> list[str]:
    evidence = []
    create_b = request(
        "POST",
        "/api/cve-watchlist/",
        session=user_b,
        json={"cve_id": "CVE-2099-10001", "notes": "qa-user-b-watchlist"},
    )
    if create_b.status_code == 400 and "already watched" in create_b.text:
        listing = request("GET", "/api/cve-watchlist/", session=user_b)
        require_status(listing, {200}, "user B list watchlist after duplicate")
        match = next((item for item in listing.json() if item.get("cve_id") == "CVE-2099-10001"), None)
        if not match:
            raise CheckFailure("watchlist duplicate reported but existing entry not found")
        watch_id = match["id"]
    else:
        require_status(create_b, {200}, "user B create watchlist")
        watch_id = create_b.json()["id"]

    delete_foreign = request("DELETE", f"/api/cve-watchlist/{watch_id}", session=user_a)
    require_status(delete_foreign, {404}, "user A delete user B watchlist")
    ensure_no_sensitive_leak(delete_foreign, ["qa-user-b-watchlist"], "watchlist delete foreign")
    evidence.append(f"watchlist DELETE foreign resource -> {delete_foreign.status_code}")

    listing_b = request("GET", "/api/cve-watchlist/", session=user_b)
    require_status(listing_b, {200}, "user B list watchlist")
    if not any(item.get("id") == watch_id for item in listing_b.json()):
        raise CheckFailure("watchlist integrity: foreign delete removed user B entry")
    evidence.append("watchlist owner integrity -> PASS")
    return evidence


def check_notification_idor(user_a: Session, user_b: Session) -> list[str]:
    evidence = []

    forged_create = request(
        "POST",
        "/api/notifications/",
        session=user_a,
        json={
            "user_id": user_b.user_id,
            "title": "qa-forged-notification",
            "message": "qa-user-a-should-not-create-for-b",
            "type": "qa",
        },
    )
    require_status(forged_create, {403}, "user A create notification for user B")
    evidence.append(f"notification POST forged owner -> {forged_create.status_code}")

    create_b = request(
        "POST",
        "/api/notifications/",
        session=user_b,
        json={
            "user_id": user_b.user_id,
            "title": "qa-user-b-notification",
            "message": "qa-user-b-private-notification",
            "type": "qa",
        },
    )
    require_status(create_b, {200}, "user B create notification")
    notification_id = create_b.json()["id"]

    mark_foreign = request("PUT", f"/api/notifications/{notification_id}/read", session=user_a)
    require_status(mark_foreign, {404}, "user A mark user B notification read")
    ensure_no_sensitive_leak(mark_foreign, ["qa-user-b-private-notification"], "notification mark foreign")
    evidence.append(f"notification PUT foreign resource -> {mark_foreign.status_code}")

    listing_b = request("GET", "/api/notifications/", session=user_b)
    require_status(listing_b, {200}, "user B list notifications")
    match = next((item for item in listing_b.json() if item.get("id") == notification_id), None)
    if not match:
        raise CheckFailure("notification integrity: user B notification missing")
    if match.get("is_read") is not False:
        raise CheckFailure("notification integrity: foreign mark-read changed user B notification")
    evidence.append("notification owner integrity -> PASS")
    return evidence


def check_global_admin_surface_boundaries(user_a: Session, analyst: Session, admin: Session) -> list[str]:
    evidence = []
    marker = f"qa-idor-global-{uuid4().hex[:10]}"
    asset_id = None
    incident_id = None

    try:
        create_asset = request(
            "POST",
            "/api/assets/",
            session=analyst,
            json={
                "name": f"{marker}-asset",
                "asset_type": "server",
                "hostname": f"{marker}.qa.local",
                "environment": "qa",
                "criticality": "high",
                "internet_exposure": True,
                "status": "active",
                "notes": "qa idor asset sentinel",
            },
        )
        require_status(create_asset, {200}, "analyst create asset sentinel")
        asset_id = create_asset.json()["id"]

        create_incident = request(
            "POST",
            "/api/incidents/",
            session=analyst,
            json={
                "title": f"{marker}-incident",
                "description": "qa idor incident sentinel",
                "severity": "high",
                "status": "open",
            },
        )
        require_status(create_incident, {200}, "analyst create incident sentinel")
        incident_id = create_incident.json()["id"]

        blocked_paths = [
            ("GET", "/api/assets/", "asset list"),
            ("GET", f"/api/assets/{asset_id}", "asset detail"),
            ("PUT", f"/api/assets/{asset_id}", "asset update"),
            ("GET", "/api/incidents/", "incident list"),
            ("GET", f"/api/incidents/{incident_id}", "incident detail"),
            ("PUT", f"/api/incidents/{incident_id}", "incident update"),
            ("GET", "/api/alerts/", "alert list"),
            ("GET", "/api/audit-logs/", "audit log list"),
            ("GET", "/api/reports/export/assets", "asset report export"),
            ("GET", "/api/reports/export/incidents", "incident report export"),
            ("GET", "/api/reports/export/audit-logs", "audit report export"),
        ]
        for method, path, label in blocked_paths:
            kwargs: dict[str, Any] = {}
            if method == "PUT" and "assets" in path:
                kwargs["json"] = {"notes": "qa user attempted overwrite"}
            if method == "PUT" and "incidents" in path:
                kwargs["json"] = {"notes": "qa user attempted overwrite"}
            response = request(method, path, session=user_a, **kwargs)
            require_status(response, {403}, f"user blocked from {label}")
            ensure_no_sensitive_leak(response, [marker], f"user blocked from {label}")
            evidence.append(f"{label} as regular user -> {response.status_code}")

        require_status(request("GET", "/api/reports/export/assets", session=analyst), {200}, "analyst export assets")
        require_status(request("GET", "/api/reports/export/incidents", session=analyst), {200}, "analyst export incidents")
        require_status(request("GET", "/api/reports/export/audit-logs", session=analyst), {403}, "analyst blocked from audit export")
        require_status(request("GET", "/api/reports/export/audit-logs", session=admin), {200}, "admin export audit logs")
        evidence.append("elevated report boundaries -> PASS")
    finally:
        if asset_id:
            request("DELETE", f"/api/assets/{asset_id}", session=admin)
        if incident_id:
            psql(f"DELETE FROM public.incidents WHERE id = {sql_literal(incident_id)};")

    return evidence


def main() -> int:
    guard_or_exit()

    checks: list[str] = []
    user_a = login("qa_user_a", "QA_USER_A_PASSWORD")
    user_b = login("qa_user_b", "QA_USER_B_PASSWORD")
    analyst = login("qa_analyst", "QA_ANALYST_PASSWORD")
    admin = login("qa_admin", "QA_ADMIN_PASSWORD")

    for check in (
        check_profile_idor,
        check_chat_idor,
        check_watchlist_idor,
        check_notification_idor,
    ):
        checks.extend(check(user_a, user_b))
    checks.extend(check_global_admin_surface_boundaries(user_a, analyst, admin))

    print("IDOR matrix PASS")
    for line in checks:
        print(f"- {line}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"IDOR matrix FAIL: {exc}")
        raise SystemExit(1) from exc
