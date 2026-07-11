"""
Input validation and sanitization utilities.

Provides functions to validate and sanitize user input to prevent security vulnerabilities.
"""

import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_PASSWORD_STRENGTH_LEVELS = (
    (80, 'VERY_STRONG'),
    (60, 'STRONG'),
    (40, 'MEDIUM'),
    (20, 'WEAK'),
)


def _get_password_strength(strength_score: int) -> str:
    for minimum_score, strength in _PASSWORD_STRENGTH_LEVELS:
        if strength_score >= minimum_score:
            return strength
    return 'TOO_WEAK'


def validate_cve_id(cve_id: str) -> Dict[str, Any]:
    """
    Validate CVE ID format.

    Args:
        cve_id: CVE ID string to validate

    Returns:
        Dict with validation result and cleaned CVE ID
    """
    if not cve_id or not isinstance(cve_id, str):
        return {
            'valid': False,
            'error': 'CVE ID must be a non-empty string',
            'cleaned_cve': None
        }

    # Remove whitespace and convert to uppercase
    cve_id = cve_id.strip().upper()

    # Validate CVE ID format: CVE-YYYY-NNNN
    pattern = r'^CVE-\d{4}-\d{4,}$'
    if not re.match(pattern, cve_id):
        return {
            'valid': False,
            'error': f'Invalid CVE ID format. Expected format: CVE-YYYY-NNNN (e.g., CVE-2024-1234)',
            'cleaned_cve': None
        }

    return {
        'valid': True,
        'error': None,
        'cleaned_cve': cve_id
    }


def validate_url(url: str) -> Dict[str, Any]:
    """
    Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        Dict with validation result and cleaned URL
    """
    if not url or not isinstance(url, str):
        return {
            'valid': False,
            'error': 'URL must be a non-empty string',
            'cleaned_url': None
        }

    # Remove whitespace
    url = url.strip()

    # Basic URL validation
    try:
        from urllib.parse import urlparse
        result = urlparse(url)

        if not all([result.scheme, result.netloc]):
            return {
                'valid': False,
                'error': 'Invalid URL format. Must include scheme (http:// or https://)',
                'cleaned_url': None
            }

        # Only allow http and https
        if result.scheme not in ['http', 'https']:
            return {
                'valid': False,
                'error': 'URL must use http:// or https:// protocol',
                'cleaned_url': None
            }

        return {
            'valid': True,
            'error': None,
            'cleaned_url': url
        }

    except Exception as e:
        return {
            'valid': False,
            'error': f'URL validation failed: {str(e)}',
            'cleaned_url': None
        }


def validate_password(password: str, min_length: int = 8) -> Dict[str, Any]:
    """
    Validate password strength.

    Args:
        password: Password string to validate
        min_length: Minimum required length

    Returns:
        Dict with validation result and password strength score
    """
    if not password or not isinstance(password, str):
        return {
            'valid': False,
            'error': 'Password must be a non-empty string',
            'strength': None,
            'strength_score': 0
        }

    # Length validation
    if len(password) < min_length:
        return {
            'valid': False,
            'error': f'Password must be at least {min_length} characters long',
            'strength': 'TOO_SHORT',
            'strength_score': 0
        }

    # Security checks
    checks = {
        'has_upper': bool(re.search(r'[A-Z]', password)),
        'has_lower': bool(re.search(r'[a-z]', password)),
        'has_digit': bool(re.search(r'\d', password)),
        'has_special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    }

    # Calculate strength score (0-100)
    strength_score = sum(checks.values()) * 20
    if len(password) >= 12:
        strength_score += 10
    if len(password) >= 16:
        strength_score += 10

    strength = _get_password_strength(strength_score)

    # Return validation result
    return {
        'valid': True,
        'error': None,
        'strength': strength,
        'strength_score': strength_score,
        'checks': checks,
        'password_length': len(password)
    }


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize input text to prevent XSS and injection attacks.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ''

    # Remove HTML tags and script tags
    text = re.sub(r'<[^>]*>', '', text)

    # Remove script tags
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';']
    for char in dangerous_chars:
        text = text.replace(char, '')

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def validate_search_query(query: str, min_length: int = 2, max_length: int = 200) -> Dict[str, Any]:
    """
    Validate search query.

    Args:
        query: Search query string
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Dict with validation result and sanitized query
    """
    if not query or not isinstance(query, str):
        return {
            'valid': False,
            'error': 'Search query must be a non-empty string',
            'sanitized_query': None
        }

    # Sanitize input
    sanitized = sanitize_input(query, max_length)

    # Validate length
    if len(sanitized) < min_length:
        return {
            'valid': False,
            'error': f'Search query must be at least {min_length} characters',
            'sanitized_query': None
        }

    if len(sanitized) > max_length:
        return {
            'valid': False,
            'error': f'Search query cannot exceed {max_length} characters',
            'sanitized_query': None
        }

    return {
        'valid': True,
        'error': None,
        'sanitized_query': sanitized
    }


def validate_pagination_params(page: int, page_size: int, max_page_size: int = 100) -> Dict[str, Any]:
    """
    Validate pagination parameters.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Dict with validated parameters
    """
    # Default values
    page = max(1, page) if page else 1
    page_size = min(max_page_size, page_size) if page_size else 20

    return {
        'valid': True,
        'error': None,
        'page': page,
        'page_size': page_size,
        'offset': (page - 1) * page_size
    }


def validate_api_key(api_key: str, required_prefix: str = 'Bearer ') -> Dict[str, Any]:
    """
    Validate API key format.

    Args:
        api_key: API key string to validate
        required_prefix: Expected prefix

    Returns:
        Dict with validation result
    """
    if not api_key or not isinstance(api_key, str):
        return {
            'valid': False,
            'error': 'API key must be provided',
            'cleaned_key': None
        }

    # Check for required prefix
    if not api_key.startswith(required_prefix):
        return {
            'valid': False,
            'error': f'API key must start with "{required_prefix}"',
            'cleaned_key': None
        }

    # Remove prefix for storage
    cleaned_key = api_key[len(required_prefix):]

    return {
        'valid': True,
        'error': None,
        'cleaned_key': cleaned_key
    }


def validate_email(email: str) -> Dict[str, Any]:
    """
    Validate email format.

    Args:
        email: Email string to validate

    Returns:
        Dict with validation result and cleaned email
    """
    if not email or not isinstance(email, str):
        return {
            'valid': False,
            'error': 'Email must be provided',
            'cleaned_email': None
        }

    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email.strip()):
        return {
            'valid': False,
            'error': 'Invalid email format',
            'cleaned_email': None
        }

    return {
        'valid': True,
        'error': None,
        'cleaned_email': email.strip().lower()
    }
