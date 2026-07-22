# RAG Benchmark Report

This document reports the baseline metrics and evaluation details for local RAG retrieval.

## 1. Environment Parameters
* **Embedding Backend**: `hash`
* **Collection Name**: `security_knowledge`
* **Total Chunks Indexed**: 0 (no documents ingested in local ChromaDB container)
* **Ingestion and Query Parity**: Verified. Both use the deterministic token hash algorithm.
* **Vector Dimension**: 128 (default)

## 2. Benchmark Queries
Due to the collection document count being 0, all RAG queries return exactly 0 documents. There is no expected ground truth or golden dataset pre-loaded in the local ChromaDB database.

| Query | Top-K Retrieved | Duplicate Chunks | Docs Below Threshold | Recall@K | Expected Document Found |
| :--- | :--- | :--- | :--- | :--- | :--- |
| "Giải thích cách harden Ubuntu server" | 0 | 0 | 0 | 0.00 | **NOT VERIFIED** |
| "Cho tôi tin tức an ninh mạng" | 0 | 0 | 0 | 0.00 | **NOT VERIFIED** |

## 3. Audit Verdict
**NOT VERIFIED** / **BLOCKED** due to the absence of pre-indexed documents and benchmark evaluation sets. RAG context retrieval logic is syntactically present and fallback checks operate cleanly, but semantic quality cannot be benchmarked under zero-state collection limits.
