"""
Embedding generation service for RAG system.

Supports multiple embedding backends:
1. sentence-transformers (preferred for Vietnamese)
2. OpenAI embeddings (requires API key)
3. Simple hash-based fallback (no ML required, Python 3.14 compatible)
"""

import numpy as np
from typing import List, Union, Optional
import logging
import sys
import warnings
import hashlib
import os
from collections import Counter

# Suppress NumPy warnings for Python 3.14
warnings.filterwarnings('ignore', category=RuntimeWarning)

logger = logging.getLogger(__name__)


class SimpleHashEmbedding:
    """
    Simple hash-based embedding generator (no ML required).
    Uses character n-gram hashing for similarity search.
    """

    def __init__(self, dim: int = 384):
        """
        Initialize hash-based embedding.

        Args:
            dim: Embedding dimension
        """
        self.dim = dim
        self.hash_fn = hashlib.sha256

    def _text_to_vector(self, text: str) -> np.ndarray:
        """Convert text to hash-based vector."""
        # Normalize text
        text = text.lower().strip()

        # Create features from character n-grams (3-5 chars)
        ngrams = []
        for n in range(3, 6):
            for i in range(len(text) - n + 1):
                ngrams.append(text[i:i+n])

        # Hash n-grams to create vector
        vector = np.zeros(self.dim, dtype=np.float32)

        for ngram in ngrams:
            # Hash the n-gram
            hash_bytes = self.hash_fn(ngram.encode()).digest()
            # Use first 4 bytes for index
            idx = int.from_bytes(hash_bytes[:4], byteorder='big') % self.dim
            # Increment count (simple frequency)
            vector[idx] += 1

        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

    def transform(self, texts: List[str]) -> np.ndarray:
        """Transform list of texts to embeddings."""
        vectors = np.array([self._text_to_vector(text) for text in texts])
        return vectors

    def fit(self, texts: List[str]):
        """Fit is no-op for hash-based embedding."""
        pass  # Already fitted


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, model_name: str = "paraphrase-multilingual-mpnet-base-v2", backend: str = "auto"):
        """
        Initialize embedding service.

        Args:
            model_name: Name of the embedding model to use
            backend: Backend to use ('auto', 'sentence-transformers', 'openai', 'tfidf')
        """
        self.model_name = model_name
        self.backend = backend
        self.model = None
        self.embedding_dim = None
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the embedding backend."""
        if self.backend == "auto":
            # Check Python version - sentence-transformers not compatible with Python 3.14+
            python_version = sys.version_info
            if python_version >= (3, 14):
                logger.warning(f"Python {python_version.major}.{python_version.minor} detected - sentence-transformers may be unstable")
                logger.info("Using TF-IDF fallback for stability")
                self._init_tfidf()
                return

            # Try sentence-transformers first, fallback to TF-IDF
            try:
                self._init_sentence_transformers()
                return
            except Exception as e:
                logger.warning(f"Could not initialize sentence-transformers: {e}")
                logger.info("Falling back to TF-IDF embeddings")
                self._init_tfidf()
        elif self.backend == "sentence-transformers":
            self._init_sentence_transformers()
        elif self.backend in ("tfidf", "hash"):
            self._init_tfidf()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _init_sentence_transformers(self):
        """Initialize sentence-transformers backend."""
        try:
            # Test import first - this can segfault on Python 3.14
            import sentence_transformers
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            self.backend = "sentence-transformers"
            logger.info(f"✅ sentence-transformers initialized. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to initialize sentence-transformers: {e}")
            raise

    def _init_tfidf(self):
        """Initialize simple hash-based fallback backend (Python 3.14 compatible)."""
        try:
            logger.info("Initializing hash-based fallback embeddings")
            self.model = SimpleHashEmbedding(dim=384)
            self.embedding_dim = 384
            self.backend = "hash"
            logger.info(f"✅ Hash-based embeddings initialized. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to initialize hash embeddings: {e}")
            raise

    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text or list of texts.

        Args:
            text: Single text string or list of texts

        Returns:
            Embedding vectors (numpy array)
        """
        if self.backend == "sentence-transformers":
            if isinstance(text, str):
                text = [text]
            return self.model.encode(text, convert_to_numpy=True)

        elif self.backend == "hash":
            if isinstance(text, str):
                text = [text]
            return self.model.transform(text)

        else:
            raise NotImplementedError(f"Embedding not implemented for backend: {self.backend}")

    def embed_documents(self, documents: List[dict]) -> List[np.ndarray]:
        """
        Generate embeddings for documents.

        Args:
            documents: List of document dicts with 'text' field

        Returns:
            List of embedding vectors
        """
        texts = [doc['text'] for doc in documents]
        embeddings = self.embed_text(texts)

        # If single embedding, convert to list
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)

        return [embeddings[i] for i in range(len(embeddings))]

    def get_info(self) -> dict:
        """
        Get information about the embedding service.

        Returns:
            Dictionary with service information
        """
        return {
            'backend': self.backend,
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim
        }


# Global instance (initialized on first use)
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global embedding service instance.

    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        logger.info("Initializing global embedding service...")
        # Docker can explicitly select the deterministic fallback so the first
        # request never blocks on downloading a large Hugging Face model.
        backend = os.getenv("EMBEDDING_BACKEND", "auto").strip().lower() or "auto"
        _embedding_service = EmbeddingService(backend=backend)
    return _embedding_service
