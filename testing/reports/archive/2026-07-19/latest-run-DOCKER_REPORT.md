# Docker report

Checked: `2026-07-18T21:03:23.231259+00:00`

## Evidence

- `docker compose config --quiet`: **PASS**
- `docker compose ps`: **PASS**

| Service | State | Health | Status |
|---|---|---|---|
| backend-qa | running | healthy | PASS |
| chromadb-test | running |  | PASS |
| frontend-qa | running | healthy | PASS |
| postgres-qa | running | healthy | PASS |
| redis-test | running | healthy | PASS |

## Safety

No `down --volumes`, volume deletion, or production-data operation was performed.
