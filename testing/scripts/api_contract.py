"""Live, non-destructive API contract checks for the Docker-backed stack."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing" / "reports" / "cybersec-assistant" / "API_REPORT.md"
BASE = os.getenv("BACKEND_URL", "http://localhost:8000")

def request(path: str, method: str = "GET", body: object | None = None) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8", "replace")
            try: value = json.loads(raw)
            except json.JSONDecodeError: value = raw
            return response.status, value
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try: value = json.loads(raw)
        except json.JSONDecodeError: value = raw
        return exc.code, value

def main() -> int:
    checks = []
    def check(test_id: str, path: str, expected: set[int], predicate, method="GET", body=None):
        status, value = request(path, method, body)
        ok = status in expected and predicate(value)
        checks.append((test_id, path, status, "PASS" if ok else "FAIL", str(value)[:240]))

    check("API-HEALTH", "/health", {200}, lambda v: isinstance(v, dict) and str(v.get("status", "")).lower() in {"ok", "healthy", "available"})
    check("API-METRICS", "/metrics", {200}, lambda v: isinstance(v, str) and "# HELP" in v and "# TYPE" in v)
    check("API-OPENAPI", "/openapi.json", {200}, lambda v: isinstance(v, dict) and len(v.get("paths", {})) >= 40)
    check("API-AUTH-401", "/api/auth/me", {401, 403}, lambda v: isinstance(v, (dict, str)))
    check("API-ADMIN-401", "/api/admin/users", {401, 403}, lambda v: isinstance(v, (dict, str)))
    check("API-LOGIN-INVALID", "/api/auth/login", {401, 422}, lambda v: isinstance(v, (dict, str)), "POST", {"username": "qa-invalid", "password": "definitely-invalid"})
    check("API-PASSWORD-VALIDATION", "/api/chatbot/password-strength", {200, 422}, lambda v: isinstance(v, (dict, str)), "POST", {"password": "password"})
    check("API-PHISHING-VALIDATION", "/api/chatbot/phishing-check", {200, 422}, lambda v: isinstance(v, (dict, str)), "POST", {"url": "http://127.0.0.1/"})

    lines = ["# API report", "", f"Checked: `{datetime.now(timezone.utc).isoformat()}`", "",
             "| Test ID | Endpoint | HTTP | Evidence | Status |", "|---|---|---:|---|---|"]
    lines += [f"| {a} | `{b}` | {c} | {e} | {d} |" for a, b, c, d, e in checks]
    lines += ["", f"Summary: **{sum(x[3] == 'PASS' for x in checks)}/{len(checks)} PASS**."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if all(x[3] == "PASS" for x in checks) else 1

if __name__ == "__main__":
    raise SystemExit(main())
