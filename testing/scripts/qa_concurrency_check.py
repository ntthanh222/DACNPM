"""Guarded concurrent authenticated CRUD checks against isolated QA."""
from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 20
REPORT = ROOT / "testing" / "reports" / "cybersec-assistant" / "QA_CONCURRENCY_REPORT.md"


@dataclass(frozen=True)
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


def create_chat(session: Session, marker: str, index: int) -> dict:
    payload = {
        "user_id": session.user_id,
        "user_message": f"{marker}:{session.username}:message:{index}",
        "bot_response": f"{marker}:{session.username}:response:{index}",
        "intent": "qa_concurrency",
    }
    start = time.perf_counter()
    try:
        response = request("POST", "/api/chat/", session=session, json=payload)
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        return {
            "username": session.username,
            "index": index,
            "status": response.status_code,
            "latency_ms": round((time.perf_counter() - start) * 1000),
            "id": body.get("id") if isinstance(body, dict) else None,
            "body": body,
        }
    except Exception as exc:
        return {
            "username": session.username,
            "index": index,
            "status": 0,
            "latency_ms": round((time.perf_counter() - start) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def delete_created_messages(results: list[dict], sessions: dict[str, Session]) -> None:
    for item in results:
        message_id = item.get("id")
        if not message_id:
            continue
        response = request("DELETE", f"/api/chat/{message_id}", session=sessions[item["username"]])
        require_status(response, {200, 404}, f"cleanup chat {message_id}")


def assert_owner_isolation(session: Session, own_marker: str, foreign_marker: str) -> None:
    response = request("GET", f"/api/chat/user/{session.user_id}?limit=100", session=session)
    require_status(response, {200}, f"list chat {session.username}")
    body = response.json()
    own = [item for item in body if own_marker in item.get("user_message", "")]
    foreign = [item for item in body if foreign_marker in item.get("user_message", "")]
    if len(own) != 10:
        raise CheckFailure(f"{session.username}: expected 10 own concurrent messages, got {len(own)}")
    if foreign:
        raise CheckFailure(f"{session.username}: listed foreign concurrent messages")


def main() -> int:
    guard_or_exit()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    marker = f"qa-concurrency-{uuid4().hex[:12]}"

    user_a = login("qa_user_a", "QA_USER_A_PASSWORD")
    user_b = login("qa_user_b", "QA_USER_B_PASSWORD")
    sessions = {user_a.username: user_a, user_b.username: user_b}

    work = [(user_a, marker, i) for i in range(10)] + [(user_b, marker, i) for i in range(10)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda args: create_chat(*args), work))

    ok = [item for item in results if item["status"] == 201 and item.get("id")]
    try:
        if len(ok) != len(results):
            raise CheckFailure(f"expected {len(results)} successful creates, got {len(ok)}")
        assert_owner_isolation(user_a, f"{marker}:{user_a.username}", f"{marker}:{user_b.username}")
        assert_owner_isolation(user_b, f"{marker}:{user_b.username}", f"{marker}:{user_a.username}")
    finally:
        delete_created_messages(results, sessions)

    latencies = sorted(item["latency_ms"] for item in results)
    p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
    lines = [
        "# QA concurrency report",
        "",
        f"Checked: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "| Scenario | Requests | Pass | Fail | Status |",
        "|---|---:|---:|---:|---|",
        f"| concurrent authenticated chat creates | {len(results)} | {len(ok)} | {len(results) - len(ok)} | PASS |",
        "| owner-isolated listing after concurrent writes | 2 | 2 | 0 | PASS |",
        f"| p95 create latency ms | {p95} |  |  | PASS |",
        "",
        "Raw results:",
        "",
        "```json",
        json.dumps(results, ensure_ascii=False, indent=2),
        "```",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("QA concurrency PASS")
    print(f"- report: {REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"QA concurrency FAIL: {exc}")
        raise SystemExit(1) from exc
