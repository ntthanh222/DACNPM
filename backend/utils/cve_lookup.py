"""
Shared CVE lookup utility

This module consolidates CVE lookup logic used by both API endpoints
and Rasa actions, ensuring consistent behavior and caching.

Protected by circuit breaker to prevent cascading failures from NIST NVD API.
"""
import requests
import httpx
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from backend.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)

# Circuit breaker for NIST NVD API protection
nist_nvd_circuit_breaker = CircuitBreaker(
    service_name="NIST_NVD",
    failure_threshold=5,      # Open circuit after 5 consecutive failures
    timeout=60,              # Try again after 60 seconds
    success_threshold=2,     # Need 2 successes to close circuit
    half_open_max_calls=3    # Max test calls in half-open state
)

# API Key Configuration
try:
    from backend.config import settings
    NIST_NVD_API_KEY = settings.nist_nvd_api_key if hasattr(settings, 'nist_nvd_api_key') else ""
except ImportError:
    import os
    NIST_NVD_API_KEY = os.getenv("NIST_NVD_API_KEY", "")
    logger.info("Using environment variables for API keys")

# Warn if API key is missing
if not NIST_NVD_API_KEY:
    logger.warning("NIST_NVD_API_KEY not configured. CVE lookup will be rate limited.")


def validate_cve_id(cve_id: str) -> bool:
    """
    Validate CVE ID format (e.g., CVE-2024-1234)

    Args:
        cve_id: CVE ID to validate

    Returns:
        bool: True if valid format, False otherwise
    """
    if not cve_id:
        return False

    # CVE ID pattern: CVE-YYYY-NNNN (or more digits)
    cve_pattern = r'^CVE-\d{4}-\d{4,}$'
    return bool(re.match(cve_pattern, cve_id.upper()))


def lookup_cve(cve_id: str) -> Dict[str, Any]:
    """
    Lookup CVE using NIST NVD API with validation and fallback

    NOTE: Circuit breaker protection requires async context. Use async_lookup_cve()
    for production. This sync version is provided for backward compatibility.

    Args:
        cve_id: CVE ID to lookup

    Returns:
        Dict with CVE data or error information
    """
    # Ensure CVE ID is in correct format
    if not cve_id.upper().startswith('CVE-'):
        cve_id = f"CVE-{cve_id}"
    else:
        cve_id = cve_id.upper()

    # Validate CVE ID format
    if not validate_cve_id(cve_id):
        return {
            "error": "Invalid CVE ID format. Expected format: CVE-YYYY-NNNN",
            "message": "Invalid CVE ID format. Expected format: CVE-YYYY-NNNN (e.g., CVE-2024-1234).",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }

    # Build API URL with or without API key
    if not NIST_NVD_API_KEY:
        logger.warning("NIST_NVD_API_KEY not configured, using rate-limited public endpoint")
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
    else:
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}&apiKey={NIST_NVD_API_KEY}"

    try:
        response = requests.get(url, timeout=10)  # Add timeout to prevent hanging
    except requests.exceptions.Timeout:
        logger.error("NIST NVD API timeout")
        return {
            "error": "API timeout",
            "message": "NIST NVD service unavailable. Please try again later.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }
    except requests.RequestException as e:
        logger.error(f"NIST NVD API network error: {e}")
        return {
            "error": f"Network error: {str(e)}",
            "message": "NIST NVD service unavailable. Please try again later.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }

    if response.status_code == 200:
        return response.json()
    if response.status_code == 403:
        logger.warning("NIST NVD API rate limit exceeded")
        return {
            "error": "API rate limit exceeded",
            "message": "NIST NVD API rate limit exceeded. Please try again later or provide an API key.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id,
            "rate_limited": True
        }
    if response.status_code == 404:
        logger.warning(f"CVE not found: {cve_id}")
        return {
            "error": "CVE not found",
            "message": f"CVE {cve_id} not found in NIST NVD database.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }
    logger.error(f"NIST NVD API error: {response.status_code}")
    return {
        "error": f"API error: {response.status_code}",
        "message": "Failed to lookup CVE. Please try again later.",
        "fallback": True,
        "lookup_date": datetime.now().isoformat(),
        "cve_id": cve_id
    }


def parse_cve_response(result: Dict[str, Any], cve_id: str) -> Dict[str, Any]:
    """
    Parse NIST NVD API response into standardized format

    Args:
        result: Raw NIST NVD API response
        cve_id: The CVE ID that was looked up

    Returns:
        Dict with standardized CVE information
    """
    # Check for API errors
    if 'error' in result:
        return {
            "cve_id": cve_id,
            "response_data": {},
            "cvss_score": None,
            "severity": None,
            "error": result.get('error'),
            "message": result.get('message', 'API lookup failed'),
            "is_cached": False,
            "rate_limited": result.get('rate_limited', False)
        }

    # Extract CVE data
    cve_items = result.get('vulnerabilities', [])
    if not cve_items:
        return {
            "cve_id": cve_id,
            "response_data": {},
            "cvss_score": None,
            "severity": None,
            "error": "CVE not found",
            "message": f"CVE {cve_id} not found in NIST NVD database.",
            "is_cached": False
        }

    cve_data = cve_items[0].get('cve', {})

    # Get description (prefer English)
    descriptions = cve_data.get('descriptions', [])
    description = "No description available"
    for desc in descriptions:
        if desc.get('lang') == 'en':
            description = desc.get('value', '')
            break

    # Get CVSS v3.1 score
    metrics = cve_data.get('metrics', {})
    cvss_v31 = metrics.get('cvssMetricV31', [])
    cvss_score = None
    severity = None

    if cvss_v31:
        cvss_data = cvss_v31[0].get('cvssData', {})
        cvss_score = str(cvss_data.get('baseScore', 'N/A'))
        severity = cvss_data.get('baseSeverity', 'Unknown').lower()

    # Get references
    references = cve_data.get('references', [])
    ref_urls = [ref.get('url', '') for ref in references if ref.get('url')]

    # Get affected products
    affected_products = []
    configurations = cve_data.get('configurations', [])
    for config in configurations:
        for node in config.get('nodes', []):
            for cpe_match in node.get('cpeMatch', []):
                if cpe_match.get('vulnerable'):
                    cpe_uri = cpe_match.get('criteria', '')
                    affected_products.append(cpe_uri)

    return {
        "cve_id": cve_id,
        "response_data": {
            "description": description,
            "cvss_score": cvss_score,
            "severity": severity,
            "references": ref_urls,
            "affected_products": affected_products[:10],  # Limit to first 10
            "published_date": cve_data.get('published', ''),
            "modified_date": cve_data.get('lastModified', ''),
            "source": "NIST NVD"
        },
        "cvss_score": cvss_score,
        "severity": severity,
        "is_cached": False
    }


def check_cve(cve_id: str) -> Dict[str, Any]:
    """
    Main entry point for CVE lookup (synchronous version)

    Args:
        cve_id: CVE ID to lookup

    Returns:
        Dict with standardized CVE information
    """
    try:
        # Call NIST NVD API
        result = lookup_cve(cve_id)

        # Parse response
        return parse_cve_response(result, cve_id)

    except Exception as e:
        logger.error(f"CVE lookup error: {e}")
        return {
            "cve_id": cve_id,
            "response_data": {},
            "cvss_score": None,
            "severity": None,
            "error": "lookup_failed",
            "message": f"CVE lookup failed: {str(e)}",
            "is_cached": False
        }


async def async_lookup_cve(cve_id: str) -> Dict[str, Any]:
    """
    Async CVE lookup using NIST NVD API with circuit breaker protection

    This is the recommended version for production use as it includes
    circuit breaker protection to prevent cascading failures.

    Args:
        cve_id: CVE ID to lookup

    Returns:
        Dict with CVE data or error information
    """
    # Ensure CVE ID is in correct format
    if not cve_id.upper().startswith('CVE-'):
        cve_id = f"CVE-{cve_id}"
    else:
        cve_id = cve_id.upper()

    # Validate CVE ID format
    if not validate_cve_id(cve_id):
        return {
            "error": "Invalid CVE ID format. Expected format: CVE-YYYY-NNNN",
            "message": "Invalid CVE ID format. Expected format: CVE-YYYY-NNNN (e.g., CVE-2024-1234).",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }

    async def fetch_nvd_data():
        """Internal function to fetch CVE data from NIST NVD API"""
        import httpx

        # Build API URL with or without API key
        if not NIST_NVD_API_KEY:
            logger.warning("NIST_NVD_API_KEY not configured, using rate-limited public endpoint")
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        else:
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}&apiKey={NIST_NVD_API_KEY}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

        # Handle non-success responses as exceptions for circuit breaker
        if response.status_code == 403:
            raise httpx.HTTPStatusError(
                f"API rate limit exceeded - {response.status_code}",
                request=response.request,
                response=response
            )
        if response.status_code == 404:
            # 404 is a valid response (CVE not found), not a failure
            return response
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"API returned status code {response.status_code}",
                request=response.request,
                response=response
            )

        return response

    try:
        # Use circuit breaker to protect against cascading failures
        response = await nist_nvd_circuit_breaker.call(fetch_nvd_data)

        # Handle different response types
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            logger.warning(f"CVE not found: {cve_id}")
            return {
                "error": "CVE not found",
                "message": f"CVE {cve_id} not found in NIST NVD database.",
                "fallback": True,
                "lookup_date": datetime.now().isoformat(),
                "cve_id": cve_id
            }
        # This shouldn't happen, but handle it anyway
        return {
            "error": f"API error: {response.status_code}",
            "message": "Failed to lookup CVE. Please try again later.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }

    except CircuitBreakerOpenError as e:
        logger.warning(f"NIST NVD circuit breaker is open: {e}")
        return {
            "error": "Service temporarily unavailable",
            "message": "NIST NVD dịch vụ tạm thời không khả dụng do lỗi hệ thống. Vui lòng thử lại sau vài phút.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id,
            "circuit_breaker_active": True
        }

    except httpx.TimeoutException:
        logger.error("NIST NVD API timeout")
        return {
            "error": "API timeout",
            "message": "NIST NVD service unavailable. Please try again later.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }
    except httpx.HTTPStatusError as e:
        if "rate limit" in str(e):
            logger.warning("NIST NVD API rate limit exceeded")
            return {
                "error": "API rate limit exceeded",
                "message": "NIST NVD API rate limit exceeded. Please try again later or provide an API key.",
                "fallback": True,
                "lookup_date": datetime.now().isoformat(),
                "cve_id": cve_id,
                "rate_limited": True
            }
        else:
            logger.error(f"NIST NVD API HTTP error: {e}")
            return {
                "error": f"HTTP error: {str(e)}",
                "message": "NIST NVD service unavailable. Please try again later.",
                "fallback": True,
                "lookup_date": datetime.now().isoformat(),
                "cve_id": cve_id
            }
    except httpx.RequestError as e:
        logger.error(f"NIST NVD API network error: {e}")
        return {
            "error": f"Network error: {str(e)}",
            "message": "NIST NVD service unavailable. Please try again later.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }
    except Exception as e:
        logger.error(f"CVE lookup unexpected error: {e}")
        return {
            "error": "Unexpected error",
            "message": "NIST NVD service unavailable. Please try again later.",
            "fallback": True,
            "lookup_date": datetime.now().isoformat(),
            "cve_id": cve_id
        }


async def async_check_cve(cve_id: str) -> Dict[str, Any]:
    """
    Async main entry point for CVE lookup with circuit breaker protection

    This is the recommended version for production use.

    Args:
        cve_id: CVE ID to lookup

    Returns:
        Dict with standardized CVE information
    """
    try:
        # Call NIST NVD API with circuit breaker protection
        result = await async_lookup_cve(cve_id)

        # Parse response
        return parse_cve_response(result, cve_id)

    except Exception as e:
        logger.error(f"Async CVE lookup error: {e}")
        return {
            "cve_id": cve_id,
            "response_data": {},
            "cvss_score": None,
            "severity": None,
            "error": "lookup_failed",
            "message": f"CVE lookup failed: {str(e)}",
            "is_cached": False
        }
