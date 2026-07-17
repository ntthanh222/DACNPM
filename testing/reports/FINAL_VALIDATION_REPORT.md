# Final Validation Report

Updated: 2026-07-19 05:05 +07:00

## Conclusion

Status: PROJECT STABLE FOR ISOLATED QA GATE SET.

Do not use this report as a production stability claim. Current evidence proves the local development stack, isolated QA stack, admin auth, security/permission slices, cleanup scripts, and backend/frontend regression suites are healthy after the latest fixes. Production Supabase was not used for cleanup or validation mutations.

## Scope

- Development frontend: `http://localhost:3000`
- Development backend: `http://localhost:8000`
- Development Rasa host port: `http://localhost:15005`
- Development Rasa Actions host port: `http://localhost:15055`
- QA frontend: `http://localhost:3100`
- QA backend: `http://localhost:8100`
- QA PostgreSQL: `cybersec-postgres-qa`, database `cybersec_qa`, host port `55432`
- No production Supabase mutation was performed.

## Issues Fixed In This Pass

| ID | Root Cause | Fix | Evidence |
|---|---|---|---|
| AUDIT-002 | Windows reserved TCP ranges blocked Docker host binds for `5005` and `5055`. | Moved host mappings to `15005` and `15055`; internal container ports stay `5005` and `5055`. | `netsh interface ipv4 show excludedportrange protocol=tcp`; `scripts\windows\start.bat`; `scripts\windows\status.bat` all OK. |
| AUDIT-003 | Backend dev container did not mount `docker-compose.test.yml`, causing runtime regression tests to miss the QA Compose contract file. | Mounted `docker-compose.test.yml` read-only into backend container. | `backend/tests/test_system_regressions.py`: 11 passed. |
| AUDIT-004 | Local PostgreSQL connection test monkeypatched a stub module, but runtime used real or preloaded `psycopg2`; targeted subset could fail when `connect` was absent on the placeholder module. | Monkeypatch `backend.database.local_connection.psycopg2.connect` directly with a complete stub and `raising=False`. | Backend suite: 167 passed, 1 skipped; targeted slice: 17 passed. |
| AUDIT-005 | Live Gemini prompt-injection test treated provider quota/rate-limit as an app failure. | Added explicit provider error classification; deterministic mocked safety test remains mandatory. | Backend suite: 167 passed, 1 skipped; skip was live provider quota. |
| AUDIT-008 | Development full E2E registration scenarios could mutate Supabase-backed dev data and reused timestamp-only usernames across browser projects. | Mutation E2E now requires isolated QA port `3100` and generates UUID-suffixed users. | QA Playwright E2E: 30 passed across desktop, mobile, and tablet. |
| AUDIT-009 | Windows verification/cleanup scripts had stale ports, non-ASCII path assumptions, and local-only pytest behavior. | Reworked scripts to use the ASCII mirror when needed, current health ports, Docker-based backend tests, and safe cleanup modes. | `scripts\windows\verify-project.ps1` PASS; `scripts\windows\cleanup-safe.ps1` analyze-only PASS. |
| AUDIT-010 | Playwright metadata, old QA backups, and stale root reports accumulated after repeated gates. | Deleted generated metadata, retained only three newest QA recovery backups, and archived old reports. | Reference scan PASS; root `testing/reports` contains only current reports plus archive. |

## Validation Evidence

| Gate | Result |
|---|---|
| Development Docker start | PASS |
| Development Docker health | PASS: backend, frontend, crawler, Rasa, Rasa Actions, Redis, Prometheus |
| Development admin API username login | PASS |
| Development admin API email login | PASS |
| Development wrong password | PASS: 401 |
| Development Playwright admin username login | PASS |
| Development Playwright admin email login | PASS |
| QA Docker start | PASS |
| QA backend/frontend health | PASS |
| QA migrations | PASS: 7 migration files applied |
| QA fixture seed/reset | PASS |
| QA admin API check | PASS: username, email, `/me`, admin authorization, wrong password, inactive user, stale token |
| QA Playwright admin email login | PASS |
| QA Playwright admin username login | PASS |
| QA full Playwright E2E | PASS: 30 passed across Chromium, mobile Chrome, tablet Chrome |
| QA HTTP smoke | PASS |
| QA API contract | PASS |
| QA auth flow smoke | PASS |
| QA permission boundary | PASS |
| QA IDOR matrix | PASS |
| QA authenticated matrix | PASS |
| QA admin mutation matrix | PASS |
| QA recovery | PASS |
| QA concurrency | PASS |
| QA stability loop | PASS |
| Docker check | PASS |
| Windows verify-project script | PASS: Docker start, health, backend 167 passed/1 skipped, frontend 31 passed |
| Windows cleanup-safe analyze | PASS |
| Backend tests | PASS: 167 passed, 1 skipped, 8 warnings |
| Backend targeted regression after final test fix | PASS: 17 passed |
| Frontend unit/regression | PASS: 31 passed |
| Broken deleted-file references | PASS: no live references outside manifest/archive |
| Report root cleanup | PASS: only `FINAL_VALIDATION_REPORT.md`, `FINAL_AUDIT_WORKLOG.md`, `DELETED_FILES_MANIFEST.md`, and `archive/` remain |
| Development full Playwright E2E | NOT USED AS FINAL GATE: mutating registration scenarios are now guarded to run only on isolated QA. A dev full run attempted before the guard hit Supabase-backed development data and was stopped from being used as evidence. |

## Docker And Disk

- Baseline Docker snapshot during audit: images about `66.66GB`, build cache about `45.79GB`.
- Post-cleanup/rebuild Docker snapshot: images `56.7GB`, build cache `26.27GB`, containers `917.5kB`, local volumes `224.1MB`.
- Docker builder cleanup reclaimed `20.8GB`; the final rebuild repopulated a small amount of active build cache.
- No Docker volumes were removed.

## File Retention

- Deleted files are recorded in `testing/reports/DELETED_FILES_MANIFEST.md`.
- Retained QA recovery backups:
  - `testing/recovery/backups/qa_recovery_asset_cc05f1b6-b407-4c3e-bc0b-ccada81de313.json`
  - `testing/recovery/backups/qa_recovery_asset_bfe81ebf-5129-476f-b4ee-b1beb14df673.json`
  - `testing/recovery/backups/qa_recovery_asset_08ef9878-f58b-405c-bc9d-a1a84da3bebb.json`

## Residual Limits

- Production stability is not claimed because production was not mutated or fully exercised.
- The live Gemini prompt-injection provider check skipped only on provider quota/availability classification; deterministic safety regression remained mandatory and passed inside the backend suite.

## Related Files

- Worklog: `testing/reports/FINAL_AUDIT_WORKLOG.md`
- Deleted files manifest: `testing/reports/DELETED_FILES_MANIFEST.md`
- User runbook: `hd.md`
- Archived older root reports: `testing/reports/archive/2026-07-19/`
