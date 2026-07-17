"""Bounded repeatability checks; never retries a failing assertion forever."""
from __future__ import annotations
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing" / "reports" / "cybersec-assistant" / "STABILITY_REPORT.md"

def main() -> int:
    rows = []
    for suite, command, runs in [("smoke", ["python", "testing/scripts/http_smoke.py"], 10), ("api-contract", ["python", "testing/scripts/api_contract.py"], 3)]:
        for run in range(1, runs + 1):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
            rows.append((suite, run, result.returncode, "PASS" if result.returncode == 0 else "FAIL"))
    lines = ["# Stability report", "", f"Checked: `{datetime.now(timezone.utc).isoformat()}`", "",
             "| Suite | Run | Exit code | Status |", "|---|---:|---:|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", f"Summary: **{sum(x[3] == 'PASS' for x in rows)}/{len(rows)} PASS**."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if all(x[3] == "PASS" for x in rows) else 1

if __name__ == "__main__":
    raise SystemExit(main())
