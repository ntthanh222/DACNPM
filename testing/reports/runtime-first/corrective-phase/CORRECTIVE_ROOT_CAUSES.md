# Corrective Phase Root Causes & Remediation

This report outlines the root causes, reproduction cases, and remediation fixes for the three primary defects audited during the corrective stabilization phase.

---

## 1. Chatbot Routing Preemption

### Symptom
Querying tools (e.g. `"Kiểm tra URL https://example.com"`) resulted in a local pattern match for `clarification` (confidence `0.90`) rather than being classified correctly by the active Rasa NLU model (`check_phishing` at `1.00` confidence).

### Root Cause
In `ChatbotService.process_message`, the local pattern matcher `_pattern_matching_fallback` was run first. If it matched anything other than a handful of intents, it returned a hardcoded fallback response immediately, bypassing the Rasa NLU model entirely.

### Remediation
Refactored `process_message` to run safety policy checks first. If the message is safe, it calls the Rasa NLU classifier `/model/parse` immediately. Supplementary local pattern heuristics are only called *after* Rasa classification as a fallback if the NLU confidence is low, or if the Rasa service is offline.

---

## 2. Response Metadata Stripping

### Symptom
FastAPI POST `/chat` and SSE `/chat/stream` endpoints did not return the metadata fields `source`, `fallback_used`, `rag_attempted`, `rag_enabled`, `rag_documents`, `request_id`, `model_name`, or `persistence_status`.

### Root Cause
* **POST API**: The `ChatResponse` schema did not define these fields, and the controller mapped the response manually to a limited set of attributes.
* **SSE Stream**: The generator yielded basic data chunks without metadata and omitted metadata from the stream completion signals.

### Remediation
1. Extended `ChatResponse` and added the `RetrievedDocument` sub-schema in `backend/api/chatbot.py`.
2. Updated the `/chat` POST controller to serialize all metadata fields.
3. Updated `/chat/stream` to yield explicit `metadata` and `complete` SSE events containing the rich metadata dictionary.
4. Updated the frontend `chat-page-controller.js` to register listeners for these custom SSE event names.

---

## 3. Unit Test Regressions

### Symptom
Pytest returned two failures on `test_anonymous_processing_does_not_route_through_authenticated_rasa` and `test_rasa_generic_response_cannot_override_safety_policy`.
* **Error**: `AttributeError: 'ChatbotService' object has no attribute '_get_rasa_response'`

### Root Cause
The refactored `ChatbotService` removed the private `_get_rasa_response` method, but the test suite continued to mock and call it.

### Remediation
Rewrote the test suite to target the public `process_message` method and assert correct black-box behavior (anonymous persistence skipping and safety block preemption) instead of relying on private helper details.
