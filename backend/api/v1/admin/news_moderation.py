"""
News Moderation API for CyberSec Assistant

Provides endpoints for news content management and moderation.

SECURITY NOTICE: All admin endpoints must use get_admin_client() dependency
instead of the global supabase_admin client. This ensures admin role verification
before accessing the service role client that bypasses RLS.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import logging

from backend.api.deps import require_admin, get_admin_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class NewsUpdate(BaseModel):
    """Request model for updating news article"""
    title: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    is_deleted: Optional[bool] = None


# ============================================================================
# News Moderation Endpoints
# ============================================================================

@router.get("/news")
async def get_all_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    include_deleted: bool = False,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Get all news articles with moderation options.

    Requires admin role.
    """
    try:
        offset = (page - 1) * page_size

        # Build query
        query = admin_client.table('news_articles').select('*', count='exact')

        # Apply filters
        if not include_deleted:
            query = query.eq('is_deleted', False)

        if search:
            query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")

        # Get data with pagination
        response = query.order('published_at', desc=True).range(offset, offset + page_size - 1).execute()

        total = response.count if hasattr(response, 'count') else len(response.data)

        return {
            "news": response.data,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        logger.error(f"Error getting news: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve news")


@router.put("/news/{news_id}")
async def update_news(
    news_id: UUID,
    news_update: NewsUpdate,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Update a news article (edit content or soft delete).

    Requires admin role. Logs action to admin_audit_log.
    """
    try:
        # Get current news
        current_news = admin_client.table('news_articles').select('*').eq('id', str(news_id)).execute()
        if not current_news.data:
            raise HTTPException(status_code=404, detail="News article not found")

        # Build update data
        update_data = {}
        if news_update.title is not None:
            update_data['title'] = news_update.title

        description = news_update.description
        if description is None and news_update.summary is not None:
            description = news_update.summary

        if description is not None:
            update_data['description'] = description

        if news_update.is_deleted is not None:
            update_data['is_deleted'] = news_update.is_deleted

        update_data['moderated_by'] = str(admin_id)
        update_data['moderated_at'] = datetime.now().isoformat()

        # Update news
        response = admin_client.table('news_articles').update(update_data).eq('id', str(news_id)).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Failed to update news article")

        # Log admin action
        action_type = 'news_delete' if news_update.is_deleted else 'news_edit'
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': action_type,
            'target_type': 'news',
            'target_id': str(news_id),
            'action_details': {
                'updates': news_update.model_dump(exclude_unset=True),
                'news_title': current_news.data[0].get('title')
            },
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {"message": "News article updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating news: {e}")
        raise HTTPException(status_code=500, detail="Failed to update news article")


@router.delete("/news/{news_id}")
async def delete_news(
    news_id: UUID,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Permanently delete a news article.

    Requires admin role. Use with caution - this cannot be undone.
    """
    try:
        # Get current news for audit log
        current_news = admin_client.table('news_articles').select('*').eq('id', str(news_id)).execute()
        if not current_news.data:
            raise HTTPException(status_code=404, detail="News article not found")

        # Permanently delete
        response = admin_client.table('news_articles').delete().eq('id', str(news_id)).execute()

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'news_hard_delete',
            'target_type': 'news',
            'target_id': str(news_id),
            'action_details': {
                'news_title': current_news.data[0].get('title'),
                'warning': 'Permanent deletion - cannot be undone'
            },
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {"message": "News article permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting news: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete news article")
