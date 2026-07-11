"""
NLU Training API for CyberSec Assistant

Provides endpoints for NLU model training, active learning loop, and intent analytics.

SECURITY NOTICE: All admin endpoints must use get_admin_client() dependency
instead of the global supabase_admin client. This ensures admin role verification
before accessing the service role client that bypasses RLS.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
import logging
import asyncio
import subprocess
import os
import threading

from backend.api.deps import require_admin, require_admin_or_analyst, get_admin_client
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# NLU Training Lock Mechanism
# ============================================================================

_nlu_training_lock = asyncio.Lock()
_nlu_training_status = {
    "in_progress": False,
    "pid": None,
    "started_at": None,
    "started_by": None,
    "message": None
}


# ============================================================================
# Pydantic Models
# ============================================================================

class NLUQueryReview(BaseModel):
    """Request model for reviewing NLU query"""
    correct_intent: Optional[str] = None
    notes: Optional[str] = None


class AddToTrainingRequest(BaseModel):
    """Request model for adding reviewed queries to training"""
    intent_filter: Optional[List[str]] = None


# ============================================================================
# NLU Training Endpoints
# ============================================================================

@router.get("/nlu/failed-queries")
async def get_failed_queries(
    fallback_only: bool = Query(True, description="Only show fallback queries"),
    review_status: Optional[str] = Query(None, description="Filter by review status (pending, reviewed, approved, rejected)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Get failed/low-confidence NLU queries for review.

    Requires admin role. Part of Active Learning Loop.
    """
    try:
        # Build query - get fallback queries (low confidence where LLM was used)
        query = admin_client.table('intent_analytics').select('*')

        # Filter to show only fallback queries where confidence was low
        if fallback_only:
            query = query.eq('fallback_used', True).lt('confidence', 0.5)

        # Filter by review status if specified
        if review_status:
            query = query.eq('review_status', review_status)

        # Get failed/low confidence queries first
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)

        response = query.execute()

        # Get total count for pagination
        count_query = admin_client.table('intent_analytics').select('id', count='exact')
        if fallback_only:
            count_query = count_query.eq('fallback_used', True).lt('confidence', 0.5)
        if review_status:
            count_query = count_query.eq('review_status', review_status)
        count_response = count_query.execute()
        total = count_response.count if hasattr(count_response, 'count') else len(count_response.data)

        return {
            "queries": response.data,
            "total": total,
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting failed queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve failed queries")


@router.put("/nlu/queries/{query_id}/review")
async def review_query(
    query_id: str,
    review: NLUQueryReview,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Review and correct a failed NLU query.

    Requires admin role. Updates the intent_analytics record with corrected intent and review status.
    """
    try:
        # Check if query exists
        check_response = admin_client.table('intent_analytics').select('*').eq('id', query_id).execute()
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Query not found")

        # Update the query with review information
        update_data = {
            'correct_intent': review.correct_intent,
            'admin_notes': review.notes,
            'review_status': 'reviewed'
        }

        admin_client.table('intent_analytics').update(update_data).eq('id', query_id).execute()

        return {
            "message": "Query reviewed successfully",
            "query_id": query_id,
            "admin_user_id": str(admin_id),
            "review_data": {
                "correct_intent": review.correct_intent,
                "notes": review.notes,
                "review_status": "reviewed"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing query: {e}")
        raise HTTPException(status_code=500, detail="Failed to review query")


@router.post("/nlu/add-to-training")
async def add_reviewed_to_training(
    request: AddToTrainingRequest,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Add reviewed queries to nlu.yml and trigger retraining.

    Requires admin role. Part of Active Learning Loop.
    """
    try:
        # Get reviewed queries that have been corrected but not yet added to training
        query = admin_client.table('intent_analytics').select('*').eq('review_status', 'reviewed').eq('added_to_training', False)

        # Apply intent filter if specified (using correct_intent from admin review)
        if request.intent_filter:
            query = query.eq('correct_intent', request.intent_filter)

        # Get recent queries (last 7 days)
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        query = query.gte('created_at', week_ago)

        response = query.execute()
        queries_to_add = response.data

        if not queries_to_add:
            return {"added": 0, "message": "No new reviewed queries to add"}

        # Update nlu.yml with new training examples
        nlu_path = os.path.join(settings.PROJECT_ROOT, "rasa", "data", "nlu.yml")

        # Read existing content
        with open(nlu_path, 'r', encoding='utf-8') as f:
            nlu_content = f.read()

        # Group by intent (using correct_intent from admin review)
        by_intent = {}
        query_ids = []
        for q in queries_to_add:
            intent = q.get('correct_intent', 'unknown')
            if not intent or intent == 'nlu_fallback':
                continue  # Skip queries without corrected intents

            if intent not in by_intent:
                by_intent[intent] = []
            by_intent[intent].append(q['query'])
            query_ids.append(q['id'])

        # Append to nlu.yml
        with open(nlu_path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n# Auto-added from Active Learning - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

            for intent, examples in by_intent.items():
                f.write(f"\n- intent: {intent}\n")
                f.write(f"  examples: |\n")
                for ex in examples:
                    # Escape special characters
                    escaped_ex = ex.replace('|', '\\|').replace('-', '\\-')
                    f.write(f"    - {escaped_ex}\n")

        # Mark queries as added to training
        for query_id in query_ids:
            admin_client.table('intent_analytics').update({
                'added_to_training': True
            }).eq('id', query_id).execute()

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'nlu_training_update',
            'target_type': 'nlu_training',
            'action_details': {
                'added_count': len(query_ids),
                'intents': list(by_intent.keys())
            },
            'timestamp': datetime.now().isoformat()
        }).execute()

        logger.info(f"Added {len(queries_to_add)} queries to training data")

        return {
            "added": len(queries_to_add),
            "intents": list(by_intent.keys()),
            "message": f"Added {len(queries_to_add)} examples to nlu.yml"
        }

    except Exception as e:
        logger.error(f"Error adding to training: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add to training: {str(e)}")


@router.post("/nlu/retrain")
async def trigger_retraining(
    admin_id: UUID = Depends(require_admin)
):
    """
    Trigger Rasa model retraining.

    Requires admin role. Runs train.bat in background.
    Uses lock mechanism to prevent concurrent training.
    """
    # Check if training is already in progress
    if _nlu_training_lock.locked():
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": "Training already in progress",
                "message": "A training session is currently running. Please wait for it to complete before starting a new one.",
                "status": _nlu_training_status
            }
        )

    try:
        project_dir = str(settings.PROJECT_ROOT)
        rasa_dir = os.path.join(project_dir, "rasa")

        # Determine Rasa virtual environment Python interpreter
        if os.name == 'nt':
            rasa_python = os.path.join(rasa_dir, "venv", "Scripts", "python.exe")
        else:
            rasa_python = os.path.join(rasa_dir, "venv", "bin", "python")

        # Fallback to system Python if venv not found
        if not os.path.exists(rasa_python):
            logger.warning(f"Rasa Python not found at {rasa_python}, falling back to system 'python'")
            rasa_python = 'python'

        # Update status before starting
        _nlu_training_status["in_progress"] = True
        _nlu_training_status["started_at"] = datetime.now().isoformat()
        _nlu_training_status["started_by"] = str(admin_id)
        _nlu_training_status["message"] = "Training in progress..."

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'nlu_retrain',
            'target_type': 'rasa_model',
            'action_details': {},
            'timestamp': datetime.now().isoformat()
        }).execute()

        # Define a callback to reset status when process completes
        def on_training_complete(pid):
            _nlu_training_status["in_progress"] = False
            _nlu_training_status["pid"] = None
            _nlu_training_status["message"] = f"Training completed (PID: {pid})"
            logger.info(f"Rasa training completed (PID: {pid})")

        # Call Rasa train directly through venv Python
        process = subprocess.Popen(
            [rasa_python, "-m", "rasa", "train"],
            cwd=rasa_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        _nlu_training_status["pid"] = process.pid

        logger.info(f"Started Rasa training (PID: {process.pid}) by admin {admin_id}")

        # Start background thread to monitor process completion
        def monitor_process(pid):
            process.wait()
            on_training_complete(pid)

        monitor_thread = threading.Thread(target=monitor_process, args=(process.pid,), daemon=True)
        monitor_thread.start()

        return {
            "status": "training_started",
            "message": "Rasa model training initiated",
            "pid": process.pid,
            "started_at": _nlu_training_status["started_at"]
        }

    except HTTPException:
        # Reset status on HTTP exception
        _nlu_training_status["in_progress"] = False
        _nlu_training_status["message"] = None
        raise
    except Exception as e:
        # Reset status on error
        _nlu_training_status["in_progress"] = False
        _nlu_training_status["message"] = f"Training failed: {str(e)}"
        logger.error(f"Error triggering retraining: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger retraining")


@router.get("/nlu/status")
async def get_nlu_training_status(admin_id: UUID = Depends(require_admin_or_analyst)):
    """
    Get current NLU training status.

    Requires admin or security analyst role.
    """
    return _nlu_training_status


@router.get("/nlu/intent-distribution")
async def get_intent_distribution(
    days: int = Query(7, ge=1, le=90),
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Get intent distribution statistics for analytics.

    Requires admin or security analyst role.
    """
    try:
        start_date = (date.today() - timedelta(days=days)).isoformat()

        response = admin_client.table('intent_analytics').select('predicted_intent, confidence').gte('created_at', start_date).execute()

        # Count by intent
        intent_counts = {}
        confidence_by_intent = {}

        for record in response.data:
            intent = record.get('predicted_intent', 'unknown')
            confidence = record.get('confidence', 0)

            if intent not in intent_counts:
                intent_counts[intent] = 0
                confidence_by_intent[intent] = []

            intent_counts[intent] += 1
            confidence_by_intent[intent].append(confidence)

        # Calculate average confidence by intent
        intent_stats = {}
        for intent, counts in intent_counts.items():
            confidences = confidence_by_intent.get(intent, [])
            avg_conf = sum(confidences) / len(confidences) if confidences else 0

            intent_stats[intent] = {
                'count': counts,
                'avg_confidence': round(avg_conf, 2),
                'percentage': round(counts / len(response.data) * 100, 2) if response.data else 0
            }

        return {
            'total_queries': len(response.data),
            'period_days': days,
            'intent_stats': intent_stats
        }

    except Exception as e:
        logger.error(f"Error getting intent distribution: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve intent distribution")