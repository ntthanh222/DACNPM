# Building CyberSec Assistant: My Journey, Tech Choices, and Engineering Lessons

In recent years, the intersection of cybersecurity and artificial intelligence has opened up new frontiers for threat intelligence, threat assessment, and security automation. Building an AI-driven security companion that can intelligently analyze vulnerabilities, scan URLs, evaluate password strength, and keep security teams updated with real-time news is a thrilling engineering endeavor. Today, I want to share my journey in building **CyberSec Assistant**, the technical choices that shaped its architecture, the challenges we overcame, and the lessons we learned along the way.

---

## The Tech Stack: Finding the Perfect Balance

When designing the system, we wanted to avoid the pitfalls of a monolithic chatbot that relies entirely on a third-party LLM for everything. Security operations require speed, deterministic tools, local compliance, and intelligent reasoning. To achieve this balance, we chose three core technologies:

1. **FastAPI (The Gateway & Business Layer)**: For our backend, Python's FastAPI was an obvious choice. Its native asynchronous IO (`async/await`) allows us to handle multiple concurrent API calls and streaming responses with minimal overhead. Furthermore, FastAPI's automatic OpenAPI/Swagger documentation speeds up developer integration, while Pydantic guarantees request validation—a critical factor when dealing with untrusted user inputs.
2. **Rasa Open Source (The Deterministic Router)**: Rasa acts as our local intent classifier and dialogue manager. Rather than sending basic greetings, password evaluations, or specific tool commands to an expensive cloud LLM, Rasa parses the intents offline. This keeps our system extremely secure, fast, and compliant with data privacy regulations since simple queries never leave our infrastructure.
3. **Google Gemini 2.5 Flash (The Neural Brain)**: For open-ended queries (e.g., *"How do I secure an Apache server?"*), a standard dialogue tree falls short. We integrated Gemini via the modern `google-genai` SDK. Gemini provides deep security reasoning, fluent Vietnamese language understanding, and a massive context window ideal for processing retrieved security documents.

---

## Overcoming Engineering Roadblocks

Every project has its fair share of integration pain. Here are the three most significant challenges we faced and how we solved them:

### 1. The Python/Rasa Dependency Hell
Rasa 3.6.20 relies on several compiled C-extensions (like older versions of `uvloop` and `ruamel.yaml.clib`) that are notoriously unstable or refuse to compile on Python 3.12+ (which many of us run on our host OS). 
* **The Solution**: We fully containerized the Rasa engine and Rasa Action Server using Docker. By binding our local config, model, and data directories via Docker volumes, we isolated the Rasa environment on a stable Python 3.10 image. Developers can now train and run Rasa using simple Docker Compose commands without installing complex C-compilers locally.

### 2. Supabase Cloud Database Namespace Clashes
During our initial database migrations to Supabase Cloud, we ran into a critical SQL bug where our `INSERT INTO users` queries were failing with a `column password_hash does not exist` error. We discovered that because Supabase uses a dedicated internal `auth.users` schema, our unqualified queries were defaulting to their schema instead of our custom business schema.
* **The Solution**: We rewritten our migrations to explicitly target the `public` schema (`INSERT INTO public.users ...`). We also made our SQL scripts fully idempotent using `CREATE TABLE IF NOT EXISTS` and check constraints so that database setups can be repeated safely.

### 3. Implementing the Hybrid Chatbot Router
A major challenge was preventing LLM hallucinations when users asked for deterministic operations (like scanning a password or lookup up a CVE). 
* **The Solution**: We built a hybrid orchestration layer. When a query is received, it is first evaluated by Rasa. If Rasa detects a standard security action (e.g., `check_phishing`, `lookup_cve`) with high confidence (`> 0.7`), the router delegates the request to the deterministic local action scripts. Otherwise, it routes to Gemini with Retrieval-Augmented Generation (RAG) and conversational memory. This reduced false responses and unnecessary fallbacks.

---

## Key Lessons Learned

Building the CyberSec Assistant taught us several invaluable software engineering lessons:

* **Containerize Early**: If your stack mixes legacy NLU packages and modern generative AI libraries, isolate them using Docker immediately to avoid dependency collision.
* **Explicit Schema Declarations**: In managed cloud databases, never rely on default schemas. Always prefix your tables with `public.` or your custom namespace.
* **Control LLM Boundaries**: Generative AI is powerful, but it should not be the entry point for deterministic workflows. Combine traditional rule-based/intent classifiers with LLMs to build reliable, production-grade applications.
