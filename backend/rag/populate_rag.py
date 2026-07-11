"""
Populate RAG vector store with security knowledge.

This script loads security documents and populates the vector store
to enable intelligent RAG responses.
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up to backend directory
sys.path.insert(0, project_root)

# Import directly from files, not through package
import sys
import importlib.util

def import_module_from_file(module_name, file_path):
    """Import a module directly from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import required modules directly
current_path = os.path.dirname(os.path.abspath(__file__))

# Load document_loader
document_loader_path = os.path.join(current_path, 'document_loader.py')
document_loader_module = import_module_from_file('document_loader', document_loader_path)
DocumentLoader = document_loader_module.DocumentLoader

# Load vector_store
vector_store_path = os.path.join(current_path, 'vector_store.py')
vector_store_module = import_module_from_file('vector_store', vector_store_path)
get_vector_store = vector_store_module.get_vector_store


def populate_vector_store():
    """Populate vector store with all available security knowledge."""
    logger.info("🚀 Starting RAG vector store population...")

    try:
        # Get vector store instance
        vector_store = get_vector_store()

        # Check current status
        stats = vector_store.get_stats()
        logger.info(f"📊 Current vector store stats: {stats}")

        # Load all knowledge documents
        logger.info("📚 Loading security knowledge documents...")
        documents = DocumentLoader.load_all_knowledge()

        if not documents:
            logger.warning("⚠️ No documents to load!")
            return 0

        logger.info(f"📄 Loaded {len(documents)} documents")

        # Check if collection already has documents
        if stats.get('document_count', 0) > 0:
            logger.info(f"ℹ️ Collection already has {stats['document_count']} documents")
            logger.info("💡 If you want to re-populate, run: python rag/populate_rag.py --clear")
            return stats['document_count']

        # Add documents to vector store
        logger.info("💾 Adding documents to vector store (this may take a minute)...")
        added_count = vector_store.add_documents(documents)

        if added_count > 0:
            logger.info(f"✅ Successfully added {added_count} documents to vector store")

            # Verify population
            new_stats = vector_store.get_stats()
            logger.info(f"📊 New vector store stats: {new_stats}")

            # Test search
            logger.info("🔍 Testing vector store search...")
            test_results = vector_store.search("phishing là gì?", n_results=2)
            logger.info(f"🔍 Test search returned {len(test_results)} results")
            if test_results:
                logger.info(f"📄 First result preview: {test_results[0]['text'][:100]}...")
        else:
            logger.warning("⚠️ No documents were added to vector store")

        return added_count

    except Exception as e:
        logger.error(f"❌ Error populating vector store: {e}")
        import traceback
        traceback.print_exc()
        return 0


def clear_vector_store():
    """Clear the vector store collection."""
    logger.warning("🗑️ Clearing vector store collection...")
    vector_store = get_vector_store()
    vector_store.delete_collection()
    logger.info("✅ Vector store cleared")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_vector_store()
    else:
        count = populate_vector_store()
        if count > 0:
            print(f"\n🎉 Successfully populated RAG vector store with {count} documents!")
        else:
            print("\n❌ Failed to populate RAG vector store")
