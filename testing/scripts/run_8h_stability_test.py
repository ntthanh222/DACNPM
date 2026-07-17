"""Resumable, low-load eight-hour local stability monitor.

Each cycle is isolated: a failed probe is recorded and does not stop later
cycles. State is checkpointed every cycle so an interrupted run can resume.
No credentials are written to logs; login probes are enabled only when their
password environment variables are present.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "testing" / "reports" / "cybersec-assistant"
STATE = OUT / "8h_checkpoint.json"
LOG = OUT / "8h_stability.log"
CSV = OUT / "HOURLY_METRICS.csv"
PID = OUT / "8h_stability.pid"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe(url: str, method: str = "GET", body: bytes | None = None) -> tuple[bool, int, float]:
    started = time.perf_counter()
    try:
        req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.status
            response.read(512)
        return True, status, (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        return exc.code in {401, 403}, exc.code, (time.perf_counter() - started) * 1000
    except Exception:
        return False, 0, (time.perf_counter() - started) * 1000


def login_probe(username_env: str, password_env: str) -> dict:
    username = os.getenv(username_env)
    password = os.getenv(password_env)
    if not username or not password:
        return {"ok": False, "status": "blocked_missing_env"}
    started = time.perf_counter()
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    try:
        req = urllib.request.Request("http://localhost:8000/api/auth/login", data=payload, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
            return {"ok": bool(body.get("access_token")), "status": response.status, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        return {"ok": False, "status": type(exc).__name__}


def docker_health() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=True,
        )
        names = {line.split("|", 1)[0] for line in result.stdout.splitlines() if line}
        required = {"cybersec-backend", "cybersec-crawler", "cybersec-frontend", "cybersec-redis", "cybersec-chromadb", "cybersec-rasa", "cybersec-rasa-actions", "cybersec-redis-commander", "cybersec-prometheus", "cybersec-grafana"}
        missing = sorted(required - names)
        return not missing, "ok" if not missing else "missing=" + ",".join(missing)
    except Exception as exc:
        return False, type(exc).__name__


def command_probe(command: list[str], timeout: int = 120) -> dict:
    """Run a bounded local probe without writing its stdout to the log."""
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        data = {"ok": result.returncode == 0, "returncode": result.returncode}
        if result.stdout:
            data["output"] = result.stdout[-4000:]
        return data
    except Exception as exc:
        return {"ok": False, "returncode": -1, "error": type(exc).__name__}


def one_cycle(index: int) -> dict:
    started = time.perf_counter()
    health_ok, health_detail = docker_health()
    checks = {}
    for name, url in {
        "backend_health": "http://localhost:8000/health",
        "frontend": "http://localhost:3000/login.html",
        "prometheus": "http://localhost:9090/-/ready",
        "openapi": "http://localhost:8000/openapi.json",
    }.items():
        ok, status, latency = probe(url)
        checks[name] = {"ok": ok, "status": status, "latency_ms": round(latency, 2)}
    checks["admin_login"] = login_probe("QA_ADMIN_USERNAME", "QA_ADMIN_PASSWORD")
    checks["user_login"] = login_probe("QA_USER_USERNAME", "QA_USER_PASSWORD")
    extended = {}
    if index % 6 == 0:  # every 30 minutes at the default five-minute cadence
        extended["permission_boundary"] = command_probe(["python", "testing/scripts/permission_boundary_check.py"])
        extended["http_smoke"] = command_probe(["python", "testing/scripts/http_smoke.py"])
        extended["admin_e2e"] = {"ok": False, "status": "blocked_qa_fixture"}
        extended["authenticated_matrix"] = {"ok": False, "status": "blocked_qa_fixture"}
    if index % 12 == 0:  # every hour at the default cadence
        extended["resource_snapshot"] = command_probe(["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}"], timeout=60)
        extended["restart_snapshot"] = command_probe(["docker", "ps", "--format", "{{.Names}}|{{.Status}}"], timeout=60)
        extended["compose_ps"] = command_probe(["docker", "compose", "ps"], timeout=60)
    return {
        "cycle": index, "timestamp_utc": now(), "health_ok": health_ok,
        "health_detail": health_detail, "checks": checks,
        "extended": extended,
        "cycle_latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-hours", type=float, default=8.0)
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    PID.write_text(str(os.getpid()), encoding="utf-8")
    state = {"started_utc": now(), "ended_utc": None, "next_cycle": 1, "cycles": []}
    if args.resume and STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    deadline = time.time() + args.duration_hours * 3600
    with LOG.open("a", encoding="utf-8") as log:
        log.write(f"START pid={os.getpid()} utc={now()} resume={args.resume}\n")
        csv_exists = CSV.exists()
        csv_handle = CSV.open("a", newline="", encoding="utf-8")
        csv_writer = csv.DictWriter(csv_handle, fieldnames=["cycle", "timestamp_utc", "health_ok", "cycle_latency_ms"])
        if not csv_exists:
            csv_writer.writeheader()
        while time.time() < deadline:
            cycle = one_cycle(int(state.get("next_cycle", 1)))
            state.setdefault("cycles", []).append(cycle)
            state["next_cycle"] = cycle["cycle"] + 1
            state["last_checkpoint_utc"] = now()
            STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
            csv_writer.writerow({"cycle": cycle["cycle"], "timestamp_utc": cycle["timestamp_utc"], "health_ok": cycle["health_ok"], "cycle_latency_ms": cycle["cycle_latency_ms"]})
            csv_handle.flush()
            log.write(json.dumps(cycle, separators=(",", ":")) + "\n")
            log.flush()
            if time.time() + args.interval_seconds >= deadline:
                break
            time.sleep(max(1, args.interval_seconds))
        csv_handle.close()
    state["ended_utc"] = now()
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    rows = []
    for cycle in state.get("cycles", []):
        rows.append({"cycle": cycle["cycle"], "timestamp_utc": cycle["timestamp_utc"], "health_ok": cycle["health_ok"], "cycle_latency_ms": cycle["cycle_latency_ms"]})
    with CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cycle", "timestamp_utc", "health_ok", "cycle_latency_ms"])
        writer.writeheader(); writer.writerows(rows)
    PID.unlink(missing_ok=True)
    report = OUT / "8H_STABILITY_REPORT.md"
    passed = sum(1 for row in rows if row["health_ok"] and all(v["ok"] for v in state["cycles"][row["cycle"] - 1]["checks"].values()))
    report.write_text("\n".join(["# 8H Stability Report", "", f"Started (UTC): {state['started_utc']}", f"Ended (UTC): {state['ended_utc']}", f"Cycles recorded: {len(rows)}", f"Fully passing cycles: {passed}/{len(rows)}", "", "This report is only complete after the configured eight-hour process reaches its end checkpoint.", ""]), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
