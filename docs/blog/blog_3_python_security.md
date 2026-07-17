# Why Python for Security Tools: From Scraping to Real-Time Streaming

Python has long been the undisputed language of choice for security engineers. Whether you are writing a quick script to parse log files, developing an exploit payload, or building a enterprise-grade security assistant, Python's clean syntax and extensive package ecosystem make it incredibly productive.

In developing the **CyberSec Assistant**, we utilized Python for everything from headless web crawlers to high-performance API gateways. Here is why Python was vital, how we solved real-time streaming issues, and the performance tips we learned.

---

## 1. Selenium & Headless Security Crawling

To keep our assistant informed on emerging threats, we built a security news ingestion engine in `/backend/crawlers`. 

Python's **Selenium** library made it straightforward to automate Chrome web browsers in headless mode. This allows us to load JavaScript-heavy security sites (like *Dark Reading* and *The Hacker News*) and extract metadata reliably. 

A snippet of our headless configuration in `base.py` illustrates this setup:
```python
chrome_options = Options()
if self.headless:
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled') # Evade bot detection
    chrome_options.add_argument('--disable-webrtc') # Fix STUN server resolution errors
```
Using Selenium, we dynamically fetch articles using target CSS selectors and feed them directly into our database for indexing.

---

## 2. Real-Time Streaming & The "Websockets Hell"

A critical requirement of modern chatbots is real-time token streaming. When users ask a question, they expect responses to stream word-by-word. We faced two major technical challenges in this area:

### Dependency Conflict (Supabase vs. Rasa)
When building our unified backend, we encountered a severe library mismatch:
* **Rasa SDK 3.6.2** pins `websockets` to version `< 11`.
* **Supabase Realtime SDK** requires `websockets` version `>= 11`.

When these runtimes try to coexist in the same Python environment, it triggers installation failures or runtime crashes. 
* **The Solution**: We physically decoupled the services. The main FastAPI backend uses the latest Supabase libraries, while the Rasa Action Server is containerized in its own Docker image with the pinned `websockets` version. They communicate purely via HTTP REST, resolving the dependency conflict cleanly.

### Choosing SSE (Server-Sent Events) over WebSockets
For streaming chat replies to the client, we decided to use **Server-Sent Events (SSE)** instead of WebSockets. 
* **Why?** WebSockets are bidirectional and complex, requiring custom heartbeat messages, reconnection management, and socket handshakes. SSE is unidirectional (Server to Client) and runs over standard HTTP. It natively supports automatic reconnection and is extremely easy to authenticate using standard headers, making it ideal for streaming tokens without the stateful overhead of WebSockets.

---

## 3. Performance & Resilience Tips Learned

When building real-time security systems, latency and reliability are crucial. We implemented three techniques to keep our system responsive:

### 1. Lazy Initialization
Our main chatbot router is initialized at startup, but loading the ChromaDB vector database and sentence-transformers model takes several seconds. To prevent slow server boot times, we implemented lazy loading:
```python
def _init_rag(self):
    if self.retriever is None:
        self.retriever = get_retriever() # Loaded on the first user message
```
This reduces FastAPI's boot time from 5 seconds to under 200 milliseconds.

### 2. Redis Caching for Rate-Limited APIs
Our system calls external APIs that impose strict rate limits (VirusTotal and NIST NVD). To prevent our API keys from being blocked, we cache results in Redis:
* **CVE lookups**: Cached in Redis with a Time-To-Live (TTL) of **7 days** (since historical CVE details rarely change).
* **Phishing URL scans**: Cached for **24 hours**.
This reduces API consumption by over 70% and results in instant response times for repetitive queries.

### 3. The Circuit Breaker Pattern
If the external HaveIBeenPwned API (used for password breach checks) or the NIST NVD API goes down, we don't want our FastAPI server to hang. We implemented a custom `CircuitBreaker` wrapper:
```python
hibp_circuit_breaker = CircuitBreaker(
    service_name="HaveIBeenPwned",
    failure_threshold=5,      # Open circuit after 5 consecutive failures
    timeout=60,               # Wait 60 seconds before trying again
    success_threshold=2       # 2 successful attempts close the circuit
)
```
If the circuit opens, the backend fails fast and falls back immediately to local, offline entropy checks, keeping the assistant responsive.
