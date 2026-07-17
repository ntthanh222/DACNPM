"""Small isolated-QA auth smoke for register, token verification, /me, and bad tokens."""
from __future__ import annotations

import os
import sys
import uuid

import requests


API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")


def request(method: str, path: str, **kwargs) -> requests.Response:
    return requests.request(method, f"{API_BASE_URL}{path}", timeout=15, **kwargs)


def main() -> int:
    password = os.environ.get("QA_REGISTER_PASSWORD")
    if not password:
        print("Missing QA_REGISTER_PASSWORD.")
        return 2

    suffix = uuid.uuid4().hex[:12]
    payload = {
        "username": f"qa_reg_{suffix}",
        "email": f"qa_reg_{suffix}@qa.cybersec-assistant.dev",
        "full_name": "QA Registration Smoke",
        "password": password,
    }

    ok = True

    register_response = request("POST", "/api/auth/register", json=payload)
    if register_response.status_code != 200:
        print(f"Register failed: {register_response.status_code}")
        ok = False
        token = None
    else:
        token = register_response.json().get("access_token")
        print("Register PASS")

    duplicate_response = request("POST", "/api/auth/register", json=payload)
    if duplicate_response.status_code != 409:
        print(f"Duplicate register expected 409, got {duplicate_response.status_code}")
        ok = False
    else:
        print("Duplicate register PASS")

    bad_login_response = request(
        "POST",
        "/api/auth/login",
        json={"username": payload["username"], "password": password + "-wrong"},
    )
    if bad_login_response.status_code != 401:
        print(f"Bad login expected 401, got {bad_login_response.status_code}")
        ok = False
    else:
        print("Bad login PASS")

    bad_me_response = request("GET", "/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    if bad_me_response.status_code != 401:
        print(f"Bad token /me expected 401, got {bad_me_response.status_code}")
        ok = False
    else:
        print("Bad token /me PASS")

    if token:
        me_response = request("GET", "/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if me_response.status_code != 200 or me_response.json().get("username") != payload["username"]:
            print(f"/me after register failed: {me_response.status_code}")
            ok = False
        else:
            print("/me after register PASS")

        verify_response = request("POST", f"/api/auth/verify-token?token={token}")
        if verify_response.status_code != 200 or not verify_response.json().get("valid"):
            print(f"verify-token failed: {verify_response.status_code}")
            ok = False
        else:
            print("verify-token PASS")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
