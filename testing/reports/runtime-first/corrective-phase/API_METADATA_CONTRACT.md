# API Metadata Contract

This document defines the schema and contract for the API responses, specifically for the Chatbot streaming endpoints.

## Server-Sent Events (SSE) Stream Contract

Endpoint: `POST /api/v1/chatbot/stream` (and related streaming endpoints)

The backend streams responses using standard Server-Sent Events (SSE). Each event consists of an `event` type and `data` payload.

### Event Types

1. **`event: metadata`**
   - **Purpose**: Sent immediately after message processing starts. Contains routing and intent metadata before the text response begins streaming.
   - **Payload Schema**:
     ```json
     {
       "intent": "string (e.g., 'cve_lookup', 'greeting')",
       "confidence": "float (0.0 to 1.0)",
       "source": "string ('rasa', 'policy_guard', 'fallback', 'llm')",
       "action_taken": "string (e.g., 'search_cve', 'default_fallback')",
       "security_context": {
         "risk_level": "string",
         "requires_auth": "boolean"
       }
     }
     ```

2. **`event: chunk`**
   - **Purpose**: Streams the actual text content of the response.
   - **Payload Schema**: Raw string chunk of the response text.

3. **`event: complete`**
   - **Purpose**: Signals the end of the stream.
   - **Payload Schema**: `[DONE]` or a summary object.

### Example Stream

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: metadata
data: {"intent": "cve_lookup", "confidence": 0.95, "source": "rasa", "action_taken": "search_cve"}

event: chunk
data: CVE-2021-44228 is a critical vulnerability...

event: chunk
data:  found in Log4j.

event: complete
data: [DONE]
```
