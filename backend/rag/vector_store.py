"""
Vector database service using ChromaDB for semantic search.

Stores document embeddings and provides fast similarity search.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector database service for storing and searching document embeddings."""

    def __init__(self, collection_name: str = "security_knowledge", persist_directory: str = None):
        """
        Initialize ChromaDB vector store.

        Args:
            collection_name: Name of the collection to use
            persist_directory: Directory to persist the database (default: ./chroma_db)
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or str(Path(__file__).parent.parent / "chroma_db")

        # Initialize ChromaDB client (persistent storage)
        logger.info(f"Initializing ChromaDB with persistence directory: {self.persist_directory}")
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

        logger.info(f"✅ Vector store initialized. Collection: {collection_name}")

        # Log collection stats
        try:
            count = self.collection.count()
            logger.info(f"Collection has {count} documents")
        except Exception as e:
            logger.warning(f"Could not get collection count: {e}")

    def add_documents(self, documents: List[Dict], embeddings: List = None) -> int:
        """
        Add documents to vector store.

        Args:
            documents: List of dicts with 'text', 'metadata', 'id' fields
            embeddings: Optional pre-computed embeddings (will be computed if not provided)

        Returns:
            Number of documents added
        """
        if not documents:
            logger.warning("No documents provided to add")
            return 0

        try:
            # Prepare data
            ids = [doc.get('id', f"doc_{i}") for i, doc in enumerate(documents)]
            texts = [doc['text'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]

            # Compute embeddings if not provided
            if embeddings is None:
                logger.info(f"Computing embeddings for {len(texts)} documents...")
                from rag.embedding_service import get_embedding_service
                embedding_service = get_embedding_service()
                embeddings = embedding_service.embed_documents(documents)

            # Convert to list for ChromaDB
            embeddings_list = [emb.tolist() for emb in embeddings]

            # Add to collection
            logger.info(f"Adding {len(ids)} documents to collection...")
            self.collection.add(
                ids=ids,
                embeddings=embeddings_list,
                metadatas=metadatas,
                documents=texts
            )

            logger.info(f"✅ Added {len(documents)} documents to vector store")
            return len(documents)

        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return 0

    def search(self, query: str, n_results: int = 5, where: Optional[Dict] = None) -> List[Dict]:
        """
        Search for relevant documents.

        Args:
            query: Search query text
            n_results: Number of results to return
            where: Optional metadata filter (e.g., {'type': 'news'})

        Returns:
            List of relevant documents with scores
        """
        try:
            # Generate query embedding
            from rag.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(query)

            # Convert to list for ChromaDB
            # Handle different array shapes
            if hasattr(query_embedding, 'ndim'):
                if query_embedding.ndim == 2:
                    # Shape (1, dim) - take first row
                    query_embedding = query_embedding[0]
                elif query_embedding.ndim > 2:
                    # Unexpected shape, flatten
                    query_embedding = query_embedding.flatten()

            query_embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else list(query_embedding)

            # Search
            logger.debug(f"Searching for: {query[:50]}...")
            results = self.collection.query(
                query_embeddings=[query_embedding_list],
                n_results=n_results,
                where=where
            )

            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'text': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'id': results['ids'][0][i] if results['ids'] else ''
                    })

            logger.debug(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

    def delete_collection(self):
        """Delete the entire collection (use with caution!)."""
        try:
            logger.warning(f"Deleting collection: {self.collection_name}")
            self.client.delete_collection(name=self.collection_name)
            logger.info("✅ Collection deleted")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")

    def get_stats(self) -> dict:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                'collection_name': self.collection_name,
                'document_count': count,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'collection_name': self.collection_name,
                'document_count': 0,
                'error': str(e)
            }


# Global instance (initialized on first use)
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Get or create the global vector store instance.

    Returns:
        VectorStore instance
    """
    global _vector_store
    if _vector_store is None:
        logger.info("Initializing global vector store...")
        _vector_store = VectorStore()
    return _vector_store
