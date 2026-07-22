# Independent Runtime Audit Report

## 1. Executive Summary
This independent runtime audit evaluates the stabilization of the **CyberSec Assistant** application. This is a **PROOF-ONLY** audit carried out by validating container configurations, logs, database state, API endpoints, and test suites.

* **Audit Status**: **PARTIALLY PASSED / REGRESSIONS FOUND**
* **Active Rasa Model**: `20260719-113557-tender-basket.tar.gz`
* **Rasa Model SHA-256 Checksum**: `16430e34d0203dca50df5861b17751c0c5e5529b97df1bdbd2a995a76c7c4ad1`

While several core features (health checks, model manifest validation, stream ticket auth) are verified as successful, we identified **two critical regressions** and **one specification mismatch** that require attention.

---

## 2. Identified Defect & Regressions

### 2.1 Unit Test regressions
The previous refactoring removed `_get_rasa_response` from `ChatbotService` but failed to update corresponding unit tests. Consequently, running pytest inside the backend container yields **2 failures out of 170 tests**:
1. `backend/tests/test_chatbot_fallback_knowledge.py::test_anonymous_processing_does_not_route_through_authenticated_rasa`
2. `backend/tests/test_chatbot_policy_guard.py::test_rasa_generic_response_cannot_override_safety_policy`
* **Symptom**: `AttributeError: 'ChatbotService' object has no attribute '_get_rasa_response'`

### 2.2 Response Metadata Mismatch (FastAPI Schema Stripping)
In `/api/chatbot/chat` and `/api/chatbot/chat/stream`, the API endpoints do **not** return the metadata fields `source`, `fallback_used`, `rag_enabled`, `rag_documents`, `request_id`, or `model_name` in the JSON payload.
* **Root Cause**: The FastAPI POST endpoint is decorated with `response_model=ChatResponse`, and both endpoints manually strip these fields from the returned schemas. As a result, frontend and external clients cannot see or consume these fields, contradicting the specification in Giai đoạn 2.2.

### 2.3 Pattern Preemption in Routing
Local fallback rules preempt NLU routing. For example, the query `"Kiểm tra URL https://example.com"` is intercepted by substring checks in `_pattern_matching_fallback` and routed as `clarification` (0.90) without ever calling the Rasa NLU model (which classifies it correctly as `check_phishing` at 1.00).

---

## 3. Redacted Credentials Check

A codebase search for secrets revealed the following:
* **Code References**:
  * [hd.md](file:///d:/Đồ%20án%20CNPM/hd.md#L97): Contains local dev password `Password: DevAdmin-[REDACTED]`
  * [hd.md](file:///d:/Đồ%20án%20CNPM/hd.md#L371): Contains local dev password `Password: DevAdmin-[REDACTED]`
  * `backend/ADMIN_CREDENTIALS.txt`: Local file (gitignored).
* **Severity**: **HIGH (Security Warning)**. While these credentials are documented for local development, they must be rotated and never deployed in a public or staging environment.

---

## 4. Capability-based Verdicts

* **Authentication**: **PASS**. Verified stream ticket auth and JWT access guard.
* **Authorization**: **PASS**. Role-based access verified.
* **Dashboard**: **PASS**. Analytics and stats load successfully.
* **Chat POST**: **PARTIAL**. Chat works, but metadata fields are missing from HTTP response.
* **Chat SSE**: **PARTIAL**. Chat streams, but metadata fields are missing from EventSource response.
* **Rasa NLU**: **PASS**. Verifies manifest on startup; NLU classifications are functional.
* **Rasa Actions**: **PASS**. Handles custom action routing when online.
* **RAG**: **NOT VERIFIED / BLOCKED**. Zero documents pre-loaded in ChromaDB database.
* **LLM**: **PASS**. Gemini API integrations execute successfully.
* **Persistence**: **PASS**. Authenticated chat messages are persisted exactly once.
* **Restart Recovery**: **PASS**. Models and records persist across container restarts.
* **Dependency Failure**: **PASS**. Returns 503 on Redis offline, and degraded on optional ones.
* **Health / Observability**: **PASS**. Truthful live/ready probes and dynamic telemetry.
* **Security**: **WARN**. Local developer credential documented in `hd.md`.
