"""
Reports API for exporting security scan data

Xuất báo cáo lịch sử quét bảo mật ra CSV/PDF.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import csv
import io
from uuid import UUID
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.database.connection import supabase_admin
from backend.api.deps import get_optional_user_id, require_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize rate limiter for export endpoints
limiter = Limiter(key_func=get_remote_address)


class ReportRequest(BaseModel):
    format: str = "csv"  # csv or pdf (future)
    date_from: Optional[str] = None  # ISO date string
    date_to: Optional[str] = None  # ISO date string
    scan_type: Optional[str] = None  # url_scan, password_check, or all


@router.get("/security-scans/export")
@limiter.limit("10/minute")  # Rate limit: 10 exports per minute per user
def export_security_scans_report(
    request: Request,
    format: str = "csv",
    scan_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """
    Xuất báo cáo lịch sử quét bảo mật ra CSV với giới hạn tốc độ.

    Query params:
        format: csv (default)
        scan_type: url_scan, password_check, hoặc all (default)
        date_from: Ngày bắt đầu (ISO format: 2024-01-01)
        date_to: Ngày kết thúc (ISO format: 2024-12-31)

    Rate Limit: 10 requests per minute per user
    Date Range Limit: Maximum 1 year
    """
    try:
        # VALIDATE: Check date range to prevent excessive data exports
        if date_from and date_to:
            try:
                dt_from = datetime.fromisoformat(date_from)
                dt_to = datetime.fromisoformat(date_to)
                date_range = (dt_to - dt_from).days

                # Limit date range to prevent excessive data exports
                if date_range > 365:  # Maximum 1 year range
                    raise HTTPException(
                        status_code=400,
                        detail="Date range cannot exceed 1 year. Please use a smaller date range."
                    )
            except ValueError as e:
                if "ISO format" in str(e):
                    raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")
                raise

        # Build Supabase query
        query = supabase_admin.table('security_scans').select('*')

        # Always filter by authenticated user
        query = query.eq('user_id', str(current_user_id))

        # Filter by scan type
        if scan_type and scan_type != 'all':
            query = query.eq('scan_type', scan_type)

        # Filter by date range
        if date_from:
            try:
                dt_from = datetime.fromisoformat(date_from)
                query = query.gte('scan_timestamp', dt_from.isoformat())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO format (YYYY-MM-DD)")

        if date_to:
            try:
                dt_to = datetime.fromisoformat(date_to)
                # Add 1 day to include the end date
                dt_to = dt_to + timedelta(days=1)
                query = query.lt('scan_timestamp', dt_to.isoformat())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO format (YYYY-MM-DD)")

        # Execute query with order by timestamp descending and limit
        result = query.order('scan_timestamp', desc=True).limit(5000).execute()

        scans = result.data

        if not scans:
            raise HTTPException(status_code=404, detail="No security scan data found for the specified criteria")

        # Generate CSV
        if format.lower() == 'csv':
            return _generate_csv_report(scans)
        else:
            raise HTTPException(status_code=400, detail=f"Format '{format}' not supported. Use 'csv'.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export report error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")


def _generate_csv_report(scans: List[dict]) -> StreamingResponse:
    """
    Generate CSV report from security scan data.

    Args:
        scans: List of security scan records

    Returns:
        StreamingResponse with CSV file
    """
    # Create CSV buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Timestamp',
        'Scan Type',
        'Target',
        'Risk Score',
        'Severity',
        'Status',
        'Source'
    ])

    # Write data rows
    for scan in scans:
        timestamp = scan.get('scan_timestamp', 'N/A')
        scan_type = scan.get('scan_type', 'N/A')
        target = scan.get('target', 'N/A')

        # Extract risk_score and severity from scan_result if available
        scan_result = scan.get('scan_result', {})
        if isinstance(scan_result, dict):
            risk_score = scan_result.get('risk_score', scan.get('risk_score', 'N/A'))
            severity = scan_result.get('status', scan.get('severity', 'N/A'))
            scan_source = scan_result.get('scan_source', scan_result.get('source', 'N/A'))
        else:
            risk_score = scan.get('risk_score', 'N/A')
            severity = scan.get('severity', 'N/A')
            scan_source = 'N/A'

        status = scan.get('status', 'N/A')

        # Format timestamp
        try:
            if timestamp != 'N/A':
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass

        # Write row
        writer.writerow([
            timestamp,
            scan_type,
            target,
            risk_score,
            severity,
            status,
            scan_source
        ])

    # Prepare response
    output.seek(0)
    csv_data = output.getvalue()

    # Generate filename with timestamp
    filename = f"security_scans_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_data.encode('utf-8-sig')),  # UTF-8 with BOM for Excel compatibility
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@router.get("/stats")
def get_export_stats(
    current_user_id: UUID = Depends(require_current_user_id)
):
    """
    Get export statistics for dashboard display.

    Returns:
        Dict with total scans, breakdown by type, and date range info
    """
    try:
        query = supabase_admin.table('security_scans').select('scan_type, scan_timestamp')

        # Always filter by authenticated user
        query = query.eq('user_id', str(current_user_id))

        result = query.execute()
        scans = result.data

        # Calculate statistics
        total_scans = len(scans)
        url_scans = sum(1 for s in scans if s.get('scan_type') == 'url_scan')
        password_checks = sum(1 for s in scans if s.get('scan_type') == 'password_check')

        # Get date range
        if scans:
            timestamps = [s.get('scan_timestamp') for s in scans if s.get('scan_timestamp')]
            if timestamps:
                oldest = min(timestamps)
                newest = max(timestamps)
            else:
                oldest = newest = None
        else:
            oldest = newest = None

        return {
            'total_scans': total_scans,
            'url_scans': url_scans,
            'password_checks': password_checks,
            'date_range': {
                'oldest': oldest,
                'newest': newest
            }
        }

    except Exception as e:
        logger.error(f"Get export stats error: {e}")
        return {
            'total_scans': 0,
            'url_scans': 0,
            'password_checks': 0,
            'date_range': {
                'oldest': None,
                'newest': None
            }
        }
