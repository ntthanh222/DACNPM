# Remaining Limitations

The following minor limitations remain in the current stabilization environment:

1. **Lightweight Hash Embeddings**:
   * `EMBEDDING_BACKEND` is configured as `hash` in local stack configuration. While this has low CPU overhead and requires zero model download time on startup, it relies on static token hashing which may result in less robust semantic alignment compared to dense vector models (e.g., `sentence-transformers`).

2. **Unused Rasa Utterances**:
   * Several Rasa response templates (e.g. `utter_assess_vulnerability`, `utter_no_password`) are declared in `domain.yml` but not referenced in rules or stories. These generate standard warnings during validation but do not cause failures.

3. **In-Memory Fallback Persistence**:
   * If connection to Supabase fails, the system switches to in-memory history fallback. This preserves user sessions during active runtime, but logs stored in-memory will not persist across container restarts.

4. **Playwright Navigation Aborts**:
   * Rapidly clicking through pages in browser automation can cause outstanding fetch requests to abort (yielding `net::ERR_ABORTED` in console). This is standard browser behavior and has no impact on system functionality.
