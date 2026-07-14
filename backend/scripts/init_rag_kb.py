#!/usr/bin/env python3
"""
Initialize RAG knowledge base with existing data from the database.

This script loads data from the database and creates embeddings for semantic search.
"""

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize RAG knowledge base with data from database."""
    print("=" * 60)
    print("🔒 Initializing RAG Knowledge Base")
    print("=" * 60)

    try:
        # Import RAG modules
        from backend.rag.document_loader import DocumentLoader
        from backend.rag.vector_store import VectorStore
        from backend.rag.embedding_service import get_embedding_service

        print("\n[1/5] Initializing embedding service...")
        embedding_service = get_embedding_service()
        info = embedding_service.get_info()
        print(f"   ✅ Backend: {info['backend']}")
        print(f"   ✅ Model: {info['model_name']}")
        print(f"   ✅ Embedding dim: {info['embedding_dim']}")

        print("\n[2/5] Initializing vector store...")
        vector_store = VectorStore()
        stats = vector_store.get_stats()
        print(f"   ✅ Collection: {stats['collection_name']}")
        print(f"   ✅ Existing documents: {stats['document_count']}")

        print("\n[3/5] Loading static knowledge (tips and procedures)...")
        all_documents = DocumentLoader.load_all_knowledge()
        print(f"   ✅ Loaded {len(all_documents)} knowledge documents")

        # Try to load from database
        print("\n[4/5] Loading data from database...")

        # Load news articles
        try:
            from backend.database.connection import supabase_admin
            if supabase_admin:
                response = supabase_admin.table('news_articles').select('*').eq('is_deleted', False).execute()
                news_articles = response.data if response.data else []

                print(f"   ✅ Found {len(news_articles)} news articles in database")

                if news_articles:
                    news_docs = DocumentLoader.load_from_news(news_articles)
                    all_documents.extend(news_docs)
                    print(f"   ✅ Added {len(news_docs)} news documents")
            else:
                print("   ⚠️  No database connection, skipping news articles")

        except Exception as e:
            print(f"   ⚠️  Could not load news from database: {e}")

        # Load CVE data
        try:
            from backend.database.connection import supabase_admin
            if supabase_admin:
                response = supabase_admin.table('cve_lookups').select('*').execute()
                cve_records = response.data if response.data else []

                print(f"   ✅ Found {len(cve_records)} CVE records in database")

                if cve_records:
                    cve_docs = DocumentLoader.load_cve_data(cve_records)
                    all_documents.extend(cve_docs)
                    print(f"   ✅ Added {len(cve_docs)} CVE documents")

        except Exception as e:
            print(f"   ⚠️  Could not load CVE data from database: {e}")

        print(f"\n   📊 Total documents to index: {len(all_documents)}")

        print("\n[5/5] Creating embeddings and indexing...")

        # Add documents to vector store
        added_count = vector_store.add_documents(all_documents)

        print(f"\n   ✅ Successfully indexed {added_count} documents")

        # Get final stats
        final_stats = vector_store.get_stats()

        print("\n" + "=" * 60)
        print("✅ RAG Knowledge Base Initialization Complete")
        print("=" * 60)
        print(f"\n📊 Final Statistics:")
        print(f"   - Collection: {final_stats['collection_name']}")
        print(f"   - Total documents: {final_stats['document_count']}")
        print(f"   - Embedding backend: {info['backend']}")
        print(f"   - Storage location: {final_stats['persist_directory']}")

        # Test retrieval
        print("\n" + "=" * 60)
        print("🧪 Testing Retrieval")
        print("=" * 60)

        test_queries = [
            "Lỗ hổng bảo mật mới nhất",
            "Cách tạo mật khẩu mạnh",
            "Phishing là gì",
            "Phản ứng sự cố bảo mật",
            "CVE nguy hiểm"
        ]

        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = vector_store.search(query, n_results=2)
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                doc_type = metadata.get('type', 'unknown')
                title = metadata.get('title', metadata.get('cve_id', metadata.get('source', 'N/A')))
                distance = result.get('distance', 0)
                similarity = 1.0 - distance
                print(f"   {i}. [{doc_type}] {title}")
                print(f"      Similarity: {similarity:.2f} | Text preview: {result['text'][:50]}...")

        print("\n" + "=" * 60)
        print("✅ RAG system ready!")
        print("=" * 60)
        print("\nThe knowledge base is now ready for semantic search.")
        print("Chatbot can now use RAG for more accurate responses.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
