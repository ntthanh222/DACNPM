"""Short resource/latency soak test for the running Compose stack."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing/reports/cybersec-assistant/SOAK_REPORT.md"


def main() -> int:
    samples = []
    end = time.monotonic() + 120
    while time.monotonic() < end:
        start = time.perf_counter()
        try:
            with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as response:
                status = response.status
        except Exception:
            status = 0
        stats = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.PIDs}}"], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=15).stdout.strip().splitlines()
        samples.append({"status": status, "latency_ms": round((time.perf_counter() - start) * 1000), "stats": stats})
        time.sleep(2)
    latencies = [item["latency_ms"] for item in samples]
    passed = sum(item["status"] == 200 for item in samples)
    report = ["# Soak report", "", f"Checked: `{datetime.now(timezone.utc).isoformat()}`", "", "| Metric | Value |", "|---|---:|", f"| Duration | 120 seconds |", f"| Health samples | {len(samples)} |", f"| Health PASS | {passed} |", f"| Health FAIL | {len(samples)-passed} |", f"| P95 health latency (ms) | {sorted(latencies)[max(0, int(len(latencies)*0.95)-1)] if latencies else 'n/a'} |", f"| Gate | {'PASS' if samples and passed == len(samples) else 'FAIL'} |", "", "Raw samples:", "", "```json", json.dumps(samples, ensure_ascii=False, indent=2), "```"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if samples and passed == len(samples) else 1


if __name__ == "__main__":
    raise SystemExit(main())
