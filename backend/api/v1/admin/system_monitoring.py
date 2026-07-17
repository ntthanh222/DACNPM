"""
System Monitoring API for CyberSec Assistant

Provides endpoints for system analytics, cache management, and API usage tracking.

SECURITY NOTICE: All admin endpoints must use get_admin_client() dependency
instead of the global supabase_admin client. This ensures admin role verification
before accessing the service role client that bypasses RLS.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
import logging

from backend.api.deps import require_admin, require_admin_or_analyst, get_admin_client, get_privileged_client
from backend.database.connection import supabase
from backend.repositories.stats import get_vulnerability_distribution, get_chat_statistics
from backend.utils.cache_manager import get_admin_stats, get_cache_stats

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_missing_is_deleted_error(error: Exception) -> bool:
    message = str(error).lower()
    return "is_deleted" in message and ("does not exist" in message or "could not find" in message)


def _count_active_news(admin_client):
    try:
        return admin_client.table('news_articles').select('id', count='exact').eq('is_deleted', False).execute()
    except Exception as e:
        if not _is_missing_is_deleted_error(e):
            raise
        logger.warning("news_articles.is_deleted missing; counting news without soft-delete filter")
        return admin_client.table('news_articles').select('id', count='exact').execute()


# ============================================================================
# Pydantic Models
# ============================================================================

class CacheRefreshRequest(BaseModel):
    """Request model for refreshing CVE cache"""
    force_refresh: bool = True


class SystemAnalyticsResponse(BaseModel):
    """Response model for system analytics"""
    total_users: int
    active_users: int
    total_scans: int
    total_news: int
    severity_distribution: Dict[str, int]
    api_usage: Dict[str, Any]


# ============================================================================
# System Monitoring Endpoints
# ============================================================================

@router.get("/system/api-usage")
async def get_api_usage(
    days: int = Query(30, ge=1, le=90),
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)  # SECURE: verified admin/analyst client
):
    """
    Get API usage statistics for external services.

    Requires admin or security analyst role.
    """
    try:
        # Get recent API usage
        start_date = (date.today() - timedelta(days=days)).isoformat()

        response = admin_client.table('api_usage_tracking').select('*').gte('date', start_date).order('date', desc=True).execute()

        # Group by API name
        api_stats = {}
        for record in response.data:
            api_name = record.get('api_name')
            if api_name not in api_stats:
                api_stats[api_name] = {
                    'total_requests': 0,
                    'daily_records': []
                }

            api_stats[api_name]['total_requests'] += record.get('request_count', 0)
            api_stats[api_name]['daily_records'].append({
                'date': record.get('date'),
                'requests': record.get('request_count'),
                'limit_cap': record.get('limit_cap')
            })

        return api_stats

    except Exception as e:
        logger.error(f"Error getting API usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve API usage statistics")


@router.get("/system/cache")
async def get_cve_cache_stats(
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)  # SECURE: verified admin/analyst client
):
    """
    Get CVE lookup cache statistics.

    Requires admin or security analyst role.
    """
    try:
        # Get cache statistics
        response = admin_client.table('cve_lookups').select('cve_id, query_count, last_accessed, cache_expires_at').order('query_count', desc=True).limit(100).execute()

        total_cached = len(response.data)
        total_queries = sum(r.get('query_count', 0) for r in response.data)

        # Get recently cached entries
        recent_response = admin_client.table('cve_lookups').select('*').order('last_accessed', desc=True).limit(20).execute()

        return {
            'total_cached_entries': total_cached,
            'total_queries_served': total_queries,
            'most_queried': response.data[:10],
            'recently_cached': recent_response.data
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")


@router.delete("/system/cache/{cve_id}")
async def clear_cve_cache(
    cve_id: str,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Clear specific CVE cache entry.

    Requires admin role.
    """
    try:
        response = admin_client.table('cve_lookups').delete().eq('cve_id', cve_id).execute()

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'cache_clear',
            'target_type': 'cve_cache',
            'target_id': cve_id,
            'action_details': {'cve_id': cve_id},
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {"message": f"Cache entry for {cve_id} cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache entry")


@router.put("/system/cache/{cve_id}")
async def refresh_cve_cache(
    cve_id: str,
    refresh_request: CacheRefreshRequest,
    admin_id: UUID = Depends(require_admin),
    admin_client = Depends(get_admin_client)  # SECURE: Admin client with role verification
):
    """
    Force refresh specific CVE cache entry.

    Requires admin role.
    """
    try:
        # Update last_refreshed_at timestamp
        response = admin_client.table('cve_lookups').update({
            'last_accessed': datetime.now().isoformat()
        }).eq('cve_id', cve_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="CVE not found in cache")

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'cache_refresh',
            'target_type': 'cve_cache',
            'target_id': cve_id,
            'action_details': {'force_refresh': refresh_request.force_refresh},
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {"message": f"Cache entry for {cve_id} marked for refresh"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh cache entry")


@router.get("/system/analytics", response_model=SystemAnalyticsResponse)
async def get_system_analytics(
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)  # SECURE: verified admin/analyst client
):
    """
    Get system-wide analytics and statistics.

    Requires admin or security analyst role.
    """
    try:
        # Get user statistics
        total_users_response = admin_client.table('users').select('id', count='exact').execute()
        active_users_response = admin_client.table('users').select('id', count='exact').eq('is_active', True).execute()

        # Get scan statistics
        total_scans_response = admin_client.table('security_scans').select('id', count='exact').execute()

        # Get news statistics
        total_news_response = _count_active_news(admin_client)

        # Get severity distribution
        severity_response = admin_client.table('security_scans').select('severity').execute()
        severity_distribution = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        for scan in severity_response.data:
            severity = (scan.get('severity') or 'info').lower()
            if severity in severity_distribution:
                severity_distribution[severity] += 1

        # Get today's API usage
        today_api_usage = admin_client.table('api_usage_tracking').select('*').eq('date', date.today().isoformat()).execute()

        api_usage_summary = {}
        for record in today_api_usage.data:
            api_name = record.get('api_name')
            api_usage_summary[api_name] = {
                'requests': record.get('request_count', 0),
                'limit': record.get('limit_cap'),
                'reset_at': record.get('last_reset_at')
            }

        return SystemAnalyticsResponse(
            total_users=total_users_response.count if hasattr(total_users_response, 'count') else len(total_users_response.data),
            active_users=active_users_response.count if hasattr(active_users_response, 'count') else len(active_users_response.data),
            total_scans=total_scans_response.count if hasattr(total_scans_response, 'count') else len(total_scans_response.data),
            total_news=total_news_response.count if hasattr(total_news_response, 'count') else len(total_news_response.data),
            severity_distribution=severity_distribution,
            api_usage=api_usage_summary
        )

    except Exception as e:
        logger.error(f"Error getting system analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system analytics")


@router.get("/system/dashboard/cached")
async def get_cached_dashboard_stats(
    force_refresh: bool = False,
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)
):
    """
    Get cached dashboard statistics for improved performance.

    Uses Redis caching with 10-minute TTL to reduce database load.
    Set force_refresh=true to bypass cache and recompute statistics.

    Requires admin or security analyst role.
    """
    try:
        # Define async function to compute dashboard stats
        async def compute_dashboard_stats():
            """Compute expensive dashboard statistics from database"""
            try:
                # Get user statistics
                total_users_response = admin_client.table('users').select('id', count='exact').execute()
                active_users_response = admin_client.table('users').select('id', count='exact').eq('is_active', True).execute()

                # Get scan statistics
                total_scans_response = admin_client.table('security_scans').select('id', count='exact').execute()

                # Get news statistics
                total_news_response = _count_active_news(admin_client)

                # Get vulnerability distribution
                vuln_distribution = get_vulnerability_distribution()

                # Get chat statistics
                chat_stats = get_chat_statistics()

                # Get today's API usage
                today_api_usage = admin_client.table('api_usage_tracking').select('*').eq('date', date.today().isoformat()).execute()

                api_usage_summary = {}
                for record in today_api_usage.data:
                    api_name = record.get('api_name')
                    api_usage_summary[api_name] = {
                        'requests': record.get('request_count', 0),
                        'limit': record.get('limit_cap'),
                        'reset_at': record.get('last_reset_at')
                    }

                return {
                    'total_users': total_users_response.count if hasattr(total_users_response, 'count') else len(total_users_response.data),
                    'active_users': active_users_response.count if hasattr(active_users_response, 'count') else len(active_users_response.data),
                    'total_scans': total_scans_response.count if hasattr(total_scans_response, 'count') else len(total_scans_response.data),
                    'total_news': total_news_response.count if hasattr(total_news_response, 'count') else len(total_news_response.data),
                    'vulnerability_distribution': vuln_distribution,
                    'chat_statistics': chat_stats,
                    'api_usage': api_usage_summary,
                    'computed_at': datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error computing dashboard stats: {e}")
                raise

        # Use cache manager to get or compute statistics
        stats_data = await get_admin_stats(
            compute_fn=compute_dashboard_stats,
            ttl=600,  # 10 minutes cache
            force_refresh=force_refresh
        )

        # Add cache status
        stats_data['from_cache'] = not force_refresh
        stats_data['cache_ttl'] = 600  # 10 minutes

        return stats_data

    except Exception as e:
        logger.error(f"Error getting cached dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard statistics")


@router.post("/system/dashboard/clear-cache")
async def clear_dashboard_cache(
    admin_id: UUID = Depends(require_admin),
    admin_client=Depends(get_admin_client)
):
    """
    Clear dashboard statistics cache.

    Forces recomputation on next dashboard load.

    Requires admin role.
    """
    try:
        from backend.utils.cache_manager import invalidate_pattern

        # Clear all dashboard cache keys
        cleared_count = await invalidate_pattern("dashboard_stats:*")
        cleared_count += await invalidate_pattern("admin_stats:*")

        # Log admin action
        admin_client.table('admin_audit_log').insert({
            'admin_user_id': str(admin_id),
            'action_type': 'cache_clear',
            'target_type': 'dashboard_cache',
            'action_details': {'cleared_keys': cleared_count},
            'timestamp': datetime.now().isoformat()
        }).execute()

        return {
            'message': f'Cleared {cleared_count} dashboard cache entries',
            'cleared_count': cleared_count,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error clearing dashboard cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear dashboard cache")


@router.get("/system/cache/stats")
async def get_system_cache_stats(
    admin_id: UUID = Depends(require_admin_or_analyst),
    admin_client = Depends(get_privileged_client)
):
    """
    Get Redis cache statistics and health.

    Requires admin or security analyst role.
    """
    try:
        cache_stats = await get_cache_stats()
        return cache_stats

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")
