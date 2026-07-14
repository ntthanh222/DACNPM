"""
Crawler Control API for CyberSec Assistant

Provides endpoints for news crawler management, configuration, and monitoring.

SECURITY NOTICE: All admin endpoints must use get_admin_client() dependency
instead of the global supabase_admin client. This ensures admin role verification
before accessing the service role client that bypasses RLS.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import logging
import json
import os

from backend.api.deps import require_admin, require_admin_or_analyst, get_admin_client, get_privileged_client
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class CrawlerTriggerRequest(BaseModel):
    """Request model for triggering crawler"""
    sources: Optional[List[str]] = None
    max_articles: Optional[int] = None
    fuzzy_threshold: Optional[float] = None
    headless: Optional[bool] = True


class CrawlerConfigUpdate(BaseModel):
    """Request model for updating crawler configuration"""
    sources: Optional[Dict[str, Any]] = None
    fuzzy_similarity_threshold: Optional[float] = None
    max_articles_per_source: Optional[int] = None
    scheduled_enabled: Optional[bool] = None
    scheduled_interval_hours: Optional[int] = None


# ============================================================================
# Crawler Control Endpoints
# ============================================================================

@router.post("/crawler/trigger")
async def trigger_crawler(
    trigger_request: CrawlerTriggerRequest,
    background_tasks: BackgroundTasks,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Manually trigger the news crawler with optional configuration override.

    Requires admin role. Runs in background without blocking.
    """
    try:
        # Import crawler scheduler
        from backend.api.crawler_scheduler import trigger_crawler_now

        # Log crawler trigger
        admin_client.table('crawler_runs').insert({
            'triggered_by': str(admin_id),
            'started_at': datetime.now().isoformat(),
            'status': 'running',
            'configuration': {
                'sources': trigger_request.sources,
                'max_articles': trigger_request.max_articles,
                'fuzzy_threshold': trigger_request.fuzzy_threshold
            }
        }).execute()

        # Trigger crawler in background (non-blocking)
        try:
            background_tasks.add_task(trigger_crawler_now)
        except Exception as crawler_error:
            logger.error(f"Crawler execution error: {crawler_error}")
            # Update status to failed
            # Note: In production, you'd want to track the run ID

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'crawler_trigger',
            'target_type': 'crawler',
            'action_details': {
                'configuration': trigger_request.model_dump()
            },
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {"message": "Crawler triggered successfully", "status": "running"}

    except Exception as e:
        logger.error(f"Error triggering crawler: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger crawler")


@router.get("/crawler/config")
async def get_crawler_config(
    admin_id: UUID = Depends(require_admin)
):
    """
    Get current crawler configuration.

    Requires admin role.
    """
    try:
        # Default configuration
        default_config = {
            'sources': {
                'thehackernews': {'enabled': True, 'max_articles': 10},
                'vnexpress': {'enabled': True, 'max_articles': 10},
                'securityweek': {'enabled': False, 'max_articles': 10},
                'krebs': {'enabled': False, 'max_articles': 10},
                'bleepingcomputer': {'enabled': False, 'max_articles': 10},
                'darkreading': {'enabled': False, 'max_articles': 10},
                'helpnetsecurity': {'enabled': False, 'max_articles': 10},
                'theregister': {'enabled': False, 'max_articles': 10}
            },
            'fuzzy_similarity_threshold': 0.85,
            'max_articles_per_source': 10,
            'scheduled_enabled': True,
            'scheduled_interval_hours': 4
        }

        # Try to load from config file if exists
        config_file_path = os.path.join(settings.BASE_DIR, 'scripts', 'crawler_config.json')
        if os.path.exists(config_file_path):
            try:
                with open(config_file_path, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Could not load crawler config file: {e}")

        return default_config

    except Exception as e:
        logger.error(f"Error getting crawler config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crawler configuration")


@router.put("/crawler/config")
async def update_crawler_config(
    config_update: CrawlerConfigUpdate,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Update crawler configuration.

    Requires admin role.
    """
    try:
        # Get current config
        current_config = await get_crawler_config(admin_id)

        # Update with new values
        if config_update.sources:
            current_config['sources'].update(config_update.sources)

        if config_update.fuzzy_similarity_threshold is not None:
            current_config['fuzzy_similarity_threshold'] = config_update.fuzzy_similarity_threshold

        if config_update.max_articles_per_source is not None:
            current_config['max_articles_per_source'] = config_update.max_articles_per_source

        if config_update.scheduled_enabled is not None:
            current_config['scheduled_enabled'] = config_update.scheduled_enabled

        if config_update.scheduled_interval_hours is not None:
            current_config['scheduled_interval_hours'] = config_update.scheduled_interval_hours

        # Save to config file
        config_file_path = os.path.join(settings.BASE_DIR, 'scripts', 'crawler_config.json')
        with open(config_file_path, 'w') as f:
            json.dump(current_config, f, indent=2)

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'crawler_config_update',
            'target_type': 'crawler',
            'action_details': {
                'updates': config_update.model_dump(exclude_unset=True)
            },
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {"message": "Crawler configuration updated successfully", "config": current_config}

    except Exception as e:
        logger.error(f"Error updating crawler config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update crawler configuration")


@router.get("/crawler/stats")
async def get_crawler_stats(
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Get crawler performance statistics.

    Requires admin role.
    """
    try:
        # Get recent crawler runs
        response = admin_client.table('crawler_runs').select('*').order('started_at', desc=True).limit(20).execute()

        # Calculate statistics
        total_runs = len(response.data)
        completed_runs = len([r for r in response.data if r.get('status') == 'completed'])
        failed_runs = len([r for r in response.data if r.get('status') == 'failed'])

        total_articles_found = sum(r.get('articles_found', 0) for r in response.data)
        total_articles_added = sum(r.get('articles_added', 0) for r in response.data)
        total_duplicates = sum(r.get('duplicates_removed', 0) for r in response.data)

        return {
            'total_runs': total_runs,
            'completed_runs': completed_runs,
            'failed_runs': failed_runs,
            'success_rate': round(completed_runs / total_runs * 100, 2) if total_runs > 0 else 0,
            'total_articles_found': total_articles_found,
            'total_articles_added': total_articles_added,
            'total_duplicates_removed': total_duplicates,
            'recent_runs': response.data[:5]
        }

    except Exception as e:
        logger.error(f"Error getting crawler stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crawler statistics")


@router.get("/crawler/logs")
async def get_crawler_logs(
    limit: int = Query(50, ge=1, le=200),
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)  # SECURE: verified admin/analyst client
):
    """
    Get recent crawler logs.

    Requires admin or security analyst role.
    """
    try:
        # Get recent crawler runs with detailed information
        response = admin_client.table('crawler_runs').select('*').order('started_at', desc=True).limit(limit).execute()

        logs = []
        for run in response.data:
            log_entry = {
                'id': run.get('id'),
                'started_at': run.get('started_at'),
                'completed_at': run.get('completed_at'),
                'status': run.get('status'),
                'articles_found': run.get('articles_found'),
                'articles_added': run.get('articles_added'),
                'duplicates_removed': run.get('duplicates_removed'),
                'error_count': run.get('error_count'),
                'error_details': run.get('error_details'),
                'triggered_by': run.get('triggered_by')
            }
            logs.append(log_entry)

        return {"logs": logs}

    except Exception as e:
        logger.error(f"Error getting crawler logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve crawler logs")
