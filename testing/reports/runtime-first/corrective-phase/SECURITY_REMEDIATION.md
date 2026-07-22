# Security Remediation Report

This document outlines the security vulnerabilities discovered during the corrective stabilization phase and the steps taken to mitigate them.

## 1. Hardcoded Credentials

### Vulnerability
Hardcoded development credentials were found in `hd.md`, specifically the `admin` password. Including plaintext passwords in source control, even for development, is a critical security risk.

### Remediation
- **Redacted**: Replaced the plaintext password in `hd.md` with a placeholder `[REDACTED_DEV_ADMIN_PASSWORD]`.
- **Environment Driven**: Verified that the system relies on environment variables (`E2E_ADMIN_PASSWORD`) instead of hardcoded strings for testing and deployment environments.
- **Rule Enforcement**: Instructed the agent to adhere strictly to the rule: "Không hiển thị hoặc ghi lại password, JWT, API key hay secret."

## 2. Chatbot Prompt Injection & Safety

### Vulnerability
The original `process_message` logic in `chatbot_service.py` was vulnerable to prompt injection bypass if the NLU classification occurred before the safety guardrail evaluation, or if the safety logic was improperly short-circuited.

### Remediation
- **Preemption Implemented**: Refactored `process_message` to ensure `policy_guard` evaluates the input *before* Rasa classification.
- **Strict Short-circuiting**: If `policy_guard` detects a violation, the request is instantly halted and a `safety_violation` response is returned. Rasa and LLM fallback are bypassed entirely.
- **Validation**: Added and passed unit tests (`test_chatbot_policy_guard.py`) confirming this preemption matrix.
