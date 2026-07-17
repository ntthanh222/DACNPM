# Smoke report

Checked: `2026-07-18T21:02:56.594601+00:00`

| Check | URL | Observed | Status |
|---|---|---:|---|
| backend health | `http://localhost:8100/health` | 200 | PASS |
| backend metrics | `http://localhost:8100/metrics` | 200 | PASS |
| frontend login | `http://localhost:3100/login.html` | 200 | PASS |
| frontend dashboard | `http://localhost:3100/dashboard.html` | 200 | PASS |
| frontend assistant | `http://localhost:3100/pages/assistant/chat.html` | 200 | PASS |
| frontend URL analyzer | `http://localhost:3100/pages/url-check/index.html` | 200 | PASS |
| frontend admin | `http://localhost:3100/pages/admin.html` | 200 | PASS |
