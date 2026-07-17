import requests
import re
import hashlib
import math
import os
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from uuid import UUID

# Configure logging
logger = logging.getLogger(__name__)


def _is_missing_is_deleted_error(error: Exception) -> bool:
    message = str(error).lower()
    return "is_deleted" in message and ("does not exist" in message or "could not find" in message)


def _validate_uuid(uuid_string: Optional[str]) -> bool:
    """
    Validate if string is valid UUID format

    Args:
        uuid_string: String to validate

    Returns:
        bool: True if valid UUID format, False otherwise
    """
    if not uuid_string:
        return False
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False

# API Key Configuration - Support both backend config and environment variables
try:
    from backend.config import settings
    VIRUSTOTAL_API_KEY = settings.virustotal_api_key if hasattr(settings, 'virustotal_api_key') else ""
    NIST_NVD_API_KEY = settings.nist_nvd_api_key if hasattr(settings, 'nist_nvd_api_key') else ""
except ImportError:
    # Fallback to environment variables
    VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
    NIST_NVD_API_KEY = os.getenv("NIST_NVD_API_KEY", "")
    logger.info("Using environment variables for API keys")

# Warn if API keys are missing
if not VIRUSTOTAL_API_KEY:
    logger.warning("VIRUSTOTAL_API_KEY not configured. URL scanning will be limited.")
if not NIST_NVD_API_KEY:
    logger.warning("NIST_NVD_API_KEY not configured. CVE lookup will be limited.")

from backend.utils.url_scanner import validate_url, scan_url_virustotal
from backend.utils.cve_lookup import validate_cve_id, lookup_cve
from backend.utils.password_checker import calculate_password_entropy

def get_security_news(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch latest security news from various sources
    Integrates with Phase 1 database for enhanced functionality
    """
    try:
        # Try to get recent news from database first
        from backend.database.connection import supabase
        from datetime import datetime, timedelta

        # Get news from the last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        try:
            response = supabase.table('news_articles').select('*')\
                .eq('is_deleted', False)\
                .gte('published_at', week_ago.isoformat())\
                .order('published_at', desc=True).limit(limit).execute()
        except Exception as e:
            if not _is_missing_is_deleted_error(e):
                raise
            response = supabase.table('news_articles').select('*')\
                .gte('published_at', week_ago.isoformat())\
                .order('published_at', desc=True).limit(limit).execute()

        if response.data and len(response.data) >= limit:
            return [
                {
                    "title": item.get('title', 'No title'),
                    "url": item.get('url', ''),
                    "source": item.get('source', 'Unknown'),
                    "summary": item.get('description', item.get('summary', 'No summary available')),
                    "published_at": item.get('published_at', '')
                }
                for item in response.data[:limit]
            ]

        # Fallback to external sources if database doesn't have enough news
        external_news = []

        # RSS feeds could be integrated here for real-time news
        # For now, return some sample security news items
        sample_news = [
            {
                "title": "Critical Vulnerability Discovered in Popular Software",
                "url": "https://example.com/security-news-1",
                "source": "Security Advisory",
                "summary": "A critical vulnerability has been discovered that could allow remote code execution. Users are advised to update immediately.",
                "published_at": datetime.now().isoformat()
            },
            {
                "title": "New Phishing Campaign Targeting Financial Institutions",
                "url": "https://example.com/security-news-2",
                "source": "Threat Intelligence",
                "summary": "Security researchers have identified a sophisticated phishing campaign targeting major financial institutions worldwide.",
                "published_at": (datetime.now() - timedelta(hours=6)).isoformat()
            },
            {
                "title": "Zero-Day Vulnerability Under Active Exploitation",
                "url": "https://example.com/security-news-3",
                "source": "CVE Database",
                "summary": "A zero-day vulnerability is being actively exploited in the wild. Patches are not yet available.",
                "published_at": (datetime.now() - timedelta(hours=12)).isoformat()
            }
        ]

        return sample_news[:limit]

    except Exception as e:
        # Return error information but still provide some helpful content
        return [
            {
                "title": "Unable to fetch security news",
                "url": "",
                "source": "System",
                "summary": f"Error fetching security news: {str(e)}. Please try again later.",
                "published_at": datetime.now().isoformat()
            }
        ]

def create_security_scan_record(user_id: str, scan_type: str, target: str, scan_result: Dict[str, Any]) -> bool:
    """
    Create a security scan record in the database (Phase 1 integration)
    """
    try:
        from backend.database.connection import supabase_admin
        from backend.database.models import SecurityScanCreate
        import uuid

        # Validate user_id is UUID format before database insert
        if not _validate_uuid(user_id):
            logger.warning(f"Invalid user_id format (not UUID): {user_id}. Skipping database insert.")
            return False

        # Create scan record with Phase 1 database integration
        scan_data = {
            "user_id": user_id,
            "scan_type": scan_type,
            "target": target,
            "scan_result": scan_result,
            "status": "completed",
            "scan_metadata": {
                "initiated_by": "user",
                "scan_engine": "cybersec-assistant-v2",
                "scan_duration": "unknown"
            }
        }

        # Extract risk_score and severity from scan_result if available
        # (Calculated by url_scanner.py for consistency with REST API)
        if "risk_score" in scan_result:
            scan_data["risk_score"] = scan_result["risk_score"]
        if "severity" in scan_result:
            scan_data["severity"] = scan_result["severity"]

        response = supabase_admin.table('security_scans').insert(scan_data).execute()
        return len(response.data) > 0

    except Exception as e:
        print(f"Error creating security scan record: {e}")
        return False

def cache_cve_lookup(cve_id: str, cve_data: Dict[str, Any]) -> bool:
    """
    Cache CVE lookup result in database (Phase 1 integration)
    """
    try:
        from backend.database.connection import supabase
        from datetime import datetime, timedelta

        # Extract CVSS score and severity from CVE data
        cvss_score = None
        severity = None

        if "vulnerabilities" in cve_data and cve_data["vulnerabilities"]:
            cve_item = cve_data["vulnerabilities"][0].get("cve", {})
            metrics = cve_item.get("metrics", {})

            # Try CVSS v3.1 first, then v2.0
            cvss_v31 = metrics.get("cvssMetricV31", [])
            cvss_v20 = metrics.get("cvssMetricV2", [])

            if cvss_v31:
                cvss_data = cvss_v31[0].get("cvssData", {})
                cvss_score = str(cvss_data.get("baseScore", "N/A"))
                severity = cvss_data.get("baseSeverity", "unknown").lower()
            elif cvss_v20:
                cvss_data = cvss_v20[0].get("cvssData", {})
                cvss_score = str(cvss_data.get("baseScore", "N/A"))
                # Map v2.0 severity to standard values
                severity_mapping = {
                    "LOW": "low",
                    "MEDIUM": "medium",
                    "HIGH": "high"
                }
                severity = severity_mapping.get(cvss_data.get("baseSeverity", "unknown").upper(), "unknown")

        # Create cache entry with 24-hour TTL
        cache_data = {
            "cve_id": cve_id.upper(),
            "query_data": {"queried_at": datetime.now().isoformat()},
            "response_data": cve_data,
            "cvss_score": cvss_score,
            "severity": severity,
            "cache_expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "query_count": 1,
            "last_accessed": datetime.now().isoformat()
        }

        response = supabase.table('cve_lookups').insert(cache_data).execute()
        return len(response.data) > 0

    except Exception as e:
        print(f"Error caching CVE lookup: {e}")
        return False

def get_cached_cve(cve_id: str) -> Optional[Dict[str, Any]]:
    """
    Get cached CVE lookup result (Phase 1 integration)
    """
    try:
        from backend.database.connection import supabase

        # Check cache first
        response = supabase.table('cve_lookups').select('*').eq('cve_id', cve_id.upper()).execute()

        if response.data:
            cached_data = response.data[0]

            # Check if cache is still valid
            from datetime import datetime
            expires_at = datetime.fromisoformat(cached_data['cache_expires_at'].replace('Z', '+00:00'))

            if expires_at > datetime.now():
                # Update access tracking
                supabase.table('cve_lookups').update({
                    "last_accessed": datetime.now().isoformat(),
                    "query_count": cached_data['query_count'] + 1
                }).eq('cve_id', cve_id.upper()).execute()

                return {
                    "response_data": cached_data['response_data'],
                    "cvss_score": cached_data.get('cvss_score'),
                    "severity": cached_data.get('severity'),
                    "is_cached": True
                }

        return None

    except Exception as e:
        print(f"Error getting cached CVE: {e}")
        return None
