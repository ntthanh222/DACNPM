"""
Document retriever for RAG system.

Retrieves relevant documents from vector store and formats them as context.
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Retrieve relevant documents for RAG-augmented responses."""

    def __init__(self, max_results: int = 5, min_score: float = 0.5):
        """
        Initialize document retriever.

        Args:
            max_results: Maximum number of results to retrieve
            min_score: Minimum similarity score threshold (0-1)
        """
        self.max_results = max_results
        self.min_score = min_score

    def _format_context_header(self, index: int, metadata: Dict) -> str:
        doc_type = metadata.get('type', 'unknown')
        if doc_type == 'news':
            return f"[Tin tức {index} - {metadata.get('source', 'Unknown')}]\n{metadata.get('title', 'N/A')}"
        if doc_type == 'security_tip':
            return f"[Mẹo bảo mật {index} - {metadata.get('title', 'N/A')}]"
        if doc_type == 'cve':
            return f"[CVE {index} - {metadata.get('cve_id', 'N/A')} ({metadata.get('severity', 'N/A')})]"
        if doc_type == 'procedure':
            return f"[Quy trình {index} - {metadata.get('title', 'N/A')}]"
        return f"[Thông tin {index}]"

    def retrieve(
        self,
        query: str,
        filters: Optional[Dict] = None,
        n_results: Optional[int] = None,
        top_k: Optional[int] = None  # Backwards compatibility alias
    ) -> List[Dict]:
        """
        Retrieve relevant documents for query.

        Args:
            query: User query text
            filters: Optional metadata filters (e.g., {'type': 'news'})
            n_results: Number of results (uses max_results if not specified)
            top_k: Alias for n_results (for backwards compatibility)

        Returns:
            List of relevant documents sorted by relevance
        """
        # Support both n_results and top_k for backwards compatibility
        num_results = n_results or top_k or self.max_results
        try:
            from backend.rag.vector_store import get_vector_store
            vector_store = get_vector_store()

            # Search vector store
            results = vector_store.search(
                query=query,
                n_results=num_results,
                where=filters
            )

            # Filter by score if threshold set
            if self.min_score > 0:
                # Convert distance to similarity score (cosine distance -> similarity)
                filtered_results = []
                for result in results:
                    distance = result.get('distance', 1.0)
                    # Cosine distance to similarity: similarity = 1 - distance
                    similarity = 1.0 - distance
                    if similarity >= self.min_score:
                        result['similarity'] = similarity
                        filtered_results.append(result)
                results = filtered_results

            logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}", exc_info=True)
            return []

    def format_context(
        self,
        results: List[Dict],
        max_length: int = 2000,
        include_metadata: bool = True
    ) -> str:
        """
        Format retrieved documents into context string.

        Args:
            results: Retrieved documents
            max_length: Maximum length of context string
            include_metadata: Whether to include metadata in output

        Returns:
            Formatted context string
        """
        if not results:
            return "Không có thông tin liên quan."

        context_parts = []

        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            context_text = f"{self._format_context_header(i, metadata)}\n{result['text']}"

            # Add metadata if requested
            if include_metadata and metadata:
                meta_str = ", ".join(f"{k}: {v}" for k, v in metadata.items() if k != 'type')
                if meta_str:
                    context_text += f"\nMetadata: {meta_str}"

            context_parts.append(context_text)

        # Join with separator
        full_context = "\n\n".join(context_parts)

        # Truncate if too long
        if len(full_context) > max_length:
            full_context = full_context[:max_length] + "\n\n... (context truncated)"

        return full_context

    def retrieve_and_format(
        self,
        query: str,
        filters: Optional[Dict] = None,
        n_results: Optional[int] = None,
        max_length: int = 2000
    ) -> Dict[str, any]:
        """
        Retrieve and format documents in one call.

        Args:
            query: User query text
            filters: Optional metadata filters
            n_results: Number of results
            max_length: Maximum context length

        Returns:
            Dictionary with formatted context and metadata
        """
        results = self.retrieve(query, filters, n_results)
        context = self.format_context(results, max_length=max_length)

        return {
            'context': context,
            'num_results': len(results),
            'results': results,
            'query': query
        }


# Global instance (initialized on first use)
_retriever: Optional[DocumentRetriever] = None


def get_retriever() -> DocumentRetriever:
    """
    Get or create the global retriever instance.

    Returns:
        DocumentRetriever instance
    """
    global _retriever
    if _retriever is None:
        logger.info("Initializing global retriever...")
        _retriever = DocumentRetriever()
    return _retriever
