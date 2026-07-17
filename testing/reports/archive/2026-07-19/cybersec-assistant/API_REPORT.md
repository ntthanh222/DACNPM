# API report

Checked: `2026-07-18T21:02:57.494925+00:00`

| Test ID | Endpoint | HTTP | Evidence | Status |
|---|---|---:|---|---|
| API-HEALTH | `/health` | 200 | {'status': 'healthy'} | PASS |
| API-METRICS | `/metrics` | 200 | # HELP cybersec_app_uptime_seconds Application uptime in seconds.
# TYPE cybersec_app_uptime_seconds gauge
cybersec_app_uptime_seconds 955.791190
# HELP cybersec_http_requests_total Total HTTP requests.
# TYPE cybersec_http_requests_total c | PASS |
| API-OPENAPI | `/openapi.json` | 200 | {'openapi': '3.1.0', 'info': {'title': 'CyberSec Assistant API', 'description': 'Backend API for Cyber Security Assistant', 'version': '1.0.0'}, 'paths': {'/api/profiles/': {'post': {'tags': ['profiles'], 'summary': 'Create New Profile', 'd | PASS |
| API-AUTH-401 | `/api/auth/me` | 401 | {'error': 'HTTPException', 'message': '401: Not authenticated. No credentials provided.', 'details': {}, 'timestamp': None} | PASS |
| API-ADMIN-401 | `/api/admin/users` | 401 | {'error': 'HTTPException', 'message': '401: Not authenticated. No credentials provided.', 'details': {}, 'timestamp': None} | PASS |
| API-LOGIN-INVALID | `/api/auth/login` | 401 | {'error': 'HTTPException', 'message': '401: Incorrect username or password', 'details': {}, 'timestamp': None} | PASS |
| API-PASSWORD-VALIDATION | `/api/chatbot/password-strength` | 200 | {'password_length': 8, 'strength_score': 40, 'strength': 'TRUNG BÌNH', 'strength_color': 'yellow', 'crack_time': '< 1 hour', 'feedback': ['Password này đã bị lộ trong 52372427 vụ dữ liệu bị hack!', 'Sử dụng ít nhất 12 ký tự', 'Kết hợp chữ h | PASS |
| API-PHISHING-VALIDATION | `/api/chatbot/phishing-check` | 200 | {'error': 'Invalid URL format or security check failed', 'scan_date': '2026-07-18T21:02:57.488698+00:00', 'fallback': True} | PASS |

Summary: **8/8 PASS**.
