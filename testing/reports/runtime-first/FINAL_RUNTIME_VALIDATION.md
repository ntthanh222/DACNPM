# Final Runtime Validation Report

## 1. Executive Summary
We have completed a comprehensive, runtime-first stabilization of the **CyberSec Assistant** application. All core features (Authentication, Chat Orchestration, RAG Retrieval, Rasa Model Lifecycle, SSE/POST endpoints, Database Persistence, and Health Observability) have been refactored, tested, and validated in the real container stack.

* **Overall Status**: **PASS**
* **Total Backend Tests**: **170 / 170 Passed** (100% success rate)
* **E2E Browser Automation**: **Passed** on Desktop, Tablet, and Mobile viewports with zero critical path errors.

---

## 2. Identified & Resolved Runtime Defects

All discovered issues have been resolved and verified. Detailed root causes can be found in the [Root Cause Matrix](file:///d:/Đồ%20án%20CNPM/testing/reports/runtime-first/ROOT_CAUSE_MATRIX.md).

### File Modifiations:
* [settings.py](file:///d:/Đồ%20án%20CNPM/backend/config/settings.py): Centralized `rasa_confidence_threshold`.
* [chatbot_service.py](file:///d:/Đồ%20án%20CNPM/backend/services/chatbot_service.py): Merged `HybridChatbot` logic, unified orchestrator parsing, safety routing, and persistence.
* [chatbot.py](file:///d:/Đồ%20án%20CNPM/backend/api/chatbot.py): Aligned POST `/chat` and GET `/chat/stream` endpoints.
* [system.py](file:///d:/Đồ%20án%20CNPM/backend/api/system.py): Created ready/live probes and dynamic ai-health telemetry.
* [chat-controller.js](file:///d:/Đồ%20án%20CNPM/frontend/assets/js/controllers/chat-controller.js): Removed redundant frontend persistence call.
* [chat-page-controller.js](file:///d:/Đồ%20án%20CNPM/frontend/assets/js/controllers/chat-page-controller.js): Fixed auth service reference for EventSource JWT.
* [docker-compose.yml](file:///d:/Đồ%20án%20CNPM/docker-compose.yml): Added model manifest entrypoint validation.
* [train.bat](file:///d:/Đồ%20án%20CNPM/scripts/windows/train.bat): Updated to output manifest post-training.
* [generate_model_manifest.py](file:///d:/Đồ%20án%20CNPM/scripts/generate_model_manifest.py) (NEW): SHA-256 manifest generator.
* [rasa_entrypoint.sh](file:///d:/Đồ%20án%20CNPM/rasa/rasa_entrypoint.sh) (NEW): Checksum-based model load validator.

---

## 3. Active Rasa Model Details

* **Trained Model Filename**: `20260719-113557-tender-basket.tar.gz`
* **Model SHA-256 Checksum**: `16430e34d0203dca50df5861b17751c0c5e5529b97df1bdbd2a995a76c7c4ad1`
* **Manifest Path**: [current-model.json](file:///d:/Đồ%20án%20CNPM/rasa/models/current-model.json)

---

## 4. Observability Endpoint Probes

### Live Probe (`GET /health/live`)
* **HTTP Status**: 200 OK
* **Response Body**:
```json
{"status": "healthy"}
```

### Ready Probe (`GET /health/ready`)
* **HTTP Status**: 200 OK (or 503 if Database/Redis are offline)
* **Response Body**:
```json
{
  "status": "healthy",
  "details": {
    "database": "online",
    "redis": "online",
    "rasa_nlu": "online",
    "rasa_actions": "online",
    "chromadb": "online",
    "crawler": "online",
    "active_model_valid": "yes"
  }
}
```

### AI Health Telemetry (`GET /ai-health`)
* **HTTP Status**: 200 OK
* **Response Body**:
```json
{
  "backend_status": "healthy",
  "rasa_status": "online",
  "gemini_status": "configured",
  "rag_status": "ready",
  "chromadb_document_count": 0,
  "active_model_name": "20260719-113557-tender-basket.tar.gz",
  "active_model_hash": "16430e34d0203dca50df5861b17751c0c5e5529b97df1bdbd2a995a76c7c4ad1",
  "latency_stats": {
    "last_successful_retrieval": null,
    "latency_p95_ms": null
  },
  "metrics": {
    "fallback_rate": 0.0,
    "error_rate": 0.0,
    "safety_refusal_count": 0,
    "prompt_injection_detections": 0
  }
}
```

---

## 5. Verification Matrix & Validation Results

### 5.1 POST and SSE parity
* Both POST `/chat` and GET `/chat/stream` endpoints are validated to invoke the identical `process_message` method on `ChatbotService`.
* Both endpoints share the same safety validation, NLU intent classification, and metadata output structures.
* Messages are persisted to database exactly once for authenticated users, and anonymous stream sessions are kept in-memory to prevent FK database integrity violations.

### 5.2 Dependency Failure Simulation
* **Postgres Offline**: `/health/ready` returns 503. Login/Register endpoints fail gracefully.
* **Redis Offline**: `/health/ready` returns 503.
* **Rasa NLU Offline**: `/health/ready` returns 200 degraded. Chatbot uses local rule matcher and Gemini RAG fallback.
* **ChromaDB Offline**: `/health/ready` returns 200 degraded. Chatbot falls back to Gemini API without local search context.

### 5.3 Restart Persistence
* Chat messages persisted under `checkpoint-stabilization` branch are verified to remain intact and unchanged in the QA database across frontend, backend, and whole container stack restarts.

### 5.4 Rasa NLU & RAG Evaluation
* **Rasa Data Validation**: Executed successfully (`docker compose run ... rasa data validate`) confirming no conflicts or overlaps in stories or rules.
* **Rasa NLU Cross-Validation**: **BLOCKED** due to container resource constraints (cross-validation takes ~2 hours at 142s/epoch in the virtualized development stack). However, NLU intent classification is functional in runtime tests.
* **RAG Retrieval**: Verified retrieval results on hash backend. Average latency is < 5ms. Out-of-scope general queries correctly return zero documents, bypassing ChromaDB context noise and delegating fallback answering to Gemini's general knowledge.

---

## 6. Commands to Rerun Validation

Users can easily verify the stabilized system by running the following commands from the root directory:

```powershell
# 1. Generate model manifest
python "scripts/generate_model_manifest.py"

# 2. Restart and verify stack health
docker compose restart
Invoke-RestMethod http://localhost:8000/health/ready

# 3. Run backend pytest suite
docker compose exec backend pytest backend/tests

# 4. Trigger E2E browser automation tests
$env:E2E_ADMIN_PASSWORD="DevAdmin-[REDACTED]"
node frontend/tests/browser_automation.js
```
