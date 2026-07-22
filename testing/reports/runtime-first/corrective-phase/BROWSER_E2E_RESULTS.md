# BROWSER E2E RESULTS

**Date**: 2026-07-19
**Phase**: CORRECTIVE RUNTIME STABILIZATION
**Methodology**: PROOF-ONLY E2E Browser Testing using Playwright over Chrome CDP (`ws://127.0.0.1:9222`)
**Status**: PASSED

## Execution Summary

10 specific browser flows were verified using a real Chrome instance connecting to the Docker-hosted frontend (`http://localhost:3000`). All assertions were met, and real API integrations were validated without mocks.

| Flow | Viewport | UI result | Network result | Console result | Evidence | Verdict |
| ---- | -------- | --------- | -------------- | -------------- | -------- | ------- |
| 1. Authentication | Desktop | Shows correct error for wrong pass, successful redirect on correct pass | No JWT in URL, JWT in Authorization header | No unhandled errors | `login-success.png` | PASS |
| 2. Dashboard | Desktop | Dashboard loads completely, charts rendered without spinners | Stats APIs return real JSON responses, no infinite loop | No JS or page errors | `dashboard.png` | PASS |
| 3. Chat Greeting | Desktop | "Xin chào" appears, response displays correctly without duplicates | `intent: greet` correctly extracted, valid response payload | No HTTP 500s | `chat-greeting.png` | PASS |
| 4. URL Phishing | Desktop | Correctly displays Phishing validation response | `intent: check_phishing` routed to Rasa Action server | Confidence parsed, no duplicates | `chat-url-check.png` | PASS |
| 5. CVE Lookup | Desktop | Fallback requested missing parameters cleanly | `intent: lookup_cve` recognized successfully | No stack traces leaked | N/A | PASS |
| 6. RAG Runtime | Desktop | UI streams full response without crashing | `source: llm_rag` and metadata present | No 500 errors | `chat-rag.png` | PASS |
| 7. Authenticated SSE | Desktop | Streaming finishes and loading closes automatically | `stream-ticket` granted, valid SSE chunks received | Stream fully parsed | `chat-sse-complete.png` | PASS |
| 8. Persistence | Desktop | Reload retains marker exact one time | No extra save requests initiated on refresh | No errors on mount | `chat-history-after-refresh.png` | PASS |
| 9. Authorization | Desktop | Admin accesses page, normal user forbidden/redirected | 401/403 returned appropriately | No unauthorized API leaks | `admin-allowed.png`, `admin-forbidden.png` | PASS |
| 10. Responsive Viewports | Mobile | Chat resizes without layout breaks | Standard APIs continue working | No layout errors | `mobile-chat.png` | PASS |

## Corrective Actions Taken
- Resolved an Nginx proxy misconfiguration where the IP address for the `backend` upstream was incorrectly cached, leading to `111 Connection Refused` when the backend container restarted.
- Restarted the `frontend` container, which fixed API routing.

**Conclusion**: CORRECTIVE RUNTIME VALIDATION COMPLETED
