"""Non-destructive Docker/Compose validation with evidence output."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "testing" / "reports" / "DOCKER_REPORT.md"


def run(*args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=120)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    checked = datetime.now(timezone.utc).isoformat()
    config_code, config = run("docker", "compose", "config", "--quiet")
    ps_code, ps = run("docker", "compose", "ps", "--format", "json")
    services = []
    if ps_code == 0 and ps:
        for line in ps.splitlines():
            try:
                services.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    service_statuses = []
    for item in services:
        state = str(item.get("State", item.get("state", "unknown"))).lower()
        health = str(item.get("Health", item.get("health", ""))).lower()
        service_statuses.append(state == "running" and health not in {"unhealthy", "starting"})
    runtime_status = "PASS" if ps_code == 0 and services and all(service_statuses) else ("FAIL" if services else "BLOCKED")
    lines = ["# Docker report", "", f"Checked: `{checked}`", "", "## Evidence", "",
             f"- `docker compose config --quiet`: **{'PASS' if config_code == 0 else 'FAIL'}**",
             f"- `docker compose ps`: **{runtime_status}**"]
    lines += ["", "| Service | State | Health | Status |", "|---|---|---|---|"]
    if services:
        for item in services:
            state = item.get("State", item.get("state", "unknown"))
            health = item.get("Health", item.get("health", "unknown"))
            status = "PASS" if str(state).lower() == "running" and str(health).lower() not in {"unhealthy", "starting"} else "FAIL"
            lines.append(f"| {item.get('Service', item.get('Name', 'unknown'))} | {state} | {health} | {status} |")
    else:
        lines.append("| all services | unavailable | unavailable | BLOCKED |")
    lines += ["", "## Safety", "", "No `down --volumes`, volume deletion, or production-data operation was performed."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)
    print(config)
    return 0 if config_code == 0 and runtime_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
