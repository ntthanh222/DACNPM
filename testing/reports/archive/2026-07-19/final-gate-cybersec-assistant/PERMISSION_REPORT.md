# Permission boundary report

Unauthenticated, non-mutating authorization probe against live Docker API.

| Method | Route | HTTP | Status |
|---|---|---:|---|
| GET | `/api/admin/users` | 401 | PASS |
| GET | `/api/admin/users/{user_id}` | 401 | PASS |
| PUT | `/api/admin/users/{user_id}/role` | 401 | PASS |
| PUT | `/api/admin/users/{user_id}/status` | 401 | PASS |
| GET | `/api/admin/users/{user_id}/activity` | 401 | PASS |
| POST | `/api/admin/crawler/trigger` | 401 | PASS |
| GET | `/api/admin/crawler/config` | 401 | PASS |
| PUT | `/api/admin/crawler/config` | 401 | PASS |
| GET | `/api/admin/crawler/stats` | 401 | PASS |
| GET | `/api/admin/crawler/logs` | 401 | PASS |
| GET | `/api/admin/news` | 401 | PASS |
| PUT | `/api/admin/news/{news_id}` | 401 | PASS |
| DELETE | `/api/admin/news/{news_id}` | 401 | PASS |
| GET | `/api/admin/system/api-usage` | 401 | PASS |
| GET | `/api/admin/system/cache` | 401 | PASS |
| DELETE | `/api/admin/system/cache/{cve_id}` | 401 | PASS |
| PUT | `/api/admin/system/cache/{cve_id}` | 401 | PASS |
| GET | `/api/admin/system/analytics` | 401 | PASS |
| GET | `/api/admin/system/dashboard/cached` | 401 | PASS |
| POST | `/api/admin/system/dashboard/clear-cache` | 401 | PASS |
| GET | `/api/admin/system/cache/stats` | 401 | PASS |
| POST | `/api/admin/rag/ingest` | 401 | PASS |
| GET | `/api/admin/rag/documents` | 401 | PASS |
| DELETE | `/api/admin/rag/documents/{doc_id}` | 401 | PASS |
| GET | `/api/admin/rag/intents` | 401 | PASS |
| GET | `/api/admin/nlu/failed-queries` | 401 | PASS |
| PUT | `/api/admin/nlu/queries/{query_id}/review` | 401 | PASS |
| POST | `/api/admin/nlu/add-to-training` | 401 | PASS |
| POST | `/api/admin/nlu/retrain` | 401 | PASS |
| GET | `/api/admin/nlu/status` | 401 | PASS |
| GET | `/api/admin/nlu/intent-distribution` | 401 | PASS |

Summary: **31/31 boundary checks PASS**.

Authenticated owner/role CRUD matrix remains unproven without a synchronized QA database fixture.
