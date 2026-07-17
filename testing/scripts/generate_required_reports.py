"""Create required evidence reports without inventing test results."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "testing" / "reports" / "cybersec-assistant"
REPORTS = [
    "FUNCTION_CATALOG",
    "DOCKER_REPORT", "SMOKE_REPORT", "DASHBOARD_REPORT", "AUTH_REPORT", "USER_REPORT",
    "ADMIN_REPORT", "URL_ANALYSIS_REPORT", "PASSWORD_REPORT", "AI_FUNCTION_REPORT",
    "AI_ACCURACY_REPORT", "AI_HALLUCINATION_REPORT", "AI_SECURITY_REPORT", "NEWS_REPORT",
    "CRAWLER_REPORT", "NEWS_MODERATION_REPORT", "RAG_REPORT", "MONITORING_REPORT",
    "API_REPORT", "DATABASE_REPORT", "PERMISSION_REPORT", "E2E_REPORT", "CONCURRENCY_REPORT",
    "RECOVERY_REPORT", "SOAK_REPORT", "FLAKY_TEST_REPORT", "BUG_REPORT",
    "FIX_VERIFICATION_REPORT", "REGRESSION_REPORT", "FINAL_REPORT",
]

def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    for name in REPORTS:
        path = REPORT_DIR / f"{name}.md"
        if path.exists() and path.read_text(encoding="utf-8", errors="replace").strip():
            continue
        title = name.replace("_", " ").title()
        path.write_text(
            f"# {title}\n\nChecked: `{now}`\n\n"
            "| Test ID | Module | Input | Expected | Actual | Runs | Pass | Fail | Status |\n"
            "|---|---|---|---|---|---:|---:|---:|---|\n"
            "| pending | see harness | not run | evidence required | no runtime evidence yet | 0 | 0 | 0 | NOT TESTED |\n\n"
            "No PASS is inferred. Run the relevant harness against Docker and record observed evidence.\n",
            encoding="utf-8",
        )
    print(f"Generated/retained {len(REPORTS)} reports in {REPORT_DIR}")

if __name__ == "__main__":
    main()
