"""Read-only authorization boundary probe for live Docker API.

It intentionally sends no credentials and never mutates data. A protected
admin route must reject the request before validation or business execution.
This does not replace authenticated owner/role matrix testing.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing" / "reports" / "cybersec-assistant" / "PERMISSION_REPORT.md"


def request(method: str, path: str) -> int:
    req = urllib.request.Request(
        f"http://localhost:8000{path}",
        data=None if method == "GET" else b"{}",
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def main() -> int:
    with urllib.request.urlopen("http://localhost:8000/openapi.json", timeout=15) as response:
        spec = json.loads(response.read().decode("utf-8"))

    cases = []
    for path, operations in spec.get("paths", {}).items():
        if not path.startswith("/api/admin"):
            continue
        for method in operations:
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            status = request(method.upper(), path)
            passed = status in {401, 403}
            cases.append((method.upper(), path, status, passed))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Permission boundary report",
        "",
        "Unauthenticated, non-mutating authorization probe against live Docker API.",
        "",
        "| Method | Route | HTTP | Status |",
        "|---|---|---:|---|",
    ]
    lines.extend(f"| {m} | `{p}` | {s} | {'PASS' if ok else 'FAIL'} |" for m, p, s, ok in cases)
    passed = sum(ok for *_rest, ok in cases)
    lines.extend(["", f"Summary: **{passed}/{len(cases)} boundary checks PASS**.", "", "Authenticated owner/role CRUD matrix remains unproven without a synchronized QA database fixture."])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if cases and passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
