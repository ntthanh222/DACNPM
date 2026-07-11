"""
Shared password strength checking utility

This module consolidates password validation logic used by both API endpoints
and Rasa actions, ensuring consistent behavior and response formatting.

Updated to use async httpx for non-blocking API calls.
"""
import hashlib
import math
import httpx
import logging
from typing import Dict, Any, List, Optional
from backend.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)

# Circuit breaker for HaveIBeenPwned API protection
hibp_circuit_breaker = CircuitBreaker(
    service_name="HaveIBeenPwned",
    failure_threshold=5,      # Open circuit after 5 consecutive failures
    timeout=60,              # Try again after 60 seconds
    success_threshold=2,     # Need 2 successes to close circuit
    half_open_max_calls=3    # Max test calls in half-open state
)

_ENTROPY_LEVELS = (
    (28, "instant", "very_weak", 0),
    (36, "< 1 minute", "weak", 20),
    (43, "< 1 hour", "fair", 40),
    (50, "< 1 day", "strong", 60),
    (60, "< 1 month", "very_strong", 80),
    (80, "< 1 year", "excellent", 100),
)


def _get_entropy_assessment(entropy: float) -> tuple[str, str, int]:
    for threshold, crack_time, strength, score in _ENTROPY_LEVELS:
        if entropy < threshold:
            return crack_time, strength, score
    return "centuries", "excellent", 100


def _get_strength_display(score: int) -> tuple[str, str]:
    if score >= 80:
        return "RẤT MẠNH", "green"
    if score >= 60:
        return "MẠNH", "blue"
    if score >= 40:
        return "TRUNG BÌNH", "yellow"
    return "YẾU", "red"


def _build_password_strength_result(
    entropy_result: Dict[str, Any],
    breached_result: Dict[str, Any]
) -> Dict[str, Any]:
    score = entropy_result.get('score', 0)
    strength_text, color = _get_strength_display(score)
    breached_count = breached_result.get('count') if breached_result.get('breached') else None
    breached_warning = breached_result.get('message') if breached_result.get('breached') else None
    feedback = entropy_result.get('recommendations', [])
    all_feedback = list(feedback) if feedback else []

    if breached_warning:
        all_feedback.insert(0, breached_warning)

    return {
        "password_length": entropy_result.get('length', 0),
        "strength_score": score,
        "strength": strength_text,
        "strength_color": color,
        "crack_time": entropy_result.get('crack_time', 'instant'),
        "feedback": all_feedback,
        "breached_count": breached_count,
        "entropy": entropy_result.get('entropy', 0),
        "charset_size": entropy_result.get('charset_size', 0),
        "has_upper": entropy_result.get('has_upper', False),
        "has_lower": entropy_result.get('has_lower', False),
        "has_digit": entropy_result.get('has_digit', False),
        "has_special": entropy_result.get('has_special', False),
        "suggestions": [
            "Sử dụng ít nhất 12 ký tự",
            "Kết hợp chữ hoa, thường, số và ký tự đặc biệt",
            "Tránh sử dụng thông tin cá nhân",
            "Sử dụng trình quản lý mật khẩu",
            "Không sử dụng password đã bị lộ" if breached_count else ""
        ],
        "scan_source": "entropy_check" + ("+breached_check" if breached_result.get('breached') else "")
    }


def calculate_password_entropy(password: str) -> Dict[str, Any]:
    """
    Calculate password entropy and strength assessment

    Args:
        password: Password to analyze

    Returns:
        Dict with entropy analysis including score, strength, crack time
    """
    if not password:
        return {
            "error": "Mật khẩu không được để trống",
            "entropy": 0,
            "strength": "very_weak",
            "crack_time": "instant",
            "score": 0,
            "recommendations": ["Mật khẩu không được để trống"]
        }

    # Calculate entropy
    length = len(password)
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in password)

    # Determine character set size
    charset_size = (
        (26 if has_lower else 0)
        + (26 if has_upper else 0)
        + (10 if has_digit else 0)
        + (32 if has_special else 0)
    )

    # Calculate entropy (charset_size ^ length)
    entropy = length * math.log2(charset_size) if charset_size else 0
    crack_time, strength, score = _get_entropy_assessment(entropy)

    # Generate recommendations
    recommendations = []
    if length < 12:
        recommendations.append("Sử dụng ít nhất 12 ký tự")
    if not (has_upper and has_lower):
        recommendations.append("Kết hợp chữ hoa và chữ thường")
    if not has_digit:
        recommendations.append("Bao gồm chữ số")
    if not has_special:
        recommendations.append("Bao gồm ký tự đặc biệt")
    if length < 16 or not (has_upper and has_lower and has_digit and has_special):
        recommendations.append("Cân nhắc sử dụng cụm mật khẩu (passphrase)")
    if entropy < 50:
        recommendations.append("Sử dụng trình quản lý mật khẩu")

    return {
        "entropy": round(entropy, 2),
        "length": length,
        "charset_size": charset_size,
        "strength": strength,
        "crack_time": crack_time,
        "score": score,
        "has_upper": has_upper,
        "has_lower": has_lower,
        "has_digit": has_digit,
        "has_special": has_special,
        "recommendations": recommendations if recommendations else ["Mật khẩu mạnh"]
    }


async def check_haveibeenpwned(password: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Check if password has been breached using HaveIBeenPwned API (async version)

    Protected by circuit breaker to prevent cascading failures.

    Args:
        password: Password to check
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Dict with breach information
    """
    async def fetch_pwned_data():
        """Internal function to fetch data from HaveIBeenPwned API"""
        # HaveIBeenPwned k-Anonymity check
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}"
            )

        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"API returned status code {response.status_code}",
                request=response.request,
                response=response
            )

        hashes = response.text.split('\n')
        for hash_suffix in hashes:
            if hash_suffix.split(':')[0] == suffix:
                breached_count = int(hash_suffix.split(':')[1])
                return {
                    "breached": True,
                    "count": breached_count,
                    "message": f"Password này đã bị lộ trong {breached_count} vụ dữ liệu bị hack!"
                }
        return {
            "breached": False,
            "count": 0,
            "message": "Không tìm thấy mật khẩu trong các vụ rò rỉ đã biết"
        }

    try:
        # Use circuit breaker to protect against cascading failures
        return await hibp_circuit_breaker.call(fetch_pwned_data)

    except CircuitBreakerOpenError as e:
        logger.warning(f"HaveIBeenPwned circuit breaker is open: {e}")
        return {
            "breached": None,
            "count": 0,
            "message": "Dịch vụ kiểm tra mật khẩu bị tạm thời ngừng do lỗi hệ thống. Vui lòng thử lại sau vài phút.",
            "service_unavailable": True,
            "circuit_breaker_active": True
        }

    except httpx.TimeoutException:
        logger.debug("HaveIBeenPwned check timed out")
        return {
            "breached": None,
            "count": 0,
            "message": "Không thể kiểm tra rò rỉ mật khẩu do dịch vụ bên thứ ba gián đoạn. Tuy nhiên, mật khẩu của bạn vẫn được đánh giá dựa trên độ phức tạp entropy.",
            "service_unavailable": True
        }
    except Exception as e:
        logger.debug(f"HaveIBeenPwned check failed: {e}")
        return {
            "breached": None,
            "count": 0,
            "message": "Không thể kiểm tra rò rỉ mật khẩu do dịch vụ bên thứ ba gián đoạn. Tuy nhiên, mật khẩu của bạn vẫn được đánh giá dựa trên độ phức tạp entropy.",
            "service_unavailable": True
        }


# Synchronous wrapper for backward compatibility
def check_haveibeenpwned_sync(password: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Synchronous wrapper for HaveIBeenPwned check (uses requests for backward compatibility)

    NOTE: This version doesn't use circuit breaker protection due to synchronous limitations.
    For production use, prefer the async version: check_haveibeenpwned()

    Args:
        password: Password to check
        timeout: Request timeout in seconds (default: 5)

    Returns:
        Dict with breach information
    """
    try:
        import requests
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]

        response = requests.get(
            f"https://api.pwnedpasswords.com/range/{prefix}",
            timeout=timeout
        )

        if response.status_code != 200:
            return {
                "breached": None,
                "count": 0,
                "message": "Dịch vụ HaveIBeenPwned không khả dụng"
            }

        hashes = response.text.split('\n')
        for hash_suffix in hashes:
            if hash_suffix.split(':')[0] == suffix:
                breached_count = int(hash_suffix.split(':')[1])
                return {
                    "breached": True,
                    "count": breached_count,
                    "message": f"Password này đã bị lộ trong {breached_count} vụ dữ liệu bị hack!"
                }
        return {
            "breached": False,
            "count": 0,
            "message": "Không tìm thấy mật khẩu trong các vụ rò rỉ đã biết"
        }

    except Exception as e:
        logger.debug(f"HaveIBeenPwned check failed: {e}")
        return {
            "breached": None,
            "count": 0,
            "message": "Không thể kiểm tra rò rỉ mật khẩu do dịch vụ bên thứ ba gián đoạn. Tuy nhiên, mật khẩu của bạn vẫn được đánh giá dựa trên độ phức tạp entropy.",
            "service_unavailable": True
        }


async def check_password_strength_async(password: str) -> Dict[str, Any]:
    """
    Main entry point for password strength checking (async version)

    Combines entropy calculation with breach checking

    Args:
        password: Password to check

    Returns:
        Dict with comprehensive password analysis
    """
    # Calculate entropy-based strength
    entropy_result = calculate_password_entropy(password)

    # Check breached password (async)
    breached_result = await check_haveibeenpwned(password)
    return _build_password_strength_result(entropy_result, breached_result)


def check_password_strength(password: str) -> Dict[str, Any]:
    """
    Main entry point for password strength checking (sync version for backward compatibility)

    Combines entropy calculation with breach checking

    Args:
        password: Password to check

    Returns:
        Dict with comprehensive password analysis
    """
    # Calculate entropy-based strength
    entropy_result = calculate_password_entropy(password)

    # Check breached password using sync wrapper (for backward compatibility)
    breached_result = check_haveibeenpwned_sync(password)
    return _build_password_strength_result(entropy_result, breached_result)


def format_password_response(result: Dict[str, Any], for_chat: bool = False) -> str:
    """
    Format password check results for display

    Args:
        result: Password check result from check_password_strength
        for_chat: If True, format for chat response with emojis

    Returns:
        Formatted string representation
    """
    if for_chat:
        strength_emoji = {
            "RẤT MẠNH": "🟢",
            "MẠNH": "🔵",
            "TRUNG BÌNH": "🟡",
            "YẾU": "🔴"
        }.get(result.get('strength', ''), '⚪')

        response = f"🔐 **KẾT QUẢ ĐÁNH GIÁ MẬT KHẨU:**\n\n"
        response += f"📏 **Độ dài:** {result.get('password_length', 0)} ký tự\n"
        response += f"💪 **Độ mạnh:** {strength_emoji} {result.get('strength', 'Unknown')}\n"
        response += f"📊 **Điểm số:** {result.get('strength_score', 0)}/100\n"
        response += f"⏱️ **Thời gian phá:** {result.get('crack_time', 'Unknown')}\n\n"

        # Add character breakdown
        response += f"**Phân tích:**\n"
        response += f"• {'✅' if result.get('has_upper') else '❌'} Chữ hoa\n"
        response += f"• {'✅' if result.get('has_lower') else '❌'} Chữ thường\n"
        response += f"• {'✅' if result.get('has_digit') else '❌'} Số\n"
        response += f"• {'✅' if result.get('has_special') else '❌'} Ký tự đặc biệt\n\n"

        # Add breach warning
        if result.get('breached_count'):
            response += f"🚨 **CẢNH BÁO:** Mật khẩu này đã bị lộ trong {result.get('breached_count')} vụ dữ liệu bị hack!\n\n"

        # Add feedback
        if result.get('feedback'):
            response += f"**Khuyến nghị:**\n"
            for suggestion in result.get('feedback', []):
                response += f"• {suggestion}\n"

        return response
    else:
        # JSON format for API
        return str(result)
