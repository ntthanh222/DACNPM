# Integrating AI with Security Data: RAG & ChromaDB in Practice

Large Language Models (LLMs) are exceptionally good at generating fluent text, but they suffer from a well-known vulnerability: **hallucinations**. In the realm of cybersecurity, a hallucinated command or an incorrect CVE severity score isn't just a minor mistake; it can lead to misconfigured firewalls, ignored alerts, or system breaches.

To ground our **CyberSec Assistant** in reality, we implemented a custom **Retrieval-Augmented Generation (RAG)** pipeline. By combining Google's Gemini API with a local vector database, we ensured that the assistant responds based on verified security knowledge, dynamic news feeds, and structured vulnerability catalogs. 

Here is how we set up our RAG pipeline, configured ChromaDB, and solved critical accuracy and compatibility challenges.

---

## The Challenge of RAG with Cybersec Data

Cybersecurity knowledge bases are highly heterogeneous. Our data includes:
* **Structured CVE records** (IDs, CVSS scores, vulnerability descriptions).
* **Semi-structured security news articles** (titles, published dates, source URLs).
* **Unstructured incident response procedures** (multi-step text instructions).
* **Short, actionable security tips** (e.g., strong password criteria, phishing signs).

In traditional RAG pipelines, chunking these documents without care leads to fragmented contexts. If a CVE description is split mid-sentence, the LLM might miss critical patch instructions. Similarly, if retrieved context contains irrelevant news, the LLM's response quality degrades due to "noise."

---

## Vector Database Setup: ChromaDB

For our vector storage, we chose **ChromaDB** due to its simplicity, speed, and capability to run embedded within our FastAPI process. 

### 1. Persistence & Metric Selection
We initialized ChromaDB using the `PersistentClient` to persist index data across container restarts:
```python
self.client = chromadb.PersistentClient(path=self.persist_directory)
self.collection = self.client.get_or_create_collection(
    name="security_knowledge",
    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
)
```
Choosing the **cosine similarity** space (`hnsw:space: cosine`) ensures that vector comparisons focus on semantic direction and document content rather than text length, which is crucial since our articles and CVE snippets vary in length.

### 2. Multi-Tier Embedding Strategy
Generating high-quality embeddings is key to semantic matching. In `embedding_service.py`, we designed a robust, multi-tier embedding generation architecture:
* **Primary Backend (`sentence-transformers`)**: We use `paraphrase-multilingual-mpnet-base-v2`. This model supports both English and Vietnamese, which is vital because our crawled news and local tips are bilingual.
* **Fallback Backend (`SimpleHashEmbedding`)**: Standard ML packages like `sentence-transformers` and `torch` can be difficult to run in lightweight runtimes, CI pipelines, or future versions of Python (e.g., Python 3.14). To solve this, we implemented a lightweight, pure-Python fallback using character n-gram hashing and vector normalization:
  ```python
  # Extracts character n-grams (3 to 5 characters) and hashes them to a 384-dimensional vector.
  hash_bytes = self.hash_fn(ngram.encode()).digest()
  idx = int.from_bytes(hash_bytes[:4], byteorder='big') % self.dim
  vector[idx] += 1
  ```
  While simple, this n-gram hashing approach enables baseline semantic search (TF-IDF style similarity) without any heavy machine learning dependencies.

---

## Achieving Accuracy and Minimizing Noise

Simply retrieving the top $K$ documents from a vector search and stuffing them into the prompt is not enough. We implemented three techniques to maximize answer accuracy:

### 1. Similarity Score Filtering
ChromaDB returns cosine distance. We convert this distance into a normalized similarity score:
$$\text{Similarity} = 1.0 - \text{Distance}$$
We then enforce a minimum score threshold:
```python
self.min_score = 0.5
filtered_results = [r for r in results if (1.0 - r.get('distance', 1.0)) >= self.min_score]
```
If ChromaDB returns documents with low similarity, they are filtered out. This ensures that when a user asks an out-of-scope question, the assistant doesn't try to answer using loosely related news articles.

### 2. Context Boundary Formatting
To help the LLM distinguish between separate sources, we format the retrieved context with structured headers:
```text
[CVE 1 - CVE-2024-3094 (CRITICAL)]
Severity: CRITICAL
CVSS Score: 10.0
Description: Backdoor in upstream xz-utils...
-----------------------
[Mẹo bảo mật 1 - CVE Management]
Theo dõi thường xuyên các CVE mới. Đánh giá severity để ưu tiên patch...
```
This structured schema prevents the LLM from merging unrelated facts, allowing it to cite the source explicitly in its final answer (e.g., *"Theo tin tức từ VnExpress..."*).

### 3. Intent Routing Fallback
We don't feed everything through RAG. Standard tool queries (like checking a password score or evaluating a phishing link) are handled by deterministic local Python scripts. RAG and LLM reasoning are reserved for informational queries where synthesising knowledge is necessary.

By grounding Gemini with filtered, structured ChromaDB context, we achieved accurate, data-driven security assistance tailored to Vietnamese security environments.
