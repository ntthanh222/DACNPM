"""Smoke-check the externally observable Docker endpoints without fake passes."""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing" / "reports" / "SMOKE_REPORT.md"
CHECKS = [
    ("backend health", os.getenv("BACKEND_URL", "http://localhost:8000") + "/health", (200,)),
    ("backend metrics", os.getenv("BACKEND_URL", "http://localhost:8000") + "/metrics", (200,)),
    ("frontend login", os.getenv("FRONTEND_URL", "http://localhost:3000") + "/login.html", (200,)),
    ("frontend dashboard", os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard.html", (200,)),
    ("frontend assistant", os.getenv("FRONTEND_URL", "http://localhost:3000") + "/pages/assistant/chat.html", (200,)),
    ("frontend URL analyzer", os.getenv("FRONTEND_URL", "http://localhost:3000") + "/pages/url-check/index.html", (200,)),
    ("frontend admin", os.getenv("FRONTEND_URL", "http://localhost:3000") + "/pages/admin.html", (200,)),
]


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, url, expected in CHECKS:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                code = response.status
                status = "PASS" if code in expected else "FAIL"
                rows.append((name, url, str(code), status))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            rows.append((name, url, type(exc).__name__, "BLOCKED"))
    report = ["# Smoke report", "", f"Checked: `{datetime.now(timezone.utc).isoformat()}`", "",
              "| Check | URL | Observed | Status |", "|---|---|---:|---|"]
    report += [f"| {a} | `{b}` | {c} | {d} |" for a, b, c, d in rows]
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if all(row[3] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
