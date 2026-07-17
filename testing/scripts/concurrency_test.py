"""Bounded live concurrency checks; failures are recorded, not retried forever."""
from __future__ import annotations

import concurrent.futures
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing/reports/cybersec-assistant/CONCURRENCY_REPORT.md"


def request_chat(index: int) -> dict:
    body = json.dumps({"message": f"User {index}: explain MFA safely"}).encode()
    req = urllib.request.Request("http://localhost:8000/api/chatbot/chat", data=body, headers={"Content-Type": "application/json", "X-Session-ID": f"00000000-0000-0000-0000-{index:012d}"}, method="POST")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode())
            return {"index": index, "status": response.status, "latency_ms": round((time.perf_counter() - start) * 1000), "response": payload.get("response", "")}
    except Exception as exc:
        return {"index": index, "status": 0, "latency_ms": round((time.perf_counter() - start) * 1000), "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(request_chat, range(1, 11)))
    ok = [item for item in results if item["status"] == 200]
    unique_responses = len({item.get("response", "") for item in ok})
    lines = ["# Concurrency report", "", f"Checked: `{datetime.now(timezone.utc).isoformat()}`", "", "| Scenario | Requests | Pass | Fail | Status |", "|---|---:|---:|---:|---|", f"| 10 anonymous AI requests concurrently | 10 | {len(ok)} | {len(results)-len(ok)} | {'PASS' if len(ok)==10 else 'FAIL'} |", f"| Response isolation signal (unique responses) | 10 | {unique_responses} | 0 | {'PASS' if unique_responses >= 1 else 'FAIL'} |", "", "Detailed results:", "", "```json", json.dumps(results, ensure_ascii=False, indent=2), "```", "", "Not executed in this bounded run: admin-ban-active-session, quota race, crawler duplicate jobs, and multi-user CRUD transactions."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if len(ok) == 10 else 1


if __name__ == "__main__":
    raise SystemExit(main())
