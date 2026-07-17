# Security threat model

## Assets

User credentials and JWTs; user/profile/role/quota data; conversations and URL history; RAG documents and embeddings; AI/provider keys; crawler/news data; Redis queues; Supabase service-role access; Docker volumes and logs.

## Trust boundaries and entry points

- Browser to Nginx/frontend and backend HTTP APIs.
- Authenticated versus anonymous API callers; user, admin, and super-admin authorization boundaries.
- Backend to Supabase/PostgREST, Redis, ChromaDB, Rasa, crawler, Prometheus, and Gemini.
- Host filesystem bind mounts into backend/crawler/action containers.
- Admin file/RAG ingestion and crawler-trigger endpoints.

## Primary threats

Credential theft/brute force, JWT tampering/reuse, IDOR/BOLA across users, role/quota mass assignment, SSRF through URL analysis or AI tools, prompt/document injection, cross-user RAG/conversation leakage, malicious file upload/path traversal, secret leakage in images/logs, exposed monitoring services, and container privilege escalation.

## Current evidence

- Anonymous admin-route boundary: 31/31 rejected with 401/403.
- Backend/crawler/action containers run as `appuser`, with `privileged=false` and no added capabilities.
- Static scan found no private-key marker, `pickle.loads`, `eval`, or `shell=True` in the scoped source scan.
- Authenticated cross-user/role matrix is not verified because QA credentials are unsynchronized.
- Dependency/image scanners `bandit`, `pip-audit`, and `trivy` were not installed; no claim of a clean CVE audit is made.

## Security gate

Status: **INCOMPLETE**. The missing authenticated matrix and unavailable dependency scanner prevent a clean security sign-off.
