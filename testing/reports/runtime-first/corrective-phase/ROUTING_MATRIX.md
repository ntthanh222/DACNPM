# Black-Box API Routing Matrix Contract

This document summarizes the expected routing matrix for the `process_message` endpoint based on input conditions.

## Expected Routing Priorities

1. **Safety Policy (Highest Priority)**
   - **Condition**: Input violates the safety policy (e.g., prompt injection, toxic content).
   - **Action**: Routing halts. `policy_guard` is invoked.
   - **Response Intent**: `safety_violation`

2. **Rasa Classification**
   - **Condition**: Rasa NLU model classifies the intent with high confidence (`> 0.6` by default).
   - **Action**: Route to the corresponding Rasa action via webhook.
   - **Response Intent**: The Rasa intent (e.g., `cve_lookup`, `threat_intelligence`, `network_scan`).

3. **Local Fallback (LLM Generation)**
   - **Condition**: Rasa NLU returns `nlu_fallback` or confidence is below threshold, and no safety violation.
   - **Action**: Route to local LLM with RAG context.
   - **Response Intent**: `general_inquiry` or `fallback`

## Test Evidence

Refer to the unit test `test_chatbot_policy_guard.py` and `test_chatbot_fallback_knowledge.py` which validate this exact preemption logic.
