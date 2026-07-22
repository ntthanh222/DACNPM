# Failure Injection Results

This document records the system's behavior when dependencies are intentionally stopped in the QA environment.

| Component Stopped | Target Command | Expected Behavior | Actual Behavior | HTTP Status | Recovery Behavior | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rasa NLU** | `docker compose stop rasa` | `/health/ready` returns degraded with `rasa_nlu: offline`. Chat uses local rules fallback | As expected. Chat fallback matches queries locally or falls back to Gemini | 200 degraded | Restored via `docker compose start rasa` | **PASS** |
| **Rasa Actions** | `docker compose stop rasa-actions` | `/health/ready` returns degraded with `rasa_actions: offline` | As expected. Actions checks fail, chat uses local fallback | 200 degraded | Restored via `docker compose start rasa-actions` | **PASS** |
| **ChromaDB** | `docker compose stop chromadb` | `/health/ready` returns degraded with `chromadb: offline`. RAG retrieval is bypassed | As expected. Chat falls back to Gemini without local retrieval context | 200 degraded | Restored via `docker compose start chromadb` | **PASS** |
| **Redis** | `docker compose stop redis` | `/health/ready` fails immediately (Redis is a mandatory dependency) | Returns `503 Service Unavailable` with details showing Redis is offline | 503 Unhealthy | Restored via `docker compose start redis` | **PASS** |

## Summary of Recovery
No full stack restarts were required for recovery. Once any stopped service was restarted, the backend automatically re-established connection and transitioned back to a fully `healthy` status on subsequent readiness checks.
