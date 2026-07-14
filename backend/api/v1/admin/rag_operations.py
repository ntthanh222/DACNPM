"""
RAG Operations API for CyberSec Assistant

Provides endpoints for RAG knowledge base management and document operations.

SECURITY NOTICE: All admin endpoints must use get_admin_client() dependency
instead of the global supabase_admin client. This ensures admin role verification
before accessing the service role client that bypasses RLS.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile
from pydantic import BaseModel
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, date, timedelta
import logging
import os

from backend.api.deps import (
    require_admin,
    require_admin_or_analyst,
    get_admin_client,
    get_privileged_client,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class RAGIngestResponse(BaseModel):
    """Response model for RAG document ingestion"""
    success: bool
    document_id: str
    message: str


class IntentAnalyticsResponse(BaseModel):
    """Response model for intent analytics"""
    total_queries: int
    fallback_queries: int
    avg_confidence: float
    low_confidence_count: int
    recent_queries: List[Dict[str, Any]]


# ============================================================================
# RAG Operations Endpoints
# ============================================================================

@router.post("/rag/ingest", response_model=RAGIngestResponse)
async def ingest_rag_document(
    file: UploadFile = File(...),
    doc_type: str = Query(..., description="Document type: tip, procedure, news, cve"),
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Upload and ingest a document into RAG knowledge base.

    Requires admin role. Supports txt and md files only.
    Enhanced with file size, encoding, and content validation.
    """
    # Constants for validation
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_CHARS = 100_000  # 100K characters
    ALLOWED_DOC_TYPES = {'tip', 'procedure', 'news', 'cve'}

    try:
        # Validate doc_type
        if doc_type not in ALLOWED_DOC_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document type '{doc_type}'. Allowed types: {', '.join(ALLOWED_DOC_TYPES)}"
            )

        # Validate file type
        allowed_extensions = {'.txt', '.md'}  # PDF removed - not implemented
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type '{file_ext}'. Allowed types: {', '.join(allowed_extensions)}. PDF processing is not available."
            )

        # Read file content
        content = await file.read()

        # File size validation
        if len(content) > MAX_FILE_SIZE:
            size_mb = len(content) / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({size_mb:.2f}MB). Maximum allowed size: {MAX_FILE_SIZE / (1024 * 1024)}MB"
            )

        # Empty file check
        if not content or len(content.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty. Please upload a file with content."
            )

        # UTF-8 encoding validation
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File encoding must be UTF-8. Please save your file with UTF-8 encoding and try again."
            )

        # Character limit validation
        if len(text_content) > MAX_CHARS:
            raise HTTPException(
                status_code=400,
                detail=f"Content too long ({len(text_content):,} characters). Maximum allowed: {MAX_CHARS:,} characters."
            )

        # Check for meaningful content (not just whitespace)
        if len(text_content.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="File content is too short (less than 10 characters). Please provide meaningful content."
            )

        # Import RAG components
        try:
            from backend.rag.document_loader import DocumentLoader
            from backend.rag.vector_store import get_vector_store
            import uuid

            # Create document
            doc_id = str(uuid.uuid4())

            document = {
                'id': doc_id,
                'text': text_content,
                'metadata': {
                    'type': doc_type,
                    'source': 'admin_upload',
                    'filename': file.filename,
                    'uploaded_by': str(admin_id),
                    'uploaded_at': datetime.now().isoformat()
                }
            }

            # Get vector store instance
            vector_store = get_vector_store()

            # Add to ChromaDB
            vector_store.add_documents([document])

            # Log admin action
            admin_client.table('admin_audit_log').insert({
                'admin_user_id': str(admin_id),
                'action_type': 'rag_document_ingest',
                'target_type': 'rag_document',
                'target_id': doc_id,
                'action_details': {
                    'filename': file.filename,
                    'doc_type': doc_type,
                    'content_length': len(text_content)
                },
                'timestamp': datetime.now().isoformat()
            }).execute()

            return RAGIngestResponse(
                success=True,
                document_id=doc_id,
                message=f"Document '{file.filename}' ingested successfully"
            )

        except ImportError as e:
            logger.error(f"RAG components not available: {e}")
            raise HTTPException(status_code=500, detail="RAG components not available")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest document")


@router.get("/rag/documents")
async def get_rag_documents(
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)
):
    """
    Get list of documents in RAG knowledge base.

    Requires admin or security analyst role.
    """
    try:
        # Try to get documents from ChromaDB
        try:
            from backend.rag.vector_store import get_vector_store

            vector_store = get_vector_store()

            # Get collection
            collection = vector_store.collection

            # Get all documents
            results = collection.get(include=['documents', 'metadatas'])

            documents = []
            if results and results.get('ids'):
                for i, doc_id in enumerate(results['ids']):
                    documents.append({
                        'id': doc_id,
                        'content': results['documents'][i][:200] + '...' if len(results['documents'][i]) > 200 else results['documents'][i],
                        'metadata': results['metadatas'][i] if results.get('metadatas') else {}
                    })

            return {"documents": documents, "total": len(documents)}

        except ImportError:
            # Fallback: return sample data
            return {
                "documents": [
                    {
                        "id": "sample_1",
                        "content": "Sample security tip document...",
                        "metadata": {"type": "tip", "source": "system"}
                    }
                ],
                "total": 1,
                "warning": "ChromaDB not available, showing sample data"
            }

    except Exception as e:
        logger.error(f"Error getting RAG documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve RAG documents")


@router.delete("/rag/documents/{doc_id}")
async def delete_rag_document(
    doc_id: str,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Delete a document from RAG knowledge base.

    Requires admin role.
    """
    try:
        from backend.rag.vector_store import get_vector_store

        vector_store = get_vector_store()

        # Delete document from ChromaDB
        vector_store.collection.delete(ids=[doc_id])

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'rag_document_delete',
            'target_type': 'rag_document',
            'target_id': doc_id,
            'action_details': {},
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {"message": f"Document {doc_id} deleted successfully"}

    except ImportError:
        raise HTTPException(status_code=500, detail="RAG components not available")
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/rag/intents", response_model=IntentAnalyticsResponse)
async def get_intent_analytics(
    days: int = Query(7, ge=1, le=30),
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)  # SECURE: verified admin/analyst client
):
    """
    Get intent confidence analytics for chat queries.

    Requires admin or security analyst role.
    """
    try:
        # Get recent intent analytics
        start_date = (date.today() - timedelta(days=days)).isoformat()

        response = admin_client.table('intent_analytics').select('*').gte('created_at', start_date).order('created_at', desc=True).execute()

        # Calculate statistics
        total_queries = len(response.data)
        fallback_queries = len([r for r in response.data if r.get('fallback_used')])

        confidences = [r.get('confidence', 0) for r in response.data if r.get('confidence') is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        low_confidence_count = len([c for c in confidences if c < 0.5])

        # Get recent low-confidence queries
        low_conf_queries = [r for r in response.data if r.get('confidence', 1.0) < 0.7][:10]

        return IntentAnalyticsResponse(
            total_queries=total_queries,
            fallback_queries=fallback_queries,
            avg_confidence=round(avg_confidence, 2),
            low_confidence_count=low_confidence_count,
            recent_queries=low_conf_queries
        )

    except Exception as e:
        logger.error(f"Error getting intent analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve intent analytics")
