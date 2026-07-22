# Baseline Runtime-First Validation

## 1. Environment Details
* **Current Branch**: `checkpoint-stabilization` (branched from `main`)
* **Files with existing modifications**:
  * `.dockerignore`
  * `backend/Dockerfile`
  * `backend/tests/test_system_regressions.py`
  * `docker-compose.yml`
  * `hd.md`
  * `scripts/windows/start.bat`
* **Container State (docker compose ps)**:
  * `codex_docker_cybersec_ascii-backend-1`: Up (healthy)
  * `codex_docker_cybersec_ascii-chromadb-1`: Up
  * `codex_docker_cybersec_ascii-crawler-1`: Up (healthy)
  * `codex_docker_cybersec_ascii-frontend-1`: Up (healthy)
  * `codex_docker_cybersec_ascii-grafana-1`: Up
  * `codex_docker_cybersec_ascii-prometheus-1`: Up
  * `codex_docker_cybersec_ascii-rasa-1`: Up (healthy)
  * `codex_docker_cybersec_ascii-rasa-actions-1`: Up (healthy)
  * `codex_docker_cybersec_ascii-redis-1`: Up (healthy)
  * `codex_docker_cybersec_ascii-redis-commander-1`: Up (healthy)
* **Host Ports**:
  * `8000`: Backend API
  * `8002`: Crawler service
  * `15005`: Rasa NLU
  * `15055`: Rasa Action Server
  * `3000`: Frontend Nginx
  * `3001`: Grafana
  * `8081`: Redis Commander
  * `9090`: Prometheus
  * `6379`: Redis
* **Current Active Rasa Model**:
  * File name: `20260714-124603-stubborn-restaurant.tar.gz`
  * Status: Outdated (there are newer models like `20260719-113557-tender-basket.tar.gz` generated today)
  * Issue: Rasa startup command uses `find /app/models -maxdepth 1 -type f -name '*.tar.gz' -print -quit` which is alphabetically/directory entry ordered and doesn't select the newest model.

## 2. Accessibility Status
* **Backend API (`/health`)**: Reachable (`http://localhost:8000/health` -> healthy)
* **Frontend Web UI**: Reachable (`http://localhost:3000` -> Login screen)
* **Rasa Server (`/status`)**: Reachable (`http://localhost:15005/status` -> 200 OK)

## 3. Initial Identified Issues / Hypotheses
1. **Rasa Model Lifecycle Issues**: The startup command uses a blind `find` search. It should follow Giai đoạn 3 (reading manifest JSON file `rasa/models/current-model.json` and checking SHA-256 before starting).
2. **Duplicate Chat Persistence**: The backend `ChatbotService` persists the chat message automatically. However, the frontend dashboard `ChatController` still sends an additional `POST /api/chat/` call to save it again.
3. **Chatbot Orchestration Fragmentation**: `HybridChatbot` is currently dead code, and the active `ChatbotService` doesn't perform real LLM Gemini + RAG orchestration on routing fallbacks, nor does it parse real Rasa NLU intents.
4. **SSE & POST Inconsistencies**: The SSE streaming endpoint generates a UUID/session ID for anonymous users and passes it as `user_id` to the chatbot service, incorrectly invoking the authenticated NLU pathway instead of the anonymous/local fallback path.
5. **Authentications**: `X-User-ID` header is sent by frontend and accepted by backend for certain calls without verification, rather than standard Bearer JWT tokens.
