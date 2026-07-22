# Baseline State Before Fixes

## 1. Git Status & Docker Compose Checkpoint

* **Git Branch**: `checkpoint-stabilization`
* **Modified Files**:
  * `.dockerignore`
  * `backend/Dockerfile`
  * `backend/api/chatbot.py`
  * `backend/api/system.py`
  * `backend/config/settings.py`
  * `backend/services/chatbot_service.py`
  * `backend/tests/test_system_regressions.py`
  * `docker-compose.yml`
  * `frontend/assets/js/controllers/chat-controller.js`
  * `frontend/assets/js/controllers/chat-page-controller.js`
  * `hd.md`
  * `scripts/windows/start.bat`
  * `scripts/windows/train.bat`

* **Running Stack Services**:
  * `backend-1` (healthy, port 8000)
  * `chromadb-1` (running, port 8000/tcp internal)
  * `crawler-1` (healthy, port 8002)
  * `frontend-1` (healthy, port 3000)
  * `rasa-1` (healthy, port 15005)
  * `rasa-actions-1` (healthy, port 15055)
  * `redis-1` (healthy, port 6379)
  * `grafana-1`, `prometheus-1`, `redis-commander-1` (running)

---

## 2. Reproduction of Known Failures

### 2.1 Pytest Suite Regressions
```text
FAILED backend/tests/test_chatbot_fallback_knowledge.py::test_anonymous_processing_does_not_route_through_authenticated_rasa
AttributeError: <backend.services.chatbot_service.ChatbotService object at 0x75aa91b4a410> has no attribute '_get_rasa_response'

FAILED backend/tests/test_chatbot_policy_guard.py::test_rasa_generic_response_cannot_override_safety_policy
AttributeError: 'ChatbotService' object has no attribute '_get_rasa_response'
```

### 2.2 Response Metadata Stripping
* **POST `/api/chatbot/chat` Response**:
  ```json
  {
    "response": "...",
    "intent": "check_password",
    "confidence": 0.9998737573623657,
    "suggested_actions": null
  }
  ```
  * *Stripped Fields*: `source`, `fallback_used`, `rag_enabled`, `rag_documents`, `request_id`, `model_name`.
* **SSE `/api/chatbot/chat/stream` Response**:
  * Only sends text chunk events. The metadata event contains:
  ```json
  {"type": "metadata", "intent": "check_password", "confidence": 0.9998737573623657, "suggested_actions": []}
  ```
  * *Stripped Fields*: `source`, `fallback_used`, `rag_enabled`, `rag_documents`, `request_id`, `model_name`.

### 2.3 Routing Preemption (URL query)
* **Query**: `"Kiểm tra URL https://example.com"`
* **Expected behavior**: Call Rasa NLU `/model/parse` to classify as `check_phishing`.
* **Actual behavior**: Preempted by local pattern matcher returning `clarification` (intent) and confidence `0.90` from memory, bypasses Rasa model completely.
