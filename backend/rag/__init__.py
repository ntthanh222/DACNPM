"""
RAG (Retrieval-Augmented Generation) module for CyberSec Assistant.

This module provides semantic search capabilities using vector embeddings
to enhance chatbot responses with relevant security knowledge.
"""

# Lazy imports to avoid circular dependencies
__all__ = [
    'EmbeddingService',
    'VectorStore',
    'DocumentLoader',
    'DocumentRetriever'
]

def _import_modules():
    """Import modules when needed"""
    from backend.rag.embedding_service import EmbeddingService
    from backend.rag.vector_store import VectorStore
    from backend.rag.document_loader import DocumentLoader
    from backend.rag.retriever import DocumentRetriever
    return EmbeddingService, VectorStore, DocumentLoader, DocumentRetriever

# Make modules available
EmbeddingService = None
VectorStore = None
DocumentLoader = None
DocumentRetriever = None

# Import on first access
def __getattr__(name):
    if name in __all__:
        EmbeddingService, VectorStore, DocumentLoader, DocumentRetriever = _import_modules()
        globals()[name] = locals().get(name)
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
