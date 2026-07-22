# Root Cause Matrix

This document maps all identified runtime defects in the **CyberSec Assistant** system to their root causes and verified fixes.

| Issue | Replay/Symptom | Root Cause | Fix |
| :--- | :--- | :--- | :--- |
| **Stale Rasa Model Loading** | Rasa container loads outdated model `20260714-...` instead of newly trained model `20260719-...` | Startup command used a blind wildcard `find` search which resolved the first directory entry rather than tracking the latest model | Created `generate_model_manifest.py` to write `current-model.json` with a SHA-256 checksum, and wrote `rasa_entrypoint.sh` to validate this checksum on startup |
| **Double Persistence Bug** | Duplicate chat messages saved in database for authenticated chats | Frontend `chat-controller.js` called `saveChatToDatabase` in addition to the backend orchestrator performing persistence during `process_message` | Removed the frontend `saveChatToDatabase` call in `chat-controller.js`, delegating authoritative persistence to the backend |
| **Anonymous Session SSE Bug** | Anonymous SSE stream requests routed through the authenticated Rasa NLU database path | SSE `/chat/stream` mapped the anonymous `x-session-id` UUID as the primary `user_id` parameter to the orchestrator | Separated `user_id` and `session_id` parameters in `process_message` signature. Kept `user_id` as `None` for anonymous stream queries |
| **Frontend Streaming Auth Bypass** | Authenticated users connected to SSE stream anonymously | `chat-page-controller.js` checked for `window.authService` (which is undefined) instead of `window.auth` | Corrected the object reference to `window.auth` to obtain JWT stream ticket successfully |
