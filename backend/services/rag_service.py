"""
RAG Service for CyberSec Assistant

Handles Retrieval-Augmented Generation operations including:
- Document retrieval from vector database
- Context formatting and enhancement
- RAG availability checks

SECURITY NOTICE: This service processes user queries and must sanitize
all inputs before database operations.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation operations"""

    def __init__(self):
        self._retriever = None
        self._rag_enabled = False
        self._initialization_attempted = False
        self.chroma_client = None
        self.embedding_service = None
        self.llm_service = None

    def _init_rag(self):
        """Initialize RAG modules (lazy loading)."""
        if self._initialization_attempted:
            return

        self._initialization_attempted = True

        try:
            from rag.retriever import get_retriever
            self._retriever = get_retriever()
            self._rag_enabled = True
            logger.info("✅ RAG modules initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize RAG: {e}")
            logger.warning("RAG features will be disabled")
            self._rag_enabled = False

    def is_enabled(self) -> bool:
        """Check if RAG is available and enabled"""
        if not self._initialization_attempted:
            self._init_rag()
        return self._rag_enabled

    async def retrieve_context(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: User query to find relevant context for
            n_results: Number of documents to retrieve

        Returns:
            List of retrieved documents with metadata
        """
        if not self.is_enabled():
            logger.debug("RAG is not enabled, skipping retrieval")
            return []

        try:
            retrieved_docs = self._retriever.retrieve(query, n_results=n_results)
            if retrieved_docs:
                logger.info(f"🔍 Retrieved {len(retrieved_docs)} relevant documents")
            return retrieved_docs
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []

    def format_context(self, retrieved_docs: List[Dict[str, Any]], max_length: int = 1500) -> str:
        """
        Format retrieved documents into context string.

        Args:
            retrieved_docs: List of retrieved documents
            max_length: Maximum length of formatted context

        Returns:
            Formatted context string
        """
        if not retrieved_docs:
            return ""

        try:
            context = self._retriever.format_context(retrieved_docs, max_length=max_length)
            logger.debug(f"Formatted RAG context (length: {len(context)})")
            return context
        except Exception as e:
            logger.error(f"Failed to format RAG context: {e}")
            return ""

    async def enhance_message(self, message: str, n_results: int = 3) -> tuple[str, List[Dict[str, Any]]]:
        """
        Enhance a message with RAG context.

        Args:
            message: Original user message
            n_results: Number of documents to retrieve

        Returns:
            Tuple of (enhanced_message, retrieved_documents)
        """
        if not self.is_enabled():
            return message, []

        try:
            retrieved_docs = await self.retrieve_context(message, n_results)
            if not retrieved_docs:
                return message, []

            rag_context = self.format_context(retrieved_docs, max_length=1500)
            if not rag_context:
                return message, []

            enhanced_message = f"[Context - Thông tin liên quan]\n{rag_context}\n\n[Câu hỏi của người dùng]\n{message}"
            logger.debug(f"Enhanced message with RAG context (length: {len(enhanced_message)})")

            return enhanced_message, retrieved_docs

        except Exception as e:
            logger.error(f"Failed to enhance message with RAG: {e}")
            return message, []

    async def get_rag_response(self, message: str) -> Optional[str]:
        """
        Get a direct RAG-based response for a message.

        Args:
            message: User message to generate response for

        Returns:
            RAG-generated response or None if unavailable
        """
        if not self.is_enabled():
            return None

        try:
            retrieved_docs = await self.retrieve_context(message, n_results=3)
            if not retrieved_docs:
                return None

            rag_context = self.format_context(retrieved_docs, max_length=1500)
            if not rag_context:
                return None

            return f"Dựa trên kiến thức bảo mật, đây là thông tin liên quan:\n\n{rag_context}\n\nBạn có muốn tìm hiểu thêm về chủ đề này không?"

        except Exception as e:
            logger.error(f"Failed to generate RAG response: {e}")
            return None

    async def search(self, query: str, intent: Optional[str] = None, limit: int = 3) -> Dict[str, Any]:
        """Search relevant context for a query"""
        if hasattr(self, 'chroma_client') and self.chroma_client is not None:
            if hasattr(self, 'embedding_service') and self.embedding_service is not None:
                await self.embedding_service.generate_embedding(query)
            query_result = self.chroma_client.query(query)
            return {
                "context": query_result.get("documents", []),
                "sources": [m.get("source", "") for m in query_result.get("metadatas", [])]
            }

        retrieved_docs = await self.retrieve_context(query, limit)
        return {
            "context": [d.get("text", "") for d in retrieved_docs] if retrieved_docs else [],
            "sources": [d.get("metadata", {}).get("source", "") for d in retrieved_docs] if retrieved_docs else []
        }

    async def add_document(self, document_id: str, content: str, metadata: Dict[str, Any]) -> str:
        """Add a document to the knowledge base"""
        if hasattr(self, 'chroma_client') and self.chroma_client is not None:
            if hasattr(self, 'embedding_service') and self.embedding_service is not None:
                await self.embedding_service.generate_embedding(content)
            self.chroma_client.add(document_id, content, metadata)
            return document_id

        from rag.vector_store import get_vector_store
        vector_store = get_vector_store()
        document = {
            'id': document_id,
            'text': content,
            'metadata': metadata
        }
        vector_store.add_documents([document])
        return document_id

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base"""
        if hasattr(self, 'chroma_client') and self.chroma_client is not None:
            self.chroma_client.delete(document_id)
            return True

        from rag.vector_store import get_vector_store
        vector_store = get_vector_store()
        vector_store.delete_documents([document_id])
        return True

    def validate_document_content(self, content: str) -> bool:
        """Validate document content"""
        if not content or len(content.strip()) < 10:
            return False
        return True

    def sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata values"""
        from ..utils.validators import sanitize_input
        sanitized = {}
        for k, v in metadata.items():
            if isinstance(v, str):
                sanitized[k] = sanitize_input(v)
            else:
                sanitized[k] = v
        return sanitized


# Global RAG service instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get global RAG service instance (singleton pattern)"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
        logger.info("RAG service created")
    return _rag_service