"""
Shared URL scanning utility for phishing detection

This module consolidates URL scanning logic used by both API endpoints
and Rasa actions, ensuring consistent behavior and response parsing.

Updated to use async httpx for non-blocking API calls.
"""
import httpx
import re
import ipaddress
import logging
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
from backend.utils.circuit_breaker import call_virustotal, CircuitBreakerOpenError

logger = logging.getLogger(__name__)

# API Key Configuration
try:
    from backend.core.config import settings
    VIRUSTOTAL_API_KEY = settings.virustotal_api_key if hasattr(settings, 'virustotal_api_key') else ""
except ImportError:
    try:
        from backend.core.config import settings
        VIRUSTOTAL_API_KEY = settings.virustotal_api_key if hasattr(settings, 'virustotal_api_key') else ""
    except ImportError:
        import os
        VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
        logger.info("Using environment variables for API keys")

# Warn if API key is missing
if not VIRUSTOTAL_API_KEY:
    logger.warning("VIRUSTOTAL_API_KEY not configured. URL scanning will be limited.")


def validate_url(url: str) -> bool:
    """
    Validates the structure and safety of a URL to prevent Server-Side Request 
    Forgery (SSRF) and path traversal attacks.

    Checks applied:
    1. Verify scheme is exclusively http or https.
    2. Confirm netloc and hostname are present.
    3. Exclude private IP subnets (RFC 1918) and loopback addresses.
    4. Exclude localhost aliases and file:// protocol links.

    Args:
        url (str): The raw URL to check.

    Returns:
        bool: True if the URL conforms to safety checks, False otherwise.
    """
    try:
        result = urlparse(url)

        # Only allow http and https schemes
        if result.scheme not in ['http', 'https']:
            return False

        # Check netloc exists
        if not result.netloc:
            return False

        # Extract hostname (separate from port)
        hostname = result.hostname
        if not hostname:
            return False

        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)

            # Prevent SSRF: block private and loopback IP addresses
            if ip.is_private or ip.is_loopback:
                return False

        except ValueError:
            # Hostname is a domain name, not a raw IP address.
            # Block common local domain aliases (localhost, etc.)
            hostname_lower = hostname.lower()
            if hostname_lower in ['localhost', 'localhost.localdomain']:
                return False

        # Block local file protocol indicators
        if result.scheme == 'file' or 'file://' in url:
            return False

        return True

    except Exception:
        return False


async def scan_url_virustotal_async(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Submits a URL to VirusTotal API and retrieves the scan analysis result (asynchronous).

    This process is wrapped in a Circuit Breaker pattern. It executes in 3 steps:
    1. Base64 encodes the URL and tries to GET an existing report (avoids consuming API credits).
    2. If no report is found, it POSTs the URL to initiate a new analysis.
    3. It polls the analysis endpoint periodically until engines complete scanning.

    Args:
        url (str): Safe URL to scan.
        timeout (int, optional): Connection timeout in seconds. Defaults to 10.

    Returns:
        Dict[str, Any]: Parsed API response or fallback payload on failure.
    """
    # SECURITY: Wrap execution with circuit breaker protection
    async def _scan_with_virustotal():
        # Double check URL safety first
        if not validate_url(url):
            return {
                "error": "Invalid URL format or security check failed",
                "scan_date": datetime.utcnow().isoformat(),
                "fallback": True
            }

        if not VIRUSTOTAL_API_KEY:
            logger.warning("VirusTotal API key not configured, using heuristic check")
            return {
                "error": "VirusTotal API key not configured",
                "message": "VirusTotal API key not configured. Using fallback heuristic check.",
                "fallback": True,
                "scan_date": datetime.utcnow().isoformat()
            }

        import base64
        import time
        import asyncio

        # VirusTotal requires URL identifier as base64 without trailing padding characters (=)
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
        headers = {
            "x-apikey": VIRUSTOTAL_API_KEY
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            # Step 1: Query for an existing report to minimize rate usage
            try:
                get_response = await client.get(
                    f"https://www.virustotal.com/api/v3/urls/{url_id}",
                    headers=headers
                )
                if get_response.status_code == 200:
                    res_json = get_response.json()
                    attributes = res_json.get('data', {}).get('attributes', {})
                    stats = attributes.get('last_analysis_stats', {})
                    total_engines = sum(stats.values()) if stats else 0
                    if total_engines > 0:
                        logger.info(f"VirusTotal report found for URL: {url} with {total_engines} scanned engines.")
                        return res_json
                    else:
                        logger.info(f"VirusTotal report found for URL: {url} but has 0 scanned engines. Requesting a new scan.")
                elif get_response.status_code == 404:
                    logger.info(f"VirusTotal report not found (404) for URL: {url}. Requesting a new scan.")
                else:
                    logger.warning(f"VirusTotal GET /urls/{{id}} returned status {get_response.status_code}")
            except httpx.TimeoutException:
                logger.error(f"VirusTotal GET /urls/{{id}} timeout")
            except httpx.RequestError as e:
                logger.error(f"VirusTotal GET /urls/{{id}} error: {e}")

            # Step 2: Request a fresh scan since no cached report exists
            try:
                submit_response = await client.post(
                    "https://www.virustotal.com/api/v3/urls",
                    headers=headers,
                    data={"url": url}
                )
            except httpx.TimeoutException:
                logger.error("VirusTotal API timeout")
                return {
                    "error": "API timeout",
                    "message": "VirusTotal service unavailable. Please try again later.",
                    "fallback": True,
                    "scan_date": datetime.utcnow().isoformat()
                }
            except httpx.RequestError as e:
                logger.error(f"VirusTotal API network error: {e}")
                return {
                    "error": f"Network error: {str(e)}",
                    "message": "VirusTotal service unavailable. Please try again later.",
                    "fallback": True,
                    "scan_date": datetime.utcnow().isoformat()
                }

            if submit_response.status_code not in (200, 201):
                logger.error(f"VirusTotal API error during submission: {submit_response.status_code}")
                return {
                    "error": f"API error: {submit_response.status_code}",
                    "message": "VirusTotal service unavailable. Please try again later.",
                    "fallback": True,
                    "scan_date": datetime.utcnow().isoformat()
                }

            # Step 3: Poll VirusTotal until analysis results populate
            poll_response = None
            poll_interval = 4
            max_poll_attempts = 8

            logger.info(f"Waiting {poll_interval} seconds before polling analysis results...")
            for attempt in range(max_poll_attempts):
                await asyncio.sleep(poll_interval)
                try:
                    logger.info(f"Polling VirusTotal GET /urls/{{id}} (attempt {attempt + 1}/{max_poll_attempts}) for URL: {url}")
                    poll_response = await client.get(
                        f"https://www.virustotal.com/api/v3/urls/{url_id}",
                        headers=headers
                    )
                    if poll_response.status_code == 200:
                        res_json = poll_response.json()
                        attributes = res_json.get('data', {}).get('attributes', {})
                        stats = attributes.get('last_analysis_stats', {})
                        total_engines = sum(stats.values()) if stats else 0
                        if total_engines > 0:
                            logger.info(f"VirusTotal analysis completed or in progress with {total_engines} engines on attempt {attempt + 1}")
                            return res_json
                        logger.info(f"VirusTotal analysis still has 0 engines scanned, retrying...")
                    else:
                        logger.error(f"VirusTotal API error getting results during polling: {poll_response.status_code}")
                except httpx.RequestError as e:
                    logger.error(f"VirusTotal API network error getting results during polling: {e}")

            # If polling did not complete in time, attempt to parse whatever exists in the final response
            if poll_response and poll_response.status_code == 200:
                try:
                    return poll_response.json()
                except Exception:
                    pass

            return {
                "error": "Analysis timed out or incomplete",
                "message": "VirusTotal analysis is taking longer than expected. Please try again in a moment.",
                "fallback": True,
                "scan_date": datetime.utcnow().isoformat()
            }

    try:
        return await call_virustotal(_scan_with_virustotal)
    except CircuitBreakerOpenError as circuit_error:
        logger.warning(f"⚡ VirusTotal circuit breaker is open: {circuit_error.detail}")
        return {
            "error": "VirusTotal service temporarily unavailable",
            "message": "VirusTotal API is experiencing issues. Circuit breaker is open to prevent cascading failures.",
            "fallback": True,
            "circuit_breaker_open": True,
            "scan_date": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Unexpected error in VirusTotal scan: {e}")
        return {
            "error": "VirusTotal scan failed",
            "message": f"Unexpected error: {str(e)}",
            "fallback": True,
            "scan_date": datetime.utcnow().isoformat()
        }


def scan_url_virustotal(url: str) -> Dict[str, Any]:
    """
    Submits a URL to VirusTotal API and retrieves the scan analysis result (synchronous).

    ⚠️ WARNING: Uses blocking network I/O. Prefer scan_url_virustotal_async() in async endpoints.

    Args:
        url (str): URL to scan.

    Returns:
        Dict[str, Any]: Parsed API response or fallback payload on failure.
    """
    if not validate_url(url):
        return {
            "error": "Invalid URL format or security check failed",
            "scan_date": datetime.utcnow().isoformat(),
            "fallback": True
        }

    if not VIRUSTOTAL_API_KEY:
        logger.warning("VirusTotal API key not configured, using heuristic check")
        return {
            "error": "VirusTotal API key not configured",
            "message": "VirusTotal API key not configured. Using fallback heuristic check.",
            "fallback": True,
            "scan_date": datetime.utcnow().isoformat()
        }

    import base64
    import time

    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    headers = {
        "x-apikey": VIRUSTOTAL_API_KEY
    }

    try:
        import requests
        get_response = requests.get(
            f"https://www.virustotal.com/api/v3/urls/{url_id}",
            headers=headers,
            timeout=10
        )
        if get_response.status_code == 200:
            res_json = get_response.json()
            attributes = res_json.get('data', {}).get('attributes', {})
            stats = attributes.get('last_analysis_stats', {})
            total_engines = sum(stats.values()) if stats else 0
            if total_engines > 0:
                logger.info(f"VirusTotal report found for URL: {url} with {total_engines} scanned engines.")
                return res_json
            else:
                logger.info(f"VirusTotal report found for URL: {url} but has 0 scanned engines. Requesting a new scan.")
        elif get_response.status_code == 404:
            logger.info(f"VirusTotal report not found (404) for URL: {url}. Requesting a new scan.")
        else:
            logger.warning(f"VirusTotal GET /urls/{{id}} returned status {get_response.status_code}")
    except requests.RequestException as e:
        logger.error(f"VirusTotal GET /urls/{{id}} error: {e}")

    try:
        submit_response = requests.post(
            "https://www.virustotal.com/api/v3/urls",
            headers=headers,
            data={"url": url},
            timeout=10
        )
    except requests.exceptions.Timeout:
        logger.error("VirusTotal API timeout")
        return {
            "error": "API timeout",
            "message": "VirusTotal service unavailable. Please try again later.",
            "fallback": True,
            "scan_date": datetime.utcnow().isoformat()
        }
    except requests.RequestException as e:
        logger.error(f"VirusTotal API network error: {e}")
        return {
            "error": f"Network error: {str(e)}",
            "message": "VirusTotal service unavailable. Please try again later.",
            "fallback": True,
            "scan_date": datetime.utcnow().isoformat()
        }

    if submit_response.status_code not in (200, 201):
        logger.error(f"VirusTotal API error during submission: {submit_response.status_code}")
        return {
            "error": f"API error: {submit_response.status_code}",
            "message": "VirusTotal service unavailable. Please try again later.",
            "fallback": True,
            "scan_date": datetime.utcnow().isoformat()
        }

    poll_response = None
    poll_interval = 4
    max_poll_attempts = 8

    logger.info(f"Waiting {poll_interval} seconds before polling analysis results...")
    for attempt in range(max_poll_attempts):
        time.sleep(poll_interval)
        try:
            logger.info(f"Polling VirusTotal GET /urls/{{id}} (attempt {attempt + 1}/{max_poll_attempts}) for URL: {url}")
            poll_response = requests.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers=headers,
                timeout=10
            )
            if poll_response.status_code == 200:
                res_json = poll_response.json()
                attributes = res_json.get('data', {}).get('attributes', {})
                stats = attributes.get('last_analysis_stats', {})
                total_engines = sum(stats.values()) if stats else 0
                if total_engines > 0:
                    logger.info(f"VirusTotal analysis completed or in progress with {total_engines} engines on attempt {attempt + 1}")
                    return res_json
                logger.info(f"VirusTotal analysis still has 0 engines scanned, retrying...")
            else:
                logger.error(f"VirusTotal API error getting results during polling: {poll_response.status_code}")
        except requests.RequestException as e:
            logger.error(f"VirusTotal API network error getting results during polling: {e}")

    if poll_response and poll_response.status_code == 200:
        try:
            return poll_response.json()
        except Exception:
            pass

    return {
        "error": "Analysis timed out or incomplete",
        "message": "VirusTotal analysis is taking longer than expected. Please try again in a moment.",
        "fallback": True,
        "scan_date": datetime.utcnow().isoformat()
    }


def parse_virustotal_results(result: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Parses raw VirusTotal API analysis stats into a clean, standardized format.

    Args:
        result (Dict[str, Any]): Raw JSON output from VirusTotal.
        url (str): The scanned URL.

    Returns:
        Dict[str, Any]: Unified phishing result model (risk_level, risk_score, reasons).
    """
    if 'error' in result:
        return {
            "url": url,
            "risk_level": "UNKNOWN",
            "risk_score": 0,
            "error": result.get('error'),
            "message": result.get('message', 'API lookup failed'),
            "scan_source": "virustotal",
            "fallback": result.get('fallback', False)
        }

    attributes = result.get('data', {}).get('attributes', {})
    stats = attributes.get('last_analysis_stats') or attributes.get('stats') or {}

    malicious = stats.get('malicious', 0)
    suspicious = stats.get('suspicious', 0)
    harmless = stats.get('harmless', 0)
    undetected = stats.get('undetected', 0)

    total_engines = malicious + suspicious + harmless + undetected

    if total_engines == 0:
        return {
            "url": url,
            "risk_level": "UNKNOWN",
            "risk_score": 0,
            "reasons": ["No security engines scanned this URL"],
            "recommendation": "Unable to determine URL safety",
            "scan_source": "virustotal",
            "message": "Scan completed but no results available",
            "stats": {
                "malicious": malicious,
                "suspicious": suspicious,
                "harmless": harmless,
                "undetected": undetected
            }
        }

    # Calculate overall risk percentage from reporting engines
    risk_percentage = ((malicious + suspicious) / total_engines) * 100

    # Categorize risk severity levels
    if malicious >= 5 or risk_percentage >= 50:
        risk_level = "HIGH"
        recommendation = "CẢNH BÁO: URL này đã được phát hiện độc hại bởi nhiều engine. KHÔNG nên truy cập."
    elif malicious >= 1 or risk_percentage >= 10:
        risk_level = "MEDIUM"
        recommendation = "CẢNH BÁO: URL này có một vài engine phát hiện độc hại. Hãy thận trọng."
    else:
        risk_level = "LOW"
        recommendation = "URL này có vẻ an toàn theo các engine quét. Tuy nhiên, luôn thận trọng."

    return {
        "url": url,
        "risk_level": risk_level,
        "risk_score": int(risk_percentage),
        "reasons": [
            f"{malicious} công cụ phát hiện độc hại",
            f"{suspicious} công cụ phát hiện nghi ngờ",
            f"Được quét bởi {total_engines} công cụ bảo mật"
        ],
        "recommendation": recommendation,
        "scan_source": "virustotal",
        "scan_date": attributes.get('last_analysis_date') or attributes.get('date'),
        "stats": {
            "malicious": malicious,
            "suspicious": suspicious,
            "harmless": harmless,
            "undetected": undetected
        }
    }


def basic_phishing_check(url: str, warning_message: str = "") -> Dict[str, Any]:
    """
    Applies local regex and string heuristics to assess phishing risk when 
    the external VirusTotal API is unreachable.

    Heuristics evaluated:
    - Keywords in domain (login, secure, bank, update).
    - direct IP address access.
    - Too many subdomains.

    Args:
        url (str): URL to scan.
        warning_message (str, optional): Custom message explaining fallback cause.

    Returns:
        Dict[str, Any]: Unified phishing result model.
    """
    suspicious_patterns = [
        r'https?://[^/]*login[^/]*\.',
        r'https?://[^/]*secure[^/]*\.',
        r'https?://[^/]*account[^/]*\.',
        r'https?://[^/]*verify[^/]*\.',
        r'https?://[^/]*update[^/]*\.',
        r'https?://[^/]*bank[^/]*\.',
    ]

    risk_score = 0
    reasons = []

    # Check for suspicious phishing terms in domain/netloc
    for pattern in suspicious_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            risk_score += 20
            reasons.append("Phát hiện mẫu URL đáng ngờ (ví dụ: login, secure...)")

    # Check if host is a raw IP address (typical for malicious temporary hosts)
    if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
        risk_score += 30
        reasons.append("Sử dụng địa chỉ IP trực tiếp thay vì tên miền")

    # Check for excessive subdomains
    if len(url.split('.')) > 4:
        risk_score += 10
        reasons.append("Cấu trúc chứa nhiều tên miền phụ đáng ngờ")

    # Evaluate Heuristic Risk Score
    if risk_score >= 50:
        risk_level = "HIGH"
        recommendation = "CẢNH BÁO: URL này có nhiều dấu hiệu lừa đảo. KHÔNG nên nhập thông tin nhạy cảm."
    elif risk_score >= 20:
        risk_level = "MEDIUM"
        recommendation = "CẢNH BÁO: URL này có một số đặc điểm đáng ngờ. Hãy kiểm tra kỹ trước khi tiếp tục."
    else:
        risk_level = "LOW"
        recommendation = "URL này có vẻ an toàn. Tuy nhiên, luôn thận trọng khi nhập thông tin cá nhân."

    return {
        "url": url,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reasons": reasons,
        "recommendation": recommendation,
        "scan_source": "pattern_matching",
        "message": warning_message or "Basic pattern matching (API unavailable)"
    }


def _process_phishing_scan_result(result: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Helper to route results through parser or fallback checks on API error"""
    if 'error' not in result:
        return parse_virustotal_results(result, url)

    error = result.get('error', '')
    if "Invalid URL format" in error:
        logger.warning(f"URL validation failed, not scanning: {error}")
        return result

    message = result.get('message', 'API unavailable')
    logger.warning(f"VirusTotal API failed, using fallback: {message}")
    return basic_phishing_check(url, message)


async def check_phishing_url_async(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Main entry point for async phishing URL checking.

    Args:
        url (str): Target URL.
        timeout (int, optional): Connection timeout. Defaults to 10.

    Returns:
        Dict[str, Any]: Final unified phishing check details.
    """
    try:
        result = await scan_url_virustotal_async(url, timeout)
        return _process_phishing_scan_result(result, url)
    except Exception as e:
        logger.error(f"Phishing check error: {e}")
        return basic_phishing_check(url, f"Scan error: {str(e)}")


def check_phishing_url(url: str) -> Dict[str, Any]:
    """
    Main entry point for synchronous phishing URL checking.

    Args:
        url (str): Target URL.

    Returns:
        Dict[str, Any]: Final unified phishing check details.
    """
    try:
        result = scan_url_virustotal(url)
        return _process_phishing_scan_result(result, url)
    except Exception as e:
        logger.error(f"Phishing check error: {e}")
        return basic_phishing_check(url, f"Scan error: {str(e)}")
