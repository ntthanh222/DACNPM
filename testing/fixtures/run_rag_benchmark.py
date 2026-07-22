import os
import json
import asyncio
import sys
from pathlib import Path

# Insert backend to sys.path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.rag.vector_store import VectorStore
from backend.rag.embedding_service import get_embedding_service
from backend.rag.retriever import DocumentRetriever

async def main():
    print("=== RAG BENCHMARK EVALUATOR ===")
    
    # 1. Load the corpus documents
    corpus_dir = Path(__file__).parent / "rag_corpus"
    documents = []
    
    doc_id_to_content = {}
    for filepath in corpus_dir.glob("*.txt"):
        doc_id = filepath.stem
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        doc_id_to_content[doc_id] = content
        
        # Split into sentences to ensure we have >= 30 chunks
        paragraphs = [p.strip() + "." for p in content.split('. ') if len(p.strip()) > 10]
        
        for i, p in enumerate(paragraphs):
            chunk_text = f"Title: {doc_id}\nContent: {p}"
            documents.append({
                "id": f"{doc_id}_chunk_{i}",
                "text": chunk_text,
                "metadata": {
                    "source": f"testing/fixtures/rag_corpus/{filepath.name}",
                    "title": doc_id,
                    "type": "procedure"
                }
            })
            
    print(f"Loaded {len(documents)} corpus chunks.")

    # 2. Re-initialize vector store collection for QA
    vector_store = VectorStore(collection_name="security_knowledge_qa_semantic_v1")
    
    # Reset/Clear collection to ensure clean state
    try:
        vector_store.client.delete_collection(name="security_knowledge_qa_semantic_v1")
        print("Cleared existing security_knowledge_qa_semantic_v1 collection.")
    except Exception:
        pass
        
    # Recreate and add documents
    vector_store = VectorStore(collection_name="security_knowledge_qa_semantic_v1")
    added = vector_store.add_documents(documents)
    print(f"Added {added} documents to security_knowledge_qa_semantic_v1.")

    # 3. Load Golden Queries
    golden_queries_path = Path(__file__).parent / "rag_golden_queries.json"
    with open(golden_queries_path, "r", encoding="utf-8") as f:
        queries = json.load(f)
    print(f"Loaded {len(queries)} golden queries.")

    # 4. Run Benchmark
    import backend.rag.vector_store
    backend.rag.vector_store._vector_store = vector_store
    retriever = DocumentRetriever()
    
    mrr_sum = 0
    recall_1_sum = 0
    recall_3_sum = 0
    empty_retrievals = 0
    duplicate_retrievals = 0
    irrelevant_retrievals = 0
    
    results_table = []
    
    for q in queries:
        query_text = q["query"]
        expected_ids = q["expected_document_ids"]
        must_not = q["must_not_retrieve"]
        
        # Retrieve n_results=3
        retrieved = retriever.retrieve(query_text, n_results=3)
        retrieved_ids = [doc.get("metadata", {}).get("title") for doc in retrieved]
        
        # Compute Recall@1 and Recall@3
        r1 = 1.0 if any(eid in retrieved_ids[:1] for eid in expected_ids) else 0.0
        r3 = 1.0 if any(eid in retrieved_ids[:3] for eid in expected_ids) else 0.0
        
        # Compute MRR
        mrr = 0.0
        for rank, rid in enumerate(retrieved_ids, 1):
            if rid in expected_ids:
                mrr = 1.0 / rank
                break
                
        # Metrics aggregations
        mrr_sum += mrr
        recall_1_sum += r1
        recall_3_sum += r3
        
        if len(retrieved) == 0:
            empty_retrievals += 1
            
        # Check duplicates
        if len(retrieved_ids) != len(set(retrieved_ids)):
            duplicate_retrievals += 1
            
        # Check must_not list
        if any(mn in retrieved_ids for mn in must_not):
            irrelevant_retrievals += 1
            
        results_table.append({
            "query": query_text,
            "expected_ids": expected_ids,
            "retrieved_ids": retrieved_ids,
            "retrieved_details": retrieved,
            "recall_1": r1,
            "recall_3": r3,
            "mrr": mrr
        })
        
    num_queries = len(queries)
    avg_recall_1 = recall_1_sum / num_queries
    avg_recall_3 = recall_3_sum / num_queries
    avg_mrr = mrr_sum / num_queries
    
    print(f"Recall@1: {avg_recall_1:.2f}")
    print(f"Recall@3: {avg_recall_3:.2f}")
    print(f"MRR: {avg_mrr:.2f}")
    
    os.makedirs(str(Path(__file__).parent.parent / "reports" / "runtime-first" / "corrective-phase"), exist_ok=True)
    report_path = str(Path(__file__).parent.parent / "reports" / "runtime-first" / "corrective-phase" / "RAG_EVALUATION.md")
    diag_path = str(Path(__file__).parent.parent / "reports" / "runtime-first" / "corrective-phase" / "RAG_DIAGNOSTICS.md")
    
    embedding_service = get_embedding_service()
    info = embedding_service.get_info()
    
    with open(diag_path, "w", encoding="utf-8") as f:
        f.write("# RAG Diagnostics Report\n\n")
        f.write(f"- Collection Name: security_knowledge_qa_semantic_v1\n")
        f.write(f"- Embedding Backend: {info.get('backend')}\n")
        f.write(f"- Vector Dimension: {info.get('embedding_dim')}\n")
        f.write(f"- Chunk Count (Total): {len(documents)}\n")
        
        f.write("\n## Queries Diagnostics\n\n")
        for q in results_table:
            f.write(f"### Query: {q['query']}\n")
            f.write(f"- Expected IDs: {q['expected_ids']}\n")
            f.write(f"- Actual Top Retrieved IDs: {q['retrieved_ids']}\n")
            f.write("- Detailed Retrieval:\n")
            for i, doc in enumerate(q['retrieved_details']):
                dist = doc.get('distance', 'N/A')
                sim = doc.get('similarity', 'N/A')
                title = doc.get('metadata', {}).get('title', 'Unknown')
                doc_id = doc.get('id', 'Unknown')
                f.write(f"  - Rank {i+1}: ID={doc_id}, Title={title}, Distance={dist}, Score={sim}\n")
            f.write("\n")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# RAG System Evaluation\n\n")
        f.write("## 1. Summary Metrics\n")
        f.write(f"* **Total Queries**: {len(queries)}\n")
        f.write(f"* **Embedding Backend**: {embedding_service.get_info()['backend']}\n\n")
        
        f.write("## Overall Metrics\n\n")
        f.write(f"| Metric | Value | Target |\n")
        f.write(f"| :--- | :--- | :--- |\n")
        f.write(f"| **Recall@1** | {avg_recall_1:.4f} | - |\n")
        f.write(f"| **Recall@3** | {avg_recall_3:.4f} | >= 0.8000 |\n")
        f.write(f"| **MRR** | {avg_mrr:.4f} | >= 0.6500 |\n")
        f.write(f"| **Empty Retrieval Rate** | {empty_retrievals / num_queries:.4f} | 0.0000 |\n")
        f.write(f"| **Duplicate Retrieval Rate** | {duplicate_retrievals / num_queries:.4f} | 0.0000 |\n")
        f.write(f"| **Irrelevant Retrieval Rate** | {irrelevant_retrievals / num_queries:.4f} | 0.0000 |\n\n")
        
        f.write("## Detailed Query Results\n\n")
        f.write("| Query | Expected ID | Retrieved IDs | Recall@3 | MRR |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for res in results_table:
            f.write(f"| {res['query']} | `{res['expected_ids']}` | `{res['retrieved_ids']}` | {res['recall_3']:.2f} | {res['mrr']:.2f} |\n")
            
    print(f"Report written to {report_path}")

if __name__ == "__main__":
    asyncio.run(main())
