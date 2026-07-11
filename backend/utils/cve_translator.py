"""
CVE Description Translator using Gemini

Dịch và tóm tắt CVE description sang tiếng Việt dễ hiểu cho người dùng phổ thông.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global translator cache to avoid re-translating same CVEs
_translation_cache = {}


def translate_cve_description(
    english_description: str,
    cve_id: str,
    cvss_score: Optional[str] = None,
    severity: Optional[str] = None
) -> str:
    """
    Dịch CVE description sang tiếng Việt dễ hiểu.

    Args:
        english_description: Mô tả tiếng Anh từ NIST NVD
        cve_id: ID CVE (ví dụ: CVE-2024-1234)
        cvss_score: Điểm CVSS (optional)
        severity: Mức độ nghiêm trọng (optional)

    Returns:
        str: Mô tả đã dịch sang tiếng Việt, hoặc original nếu fail
    """
    if not english_description or english_description == "No description available":
        return "Không có mô tả"

    # Check cache first
    cache_key = f"{cve_id}:{english_description[:50]}"
    if cache_key in _translation_cache:
        logger.debug(f"Using cached translation for {cve_id}")
        return _translation_cache[cache_key]

    try:
        from llm.gemini_service import get_gemini_service_singleton

        gemini_service = get_gemini_service_singleton()

        # Build translation prompt
        severity_info = ""
        if severity and cvss_score:
            severity_vn = {
                'critical': 'Khẩn cấp',
                'high': 'Cao',
                'medium': 'Trung bình',
                'low': 'Thấp',
                'none': 'Không'
            }.get(severity.lower(), severity)

            severity_info = f"\n- Điểm CVSS: {cvss_score}\n- Mức độ: {severity_vn}"

        system_prompt = """Bạn là chuyên gia bảo mật cyberspace. Nhiệm vụ của bạn là dịch và tóm tắt thông tin lỗ hổng bảo mật sang tiếng Việt một cách dễ hiểu cho người dùng phổ thông.

Yêu cầu:
- Dịch sang tiếng Việt tự nhiên, chuyên nghiệp nhưng dễ hiểu
- Giải thích các thuật ngữ kỹ thuật quan trọng trong ngoặc đơn
- Tóm tắt trong 2-3 câu ngắn gọn
- Giữ nguyên các tên CVE, tên sản phẩm, phiên bản
- Nếu có severity/CVSS, giải thích ý nghĩa thực tế cho người dùng

Trả về chỉ đoạn dịch tiếng Việt, không có lời mở đầu hay kết thúc."""

        user_message = f"""CVE ID: {cve_id}{severity_info}

Mô tả tiếng Anh:
{english_description}

Hãy dịch và giải thích bằng tiếng Việt:"""

        # Call Gemini
        translated = gemini_service.generate_response(
            message=user_message,
            system_prompt=system_prompt
        )

        if translated:
            # Cache the result
            _translation_cache[cache_key] = translated
            logger.info(f"✅ Translated CVE {cve_id} description")
            return translated
        else:
            return english_description

    except Exception as e:
        logger.warning(f"Failed to translate CVE {cve_id}: {e}")
        # Return original description if translation fails
        return english_description


def translate_cve_response(response_data: dict, cve_id: str) -> dict:
    """
    Dịch toàn bộ response CVE sang tiếng Việt.

    Args:
        response_data: Dict chứa CVE data từ cve_lookup.py
        cve_id: ID CVE

    Returns:
        dict: Response data với description đã dịch
    """
    if not response_data or 'response_data' not in response_data:
        return response_data

    # Extract data
    data = response_data['response_data']
    original_description = data.get('description', '')
    cvss_score = response_data.get('cvss_score')
    severity = response_data.get('severity')

    # Translate description
    if original_description and original_description != "No description available":
        translated_description = translate_cve_description(
            original_description,
            cve_id,
            cvss_score,
            severity
        )

        # Update response data
        response_data['response_data']['description'] = translated_description
        response_data['response_data']['description_original'] = original_description
        response_data['translated'] = True

    return response_data


def clear_translation_cache():
    """Xóa cache translation (để test hoặc reset)"""
    global _translation_cache
    _translation_cache = {}
    logger.info("Translation cache cleared")
