"""Bounded read-only concurrency probe against Docker services."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing" / "reports" / "cybersec-assistant" / "CONCURRENCY_REPORT.md"

def one(url: str) -> tuple[str, int, str]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read(512).decode("utf-8", "replace")
            return url, response.status, body
    except Exception as exc:
        return url, 0, type(exc).__name__

def main() -> int:
    urls = ["http://localhost:8000/health"] * 20 + ["http://localhost:8000/metrics"] * 20 + ["http://localhost:3000/login.html"] * 20
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(one, urls))
    passed = sum(code == 200 for _, code, _ in results)
    lines = ["# Concurrency report", "", f"Checked: `{datetime.now(timezone.utc).isoformat()}`", "",
             "| Probe | Requests | HTTP 200 | Status |", "|---|---:|---:|---|"]
    for name, needle in [("backend health", "/health"), ("backend metrics", "/metrics"), ("frontend login", "/login.html")]:
        subset = [x for x in results if needle in x[0]]
        count = sum(x[1] == 200 for x in subset)
        lines.append(f"| {name} | {len(subset)} | {count} | {'PASS' if count == len(subset) else 'FAIL'} |")
    lines += ["", f"Total: **{passed}/{len(results)} HTTP 200**. Read-only probe; no shared state was mutated."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
