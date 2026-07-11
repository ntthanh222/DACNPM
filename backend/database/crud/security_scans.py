"""
CRUD operations for security_scans table
Track and manage security scans with comprehensive metadata
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from backend.database.models import SecurityScan, SecurityScanCreate, SecurityScanUpdate
from backend.database.connection import supabase, supabase_admin


def get_security_scan(scan_id: UUID) -> Optional[SecurityScan]:
    """
    Get security scan by ID
    Security: Uses admin client to bypass RLS for server-side operations
    """
    try:
        # Use supabase_admin to bypass RLS restrictions for server-side operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('security_scans').select('*').eq('id', str(scan_id)).execute()
        if response.data:
            return SecurityScan(**response.data[0])
        return None
    except Exception as e:
        print(f"Error getting security scan {scan_id}: {e}")
        return None


def get_user_security_scans(
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    scan_type: Optional[str] = None,
    status: Optional[str] = None,
    min_severity: Optional[str] = None
) -> List[SecurityScan]:
    """
    Get security scans for a specific user with filtering options
    Security: Uses admin client to bypass RLS for server-side operations
    """
    try:
        # Use supabase_admin to bypass RLS restrictions for server-side operations
        client = supabase_admin if supabase_admin else supabase
        query = client.table('security_scans').select('*').eq('user_id', str(user_id))

        # Apply filters
        if scan_type:
            query = query.eq('scan_type', scan_type)
        if status:
            query = query.eq('status', status)
        if min_severity:
            # Filter by minimum severity level
            severity_order = {'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            min_level = severity_order.get(min_severity, 0)

        # Apply pagination and ordering
        response = query.order('scan_timestamp', desc=True).range(skip, skip + limit - 1).execute()

        scans = [SecurityScan(**scan) for scan in response.data]

        # Filter by severity if specified (client-side filtering for simplicity)
        if min_severity:
            severity_order = {'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            min_level = severity_order.get(min_severity, 0)
            scans = [scan for scan in scans if scan.severity and
                    severity_order.get(scan.severity, 0) >= min_level]

        return scans
    except Exception as e:
        print(f"Error getting security scans for user {user_id}: {e}")
        return []


def create_security_scan(scan: SecurityScanCreate) -> Optional[SecurityScan]:
    """
    Create new security scan
    Security: Uses admin client to bypass RLS for server-side operations
    """
    try:
        scan_data = scan.model_dump(exclude_unset=True)

        # Convert UUID objects to strings for JSON serialization
        if 'user_id' in scan_data and isinstance(scan_data['user_id'], UUID):
            scan_data['user_id'] = str(scan_data['user_id'])

        # Set timestamps
        scan_data['scan_timestamp'] = datetime.now().isoformat()
        if 'scan_result' not in scan_data or not scan_data['scan_result']:
            scan_data['scan_result'] = {}

        # Initialize scan metadata if not provided
        if 'scan_metadata' not in scan_data or not scan_data['scan_metadata']:
            scan_data['scan_metadata'] = {
                'api_version': '1.0',
                'scan_engine': 'cybersec-assistant',
                'initiated_by': 'user'
            }

        # Use supabase_admin to bypass RLS restrictions for server-side operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('security_scans').insert(scan_data).execute()
        if response.data:
            return SecurityScan(**response.data[0])
        return None
    except Exception as e:
        print(f"Error creating security scan: {e}")
        return None


def update_security_scan(scan_id: UUID, scan_update: SecurityScanUpdate) -> Optional[SecurityScan]:
    """
    Update security scan (typically used to complete pending scans)
    Security: Uses admin client to bypass RLS for server-side operations
    """
    try:
        update_data = scan_update.model_dump(exclude_unset=True)

        # Set completed_at timestamp if status is being set to completed
        if 'status' in update_data and update_data['status'] == 'completed':
            update_data['completed_at'] = datetime.now().isoformat()

        # Use supabase_admin to bypass RLS restrictions for server-side operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('security_scans').update(update_data).eq('id', str(scan_id)).execute()
        if response.data:
            return SecurityScan(**response.data[0])
        return None
    except Exception as e:
        print(f"Error updating security scan {scan_id}: {e}")
        return None


def delete_security_scan(scan_id: UUID) -> bool:
    """
    Delete security scan
    Security: Uses admin client to bypass RLS for server-side operations
    """
    try:
        # Use supabase_admin to bypass RLS restrictions for server-side operations
        client = supabase_admin if supabase_admin else supabase
        response = client.table('security_scans').delete().eq('id', str(scan_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting security scan {scan_id}: {e}")
        return False


def get_pending_scans(limit: int = 10) -> List[SecurityScan]:
    """
    Get pending security scans for background processing
    Security: Admin/Service access only
    """
    try:
        response = supabase_admin.table('security_scans').select('*').eq('status', 'pending').order('scan_timestamp', asc=True).limit(limit).execute()
        return [SecurityScan(**scan) for scan in response.data]
    except Exception as e:
        print(f"Error getting pending scans: {e}")
        return []


def get_failed_scans(hours: int = 24, limit: int = 10) -> List[SecurityScan]:
    """
    Get failed security scans for retry analysis
    Security: Admin/Service access only
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        response = supabase_admin.table('security_scans').select('*').eq('status', 'failed').gte('scan_timestamp', cutoff_time.isoformat()).limit(limit).execute()
        return [SecurityScan(**scan) for scan in response.data]
    except Exception as e:
        print(f"Error getting failed scans: {e}")
        return []


def get_user_scan_statistics(user_id: UUID) -> Dict[str, Any]:
    """
    Get scan statistics for a specific user
    Security: RLS enforced
    """
    try:
        # Get all user's scans
        scans = get_user_security_scans(user_id, limit=1000)

        if not scans:
            return {
                'total_scans': 0,
                'completed_scans': 0,
                'failed_scans': 0,
                'pending_scans': 0,
                'high_risk_scans': 0,
                'critical_risk_scans': 0,
                'avg_risk_score': 0.0,
                'last_scan_timestamp': None
            }

        # Calculate statistics
        total_scans = len(scans)
        completed_scans = sum(1 for scan in scans if scan.status == 'completed')
        failed_scans = sum(1 for scan in scans if scan.status == 'failed')
        pending_scans = sum(1 for scan in scans if scan.status == 'pending')
        high_risk_scans = sum(1 for scan in scans if scan.severity == 'high')
        critical_risk_scans = sum(1 for scan in scans if scan.severity == 'critical')

        # Calculate average risk score (only for completed scans with risk scores)
        completed_with_scores = [scan for scan in scans if scan.status == 'completed' and scan.risk_score is not None]
        avg_risk_score = sum(scan.risk_score for scan in completed_with_scores) / len(completed_with_scores) if completed_with_scores else 0.0

        # Get last scan timestamp
        last_scan_timestamp = max(scan.scan_timestamp for scan in scans) if scans else None

        return {
            'total_scans': total_scans,
            'completed_scans': completed_scans,
            'failed_scans': failed_scans,
            'pending_scans': pending_scans,
            'high_risk_scans': high_risk_scans,
            'critical_risk_scans': critical_risk_scans,
            'avg_risk_score': round(avg_risk_score, 2),
            'last_scan_timestamp': last_scan_timestamp
        }
    except Exception as e:
        print(f"Error getting scan statistics for user {user_id}: {e}")
        return {
            'total_scans': 0,
            'completed_scans': 0,
            'failed_scans': 0,
            'pending_scans': 0,
            'high_risk_scans': 0,
            'critical_risk_scans': 0,
            'avg_risk_score': 0.0,
            'last_scan_timestamp': None
        }


def cleanup_old_scans(days_to_keep: int = 90) -> int:
    """
    Cleanup old completed scans to maintain database performance
    Security: Admin/Service access only
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        response = supabase_admin.rpc('cleanup_old_scans', params={'days_to_keep': days_to_keep}).execute()
        return response.data if response.data else 0
    except Exception as e:
        print(f"Error cleaning up old scans: {e}")
        return 0


def get_recent_high_risk_scans(hours: int = 24, limit: int = 10) -> List[SecurityScan]:
    """
    Get recent high and critical risk scans for security monitoring
    Security: Admin/Security Analyst access only
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        response = supabase_admin.table('security_scans').select('*').in_('severity', ['high', 'critical']).gte('scan_timestamp', cutoff_time.isoformat()).order('risk_score', desc=True).limit(limit).execute()
        return [SecurityScan(**scan) for scan in response.data]
    except Exception as e:
        print(f"Error getting recent high risk scans: {e}")
        return []


def get_scan_type_statistics(scan_type: str) -> Dict[str, Any]:
    """
    Get statistics for a specific scan type
    Security: Admin/Service access only
    """
    try:
        response = supabase_admin.table('security_scans').select('*').eq('scan_type', scan_type).execute()
        scans = [SecurityScan(**scan) for scan in response.data]

        if not scans:
            return {
                'scan_type': scan_type,
                'total_scans': 0,
                'success_rate': 0.0,
                'avg_risk_score': 0.0,
                'severity_distribution': {}
            }

        total_scans = len(scans)
        completed_scans = sum(1 for scan in scans if scan.status == 'completed')
        success_rate = (completed_scans / total_scans) * 100 if total_scans > 0 else 0.0

        completed_with_scores = [scan for scan in scans if scan.status == 'completed' and scan.risk_score is not None]
        avg_risk_score = sum(scan.risk_score for scan in completed_with_scores) / len(completed_with_scores) if completed_with_scores else 0.0

        # Calculate severity distribution
        severity_distribution = {}
        for scan in scans:
            if scan.severity:
                severity_distribution[scan.severity] = severity_distribution.get(scan.severity, 0) + 1

        return {
            'scan_type': scan_type,
            'total_scans': total_scans,
            'success_rate': round(success_rate, 2),
            'avg_risk_score': round(avg_risk_score, 2),
            'severity_distribution': severity_distribution
        }
    except Exception as e:
        print(f"Error getting scan type statistics for {scan_type}: {e}")
        return {
            'scan_type': scan_type,
            'total_scans': 0,
            'success_rate': 0.0,
            'avg_risk_score': 0.0,
            'severity_distribution': {}
        }