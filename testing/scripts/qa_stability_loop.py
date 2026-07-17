"""Three-round bounded QA stability loop."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


REPORT = ROOT / "testing" / "reports" / "cybersec-assistant" / "QA_STABILITY_LOOP_REPORT.md"


def run_step(name: str, command: list[str], env: dict[str, str]) -> tuple[str, int, str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    evidence = (result.stdout + "\n" + result.stderr).strip().replace("\n", " ")[:500]
    return name, result.returncode, evidence


def main() -> int:
    guard_or_exit()
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("BACKEND_URL", env.get("API_BASE_URL", "http://localhost:8100"))
    env.setdefault("FRONTEND_URL", "http://localhost:3100")

    python = sys.executable
    steps = [
        ("http-smoke", [python, "testing/scripts/http_smoke.py"]),
        ("api-contract", [python, "testing/scripts/api_contract.py"]),
        ("auth-role-matrix", [python, "testing/scripts/authenticated_matrix_check.py"]),
        ("idor-matrix", [python, "testing/scripts/idor_matrix_check.py"]),
        ("admin-mutation-matrix", [python, "testing/scripts/admin_mutation_matrix_check.py"]),
        ("qa-recovery", [python, "testing/scripts/qa_recovery_check.py"]),
        ("qa-concurrency", [python, "testing/scripts/qa_concurrency_check.py"]),
    ]

    rows: list[tuple[int, str, int, str]] = []
    for round_index in range(1, 4):
        for name, command in steps:
            step_name, code, evidence = run_step(name, command, env)
            rows.append((round_index, step_name, code, evidence))

    passed = sum(code == 0 for _, _, code, _ in rows)
    lines = [
        "# QA stability loop report",
        "",
        f"Checked: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "| Round | Step | Exit | Status | Evidence |",
        "|---:|---|---:|---|---|",
    ]
    for round_index, name, code, evidence in rows:
        status = "PASS" if code == 0 else "FAIL"
        safe_evidence = evidence.replace("|", "\\|")
        lines.append(f"| {round_index} | {name} | {code} | {status} | {safe_evidence} |")
    lines.append("")
    lines.append(f"Summary: **{passed}/{len(rows)} PASS**.")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("QA stability loop " + ("PASS" if passed == len(rows) else "FAIL"))
    print(f"- report: {REPORT}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
