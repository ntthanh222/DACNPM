# CyberSec Assistant test harness

This directory contains the repeatable, evidence-first QA harness required by
`yeucau.md`. Tests are grouped by capability and reports are written under
`testing/reports/`.

## Quick start

From the repository root:

```powershell
python testing/scripts/discover_catalog.py
python testing/scripts/docker_check.py
python testing/scripts/http_smoke.py
.\backend\venv\Scripts\pytest.exe backend/tests -q
Push-Location frontend; npm test; Pop-Location
```

`docker_check.py` only validates and inspects the Compose project. It does not
remove volumes or production data. HTTP checks report `BLOCKED` when the
Docker services are not running; they never convert an unavailable service
into a false PASS.

## Evidence policy

Every report records the command, timestamp, observed result and status. A
feature can become `STABLE` only after repeated, isolated runs and restart
verification. Provider-backed AI tests use the controlled fixture provider by
default and only use a real provider when an explicit test key is configured.

Run `python testing/scripts/generate_required_reports.py` to create the complete
report inventory required by `yeucau.md`. Empty reports remain `NOT TESTED`; no
runtime result is fabricated. The ordered PowerShell runner is
`testing/scripts/run_quality_suite.ps1`.
