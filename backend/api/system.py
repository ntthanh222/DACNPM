"""System and observability endpoints."""

import os
import time
import logging
import hashlib
import json
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse

from backend.core.observability import limiter, render_metrics
from backend.api.deps import require_admin_or_analyst
from backend.services.rag_service import get_rag_service
from backend.rag.vector_store import get_vector_store
from backend.database.connection import is_database_available

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Legacy health check endpoint returning 200 healthy."""
    return {"status": "healthy"}


@router.get("/health/live", tags=["system"])
async def health_live():
    """Liveness probe. Returns 200 immediately if server is running."""
    return {"status": "healthy"}


@router.get("/health/ready", tags=["system"])
async def health_ready():
    """
    Readiness probe.
    Probes database, Redis, Rasa NLU, Rasa Actions, ChromaDB, Crawler, and active Rasa model.
    Mandatory dependencies: Database, Redis.
    """
    # 1. Database Check (Mandatory)
    db_ok = False
    try:
        db_ok = is_database_available()
    except Exception as e:
        logger.warning(f"Ready probe database check failed: {e}")

    # 2. Redis Check (Mandatory)
    redis_ok = False
    try:
        from backend.utils.cache_manager import get_redis_client
        r_client = get_redis_client()
        if r_client:
            r_client.ping()
            redis_ok = True
    except Exception as e:
        logger.warning(f"Ready probe Redis check failed: {e}")

    # If any mandatory dependency is down, return 503 Service Unavailable
    if not (db_ok and redis_ok):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "details": {
                    "database": "online" if db_ok else "offline",
                    "redis": "online" if redis_ok else "offline",
                }
            }
        )

    # 3. Rasa NLU Check (Optional/Degraded)
    rasa_ok = False
    try:
        import httpx
        rasa_url = os.getenv("RASA_SERVER_URL", "http://rasa:5005")
        r = httpx.get(rasa_url, timeout=1.0)
        if r.status_code == 200:
            rasa_ok = True
    except Exception:
        pass

    # 4. Rasa Actions Check (Optional/Degraded)
    rasa_actions_ok = False
    try:
        import httpx
        actions_url = os.getenv("RASA_ACTION_SERVER_URL", "http://rasa-actions:5055/health")
        r = httpx.get(actions_url, timeout=1.0)
        if r.status_code == 200:
            rasa_actions_ok = True
    except Exception:
        pass

    # 5. ChromaDB Check (Optional/Degraded)
    chroma_ok = False
    try:
        vs = get_vector_store()
        vs.collection.count()
        chroma_ok = True
    except Exception:
        pass

    # 6. Crawler Check (Optional/Degraded)
    crawler_ok = False
    try:
        import httpx
        crawler_url = os.getenv("CRAWLER_SERVICE_URL", "http://crawler:8002/health")
        r = httpx.get(crawler_url, timeout=1.0)
        if r.status_code == 200:
            crawler_ok = True
    except Exception:
        pass

    # 7. Active Model Validation (Optional/Degraded)
    manifest_ok = False
    try:
        manifest_path = "/app/rasa/models/current-model.json"
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
                model_file = manifest.get("filename")
                expected_hash = manifest.get("sha256")
                if model_file and expected_hash:
                    model_path = os.path.join("/app/rasa/models", model_file)
                    if os.path.exists(model_path):
                        sha2 = hashlib.sha256()
                        with open(model_path, "rb") as f_model:
                            for chunk in iter(lambda: f_model.read(4096), b""):
                                sha2.update(chunk)
                        if sha2.hexdigest() == expected_hash:
                            manifest_ok = True
    except Exception:
        pass

    degraded = not (rasa_ok and rasa_actions_ok and chroma_ok and crawler_ok and manifest_ok)

    return {
        "status": "degraded" if degraded else "healthy",
        "details": {
            "database": "online",
            "redis": "online",
            "rasa_nlu": "online" if rasa_ok else "offline",
            "rasa_actions": "online" if rasa_actions_ok else "offline",
            "chromadb": "online" if chroma_ok else "offline",
            "crawler": "online" if crawler_ok else "offline",
            "active_model_valid": "yes" if manifest_ok else "no"
        }
    }


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(
        content=render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/ai-health", tags=["system"])
async def ai_health(
    user_id: UUID = Depends(require_admin_or_analyst)
) -> Dict[str, Any]:
    """
    Exposes metrics and status for chatbot engines, Gemini API, and vector database.
    """
    # 1. Database & Redis Check
    db_ok = False
    try:
        db_ok = is_database_available()
    except Exception:
        pass

    # 2. RAG vector DB document count
    chroma_count = 0
    rag_status = "uninitialized"
    try:
        rag = get_rag_service()
        if rag.is_enabled():
            rag_status = "ready"
            vector_store = get_vector_store()
            chroma_count = vector_store.collection.count()
        else:
            rag_status = "disabled"
    except Exception as e:
        rag_status = f"failed: {e}"

    # 3. Gemini configuration status
    gemini_status = "configured" if os.environ.get("GEMINI_API_KEY") else "missing_key"

    # 4. Rasa server connectivity ping
    rasa_status = "offline"
    try:
        import httpx
        rasa_url = os.getenv("RASA_SERVER_URL", "http://rasa:5005")
        r = httpx.get(rasa_url, timeout=1.0)
        if r.status_code == 200:
            rasa_status = "online"
    except Exception:
        pass

    # 5. Active Model Name and Hash
    model_name = "unknown"
    model_hash = "unknown"
    try:
        manifest_path = "/app/rasa/models/current-model.json"
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
                model_name = manifest_data.get("filename", "unknown")
                model_hash = manifest_data.get("sha256", "unknown")
    except Exception as e:
        logger.warning(f"Failed to read Rasa model manifest: {e}")

    # 6. Telemetry metrics from Database
    fallback_rate = "unknown"
    safety_refusal_count = "unknown"
    error_rate = "unknown"
    prompt_injection_detections = "unknown"

    if db_ok:
        try:
            from backend.database.connection import supabase, supabase_admin
            client = supabase_admin if supabase_admin else supabase
            response = client.table('chat_history').select('intent').execute()
            if response.data:
                total_count = len(response.data)
                fallback_count = sum(1 for item in response.data if item.get('intent') in {'nlu_fallback', 'fallback', 'out_of_scope'})
                safety_refusal_count = sum(1 for item in response.data if item.get('intent') in {'safety_refusal', 'uncertain', 'clarification', 'incident_response', 'audit'})
                prompt_injection_detections = sum(1 for item in response.data if item.get('intent') == 'prompt_injection')
                fallback_rate = (fallback_count / total_count) if total_count > 0 else 0.0
                error_rate = 0.0  # System errors can be set to 0.0 or measured otherwise
            else:
                fallback_rate = 0.0
                safety_refusal_count = 0
                prompt_injection_detections = 0
                error_rate = 0.0
        except Exception as e:
            logger.error(f"Error fetching telemetry metrics: {e}")

    return {
        "backend_status": "healthy",
        "rasa_status": rasa_status,
        "gemini_status": gemini_status,
        "rag_status": rag_status,
        "chromadb_document_count": chroma_count,
        "active_model_name": model_name,
        "active_model_hash": model_hash,
        "latency_stats": {
            "last_successful_retrieval": True if chroma_count > 0 else None,
            "latency_p95_ms": None
        },
        "metrics": {
            "fallback_rate": fallback_rate,
            "error_rate": error_rate,
            "safety_refusal_count": safety_refusal_count,
            "prompt_injection_detections": prompt_injection_detections
        }
    }
