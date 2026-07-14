"""
CRUD operations for cve_lookups table
CVE query caching with TTL management
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
from backend.database.models import CVELookup, CVELookupCreate, CVELookupUpdate, CacheStatistics
from backend.database.connection import supabase, supabase_admin


def _get_cve_cache_fallback(cve_id: str) -> Dict[str, Any]:
    return {
        'cve_id': cve_id,
        'response_data': {},
        'cvss_score': None,
        'severity': None,
        'is_cached': False
    }


def _extract_cvss_metadata(response_data: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    vulnerabilities = response_data.get('vulnerabilities', [])
    if not vulnerabilities:
        return None, None

    metrics = vulnerabilities[0].get('cve', {}).get('metrics', {})
    cvss_v31 = metrics.get('cvssMetricV31', [])
    if cvss_v31:
        cvss_data = cvss_v31[0].get('cvssData', {})
        return (
            str(cvss_data.get('baseScore', 'N/A')),
            cvss_data.get('baseSeverity', 'unknown').lower()
        )

    cvss_v20 = metrics.get('cvssMetricV2', [])
    if not cvss_v20:
        return None, None

    cvss_data = cvss_v20[0].get('cvssData', {})
    severity_mapping = {
        'LOW': 'low',
        'MEDIUM': 'medium',
        'HIGH': 'high'
    }
    return (
        str(cvss_data.get('baseScore', 'N/A')),
        severity_mapping.get(cvss_data.get('baseSeverity', 'unknown').upper(), 'unknown')
    )


def get_cve_lookup(cve_id: str) -> Optional[CVELookup]:
    """
    Get CVE lookup by CVE ID
    Security: Public read access for caching purposes
    """
    try:
        # Normalize CVE ID
        cve_id = cve_id.upper()

        response = supabase.table('cve_lookups').select('*').eq('cve_id', cve_id).execute()

        if not response.data:
            return None

        cve_lookup = CVELookup(**response.data[0])
        if cve_lookup.cache_expires_at <= datetime.now(timezone.utc):
            return None

        update_cve_access(cve_id)
        return cve_lookup
    except Exception as e:
        print(f"Error getting CVE lookup {cve_id}: {e}")
        return None


def get_cached_cve_with_fallback(cve_id: str) -> Dict[str, Any]:
    """
    Get cached CVE or return fallback data structure
    Uses the database function for efficient cache checking
    Security: Public read access
    """
    try:
        # Normalize CVE ID
        cve_id = cve_id.upper()

        # Use the database function for efficient cache checking
        response = supabase.rpc('get_cached_cve', params={'cve_id_param': cve_id}).execute()

        if not response.data:
            return _get_cve_cache_fallback(cve_id)

        cached_cve = response.data[0]
        return {
            'cve_id': cached_cve['cve_id'],
            'response_data': cached_cve['response_data'],
            'cvss_score': cached_cve['cvss_score'],
            'severity': cached_cve['severity'],
            'is_cached': cached_cve['is_cached']
        }
    except Exception as e:
        print(f"Error getting cached CVE {cve_id}: {e}")
        return _get_cve_cache_fallback(cve_id)


def create_cve_lookup(cve_lookup: CVELookupCreate) -> Optional[CVELookup]:
    """
    Create new CVE lookup entry
    Security: Uses admin client to bypass RLS for server-side cache operations
    """
    try:
        # Normalize CVE ID
        cve_data = cve_lookup.model_dump(exclude_unset=True)
        cve_data['cve_id'] = cve_data['cve_id'].upper()

        # Set timestamps
        cve_data['query_timestamp'] = datetime.now(timezone.utc).isoformat()

        if not cve_data.get('cvss_score') or not cve_data.get('severity'):
            cvss_score, severity = _extract_cvss_metadata(cve_data.get('response_data', {}))
            if cvss_score is not None:
                cve_data['cvss_score'] = cvss_score
            if severity is not None:
                cve_data['severity'] = severity

        # Set default TTL (24 hours) if not provided
        if 'cache_expires_at' not in cve_data:
            ttl_hours = 24
            cve_data['cache_expires_at'] = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()

        # Use supabase_admin to bypass RLS restrictions for server-side cache operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('cve_lookups').insert(cve_data).execute()
        if response.data:
            return CVELookup(**response.data[0])
        return None
    except Exception as e:
        print(f"Error creating CVE lookup: {e}")
        return None


def update_cve_lookup(cve_id: str, cve_update: CVELookupUpdate) -> Optional[CVELookup]:
    """
    Update CVE lookup (typically used to extend cache TTL or update response data)
    Security: Uses admin client to bypass RLS for server-side cache operations
    """
    try:
        # Normalize CVE ID
        cve_id = cve_id.upper()

        update_data = cve_update.model_dump(exclude_unset=True)

        # Update last_accessed if not explicitly set
        if 'last_accessed' not in update_data:
            update_data['last_accessed'] = datetime.now(timezone.utc).isoformat()

        # Use supabase_admin to bypass RLS restrictions for server-side cache operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('cve_lookups').update(update_data).eq('cve_id', cve_id).execute()
        if response.data:
            return CVELookup(**response.data[0])
        return None
    except Exception as e:
        print(f"Error updating CVE lookup {cve_id}: {e}")
        return None


def delete_cve_lookup(cve_id: str) -> bool:
    """
    Delete CVE lookup (typically cache invalidation)
    Security: Uses admin client to bypass RLS for server-side cache operations
    """
    try:
        # Normalize CVE ID
        cve_id = cve_id.upper()

        # Use supabase_admin to bypass RLS restrictions for server-side cache operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('cve_lookups').delete().eq('cve_id', cve_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting CVE lookup {cve_id}: {e}")
        return False


def update_cve_access(cve_id: str) -> bool:
    """
    Update CVE access tracking (increment query count and update last_accessed)
    This is handled automatically by database trigger, but function provided for manual updates
    Security: Uses admin client to bypass RLS for server-side cache operations
    """
    try:
        # Normalize CVE ID
        cve_id = cve_id.upper()

        # The database trigger handles this automatically, but we can force an update
        # Use supabase_admin to bypass RLS restrictions for server-side cache operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('cve_lookups').update({
            'last_accessed': datetime.now(timezone.utc).isoformat()
        }).eq('cve_id', cve_id).execute()

        return len(response.data) > 0
    except Exception as e:
        print(f"Error updating CVE access {cve_id}: {e}")
        return False


def extend_cache_ttl(cve_id: str, hours_to_add: int = 24) -> bool:
    """
    Extend cache TTL for a specific CVE
    Security: Authenticated users can extend cache for frequently accessed CVEs
    """
    try:
        # Normalize CVE ID
        cve_id = cve_id.upper()

        # Use the database function for extending TTL
        response = supabase.rpc('extend_cache_ttl', params={
            'cve_id_param': cve_id,
            'hours_to_add': hours_to_add
        }).execute()

        return response.data if response.data else False
    except Exception as e:
        print(f"Error extending cache TTL for {cve_id}: {e}")
        return False


def cleanup_expired_cache() -> int:
    """
    Cleanup expired cache entries
    Security: Admin/Service access only
    """
    try:
        response = supabase_admin.rpc('cleanup_expired_cache').execute()
        return response.data if response.data else 0
    except Exception as e:
        print(f"Error cleaning up expired cache: {e}")
        return 0


def get_cache_statistics() -> Optional[CacheStatistics]:
    """
    Get comprehensive cache statistics for monitoring
    Security: Admin/Service access only
    """
    try:
        from backend.database.connection import is_database_available

        if not is_database_available() or supabase_admin is None:
            print("Database unavailable for cache statistics")
            return None

        response = supabase_admin.rpc('get_cache_statistics').execute()

        if response.data:
            stats_data = response.data[0]
            return CacheStatistics(
                total_entries=stats_data.get('total_entries', 0),
                active_entries=stats_data.get('active_entries', 0),
                expired_entries=stats_data.get('expired_entries', 0),
                avg_query_count=float(stats_data.get('avg_query_count', 0)),
                most_accessed_cve=stats_data.get('most_accessed_cve'),
                cache_hit_rate=float(stats_data.get('cache_hit_rate', 0))
            )
        return None
    except Exception as e:
        print(f"Error getting cache statistics: {e}")
        return None


def get_popular_cves(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get most frequently accessed CVEs
    Security: Admin/Service access only
    """
    try:
        response = supabase_admin.table('cve_lookups').select('*').order('query_count', desc=True).limit(limit).execute()

        return [
            {
                'cve_id': cve_data['cve_id'],
                'query_count': cve_data['query_count'],
                'last_accessed': cve_data['last_accessed'],
                'severity': cve_data.get('severity'),
                'cvss_score': cve_data.get('cvss_score')
            }
            for cve_data in response.data
        ]
    except Exception as e:
        print(f"Error getting popular CVEs: {e}")
        return []


def get_cves_by_severity(severity: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get CVEs by severity level
    Security: Uses admin client to bypass RLS for server-side cache operations
    """
    try:
        # Normalize severity
        severity = severity.lower()

        # Use supabase_admin to bypass RLS restrictions for server-side cache operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('cve_lookups').select('*').eq('severity', severity).order('query_count', desc=True).limit(limit).execute()

        cves = []
        for cve_data in response.data:
            # Only return active cache entries
            cache_expiry = datetime.fromisoformat(cve_data['cache_expires_at'].replace('Z', '+00:00'))
            if cache_expiry > datetime.now(timezone.utc):
                cves.append({
                    'cve_id': cve_data['cve_id'],
                    'cvss_score': cve_data.get('cvss_score'),
                    'severity': cve_data.get('severity'),
                    'query_count': cve_data['query_count'],
                    'response_data': cve_data.get('response_data', {})
                })

        return cves
    except Exception as e:
        print(f"Error getting CVEs by severity {severity}: {e}")
        return []


def get_expiring_cache_entries(hours: int = 6, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get cache entries that will expire soon (for proactive refresh)
    Security: Admin/Service access only
    """
    try:
        expiry_window = datetime.now(timezone.utc) + timedelta(hours=hours)
        response = supabase_admin.table('cve_lookups').select('*').lte('cache_expires_at', expiry_window.isoformat()).gte('cache_expires_at', datetime.now(timezone.utc).isoformat()).order('cache_expires_at', asc=True).limit(limit).execute()

        expiring_entries = []
        for cve_data in response.data:
            expiring_entries.append({
                'cve_id': cve_data['cve_id'],
                'cache_expires_at': cve_data['cache_expires_at'],
                'query_count': cve_data['query_count'],
                'hours_until_expiry': (expiry_window - datetime.now(timezone.utc)).total_seconds() / 3600
            })

        return expiring_entries
    except Exception as e:
        print(f"Error getting expiring cache entries: {e}")
        return []


def batch_create_cve_lookups(cve_lookups: List[CVELookupCreate]) -> List[Optional[CVELookup]]:
    """
    Batch create multiple CVE lookup entries
    Security: Authenticated users can create cache entries
    """
    try:
        return [create_cve_lookup(cve_lookup) for cve_lookup in cve_lookups]
    except Exception as e:
        print(f"Error in batch creating CVE lookups: {e}")
        return [None] * len(cve_lookups)
