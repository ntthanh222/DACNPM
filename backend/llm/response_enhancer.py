"""
Response Enhancer Service (Phase 2.1: LLM-in-the-loop)

Converts technical security results into user-friendly, natural language responses
using LLM while maintaining security expertise.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ResponseEnhancer:
    """
    Enhances technical security responses with LLM for better user experience.

    Instead of returning raw markdown with technical details, this service
    uses Gemini LLM to convert results into friendly, actionable advice
    tailored for Vietnamese users.
    """

    def __init__(self, llm_service):
        """
        Initialize the response enhancer with an LLM service.

        Args:
            llm_service: An instance of GeminiService or similar LLM service
        """
        self.llm = llm_service
        logger.info("✅ Response Enhancer initialized")

    def enhance_phishing_response(
        self,
        raw_result: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Convert VirusTotal raw data into friendly phishing advice.

        Args:
            raw_result: Raw scan result from VirusTotal or scanner
            user_context: Optional user security context for personalization

        Returns:
            Enhanced, user-friendly response text
        """
        system_prompt = """Bạn là chuyên gia bảo mật mạng đang tư vấn cho người dùng Việt Nam.

**Nhiệm vụ:** Chuyển đổi kết quả quét kỹ thuật thành lời khuyên thân thiện, dễ hiểu.

**Quy tắc:**
- Dùng emoji phù hợp để làm cho thông tin dễ đọc
- Giọng văn: hữu cơ, như đang nói chuyện với bạn bè
- Nếu nguy hiểm: cảnh báo rõ ràng, khuyến nghị hành động cụ thể
- Nếu an toàn: vẫn nhắc nhở cảnh giác
- Tối đa 200 chữ
- Dùng ngôn ngữ Việt Nam tự nhiên

**Cấu trúc phản hồi:**
1. Kết quả ngắn gọn (an toàn/nguy hiểm)
2. Lời khuyên cụ thể cho người dùng
3. Hành động cần thực hiện (nếu có)"""

        # Extract key information
        url = raw_result.get('url', 'Unknown')
        malicious = raw_result.get('malicious', 0)
        suspicious = raw_result.get('suspicious', 0)
        total = raw_result.get('total', 0)
        risk_level = raw_result.get('risk_level', 'UNKNOWN')

        # Build prompt for LLM
        prompt = f"""Kết quả quét URL cần phân tích:

**URL:** {url}
**Độc hại:** {malicious}/{total} engine phát hiện
**Đáng ngờ:** {suspicious}/{total} engine đánh dấu
**Mức rủi ro:** {risk_level}

Hãy phân tích và đưa ra lời khuyên cụ thể cho người dùng Việt Nam."""

        # Add user context if available
        if user_context:
            role = user_context.get('role_level', 'beginner')
            prompt += f"\n\nNgười dùng là: {role}"

        try:
            response = self.llm.generate_response(
                message=prompt,
                system_prompt=system_prompt
            )
            return response
        except Exception as e:
            logger.error(f"Failed to enhance phishing response: {e}")
            # Fallback to standard response
            return self._fallback_phishing_response(raw_result)

    def enhance_cve_response(
        self,
        cve_data: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Convert CVE technical data into actionable advice.

        Args:
            cve_data: CVE information from NIST NVD or cache
            user_context: Optional user security context for personalization

        Returns:
            Enhanced, user-friendly response text
        """
        system_prompt = """Bạn là chuyên gia CVE đang tư vấn cho người dùng Việt Nam.

**Nhiệm vụ:** Giải thích lỗ hổng bảo mật một cách dễ hiểu và đưa ra khuyến nghị cụ thể.

**Quy tắc:**
- Giải thích kỹ thuật thành ngôn ngữ thường hiểu
- Nhấn mạnh rủi ro và hành động cần thực hiện
- Tối đa 250 chữ
- Dùng emoji để highlight thông tin quan trọng

**Cấu trúc phản hồi:**
1. CVE là gì (dễ hiểu)
2. Tác động/Nguy hiểm như thế nào
3. Cần làm gì (khuyến nghị cụ thể)"""

        # Extract key CVE information
        cve_id = cve_data.get('cve_id', 'Unknown')
        cvss_score = cve_data.get('cvss_score', 'N/A')
        severity = cve_data.get('severity', 'Unknown')
        description = cve_data.get('description', 'Không có mô tả')

        # Build prompt
        prompt = f"""CVE cần phân tích:

**CVE ID:** {cve_id}
**Độ nghiêm trọng:** {severity}
**CVSS Score:** {cvss_score}
**Mô tả:** {description}

Hãy giải thích và đưa ra khuyến nghị cho người dùng Việt Nam."""

        # Add user context for personalization
        if user_context:
            role = user_context.get('role_level', 'beginner')
            prompt += f"\n\nNgười dùng là: {role}"

        try:
            response = self.llm.generate_response(
                message=prompt,
                system_prompt=system_prompt
            )
            return response
        except Exception as e:
            logger.error(f"Failed to enhance CVE response: {e}")
            # Fallback to standard response
            return self._fallback_cve_response(cve_data)

    def enhance_password_response(
        self,
        password_result: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Convert password analysis into friendly advice.

        Args:
            password_result: Password strength analysis result
            user_context: Optional user security context

        Returns:
            Enhanced, user-friendly response text
        """
        system_prompt = """Bạn là chuyên gia bảo mật đang tư vấn về mật khẩu.

**Nhiệm vụ:** Đánh giá độ mạnh mật khẩu và đưa ra khuyến nghị cải thiện.

**Quy tắc:**
- Thẳng thắn nhưng khuyến khích
- Đưa ra gợi ý cụ thể, khả thi
- Tối đa 150 chữ"""

        strength = password_result.get('strength', 'Unknown')
        score = password_result.get('strength_score', 0)

        prompt = f"""Kết quả phân tích mật khẩu:

**Đánh giá:** {strength}
**Điểm số:** {score}/100

Hãy đưa ra lời khuyên cụ thể."""

        try:
            response = self.llm.generate_response(
                message=prompt,
                system_prompt=system_prompt
            )
            return response
        except Exception as e:
            logger.error(f"Failed to enhance password response: {e}")
            return self._fallback_password_response(password_result)

    def _fallback_phishing_response(self, raw_result: Dict) -> str:
        """Fallback response when LLM fails"""
        malicious = raw_result.get('malicious', 0)
        suspicious = raw_result.get('suspicious', 0)
        total = raw_result.get('total', 0)

        if malicious > 0:
            return f"""⚠️ **CẢNH BÁO! URL này có ĐỘC HẠI!**

🚫 {malicious}/{total} engine chống virus đã phát hiện mã độc.

**Đừng click!** URL này có thể chứa:
- Virus hoặc malware
- Trang lừa đảo (phishing)
- Code độc hại

**Nếu đã click:**
1. Ngắt kết nối mạng ngay
2. Quét toàn bộ máy tính bằng antivirus
3. Đổi mật khẩu tất cả tài khoản quan trọng"""
        elif suspicious > 0:
            return f"""⚠️ **Cảnh báo! URL này ĐÁNG NGỜ.**

🔍 {suspicious}/{total} engine đánh dấu là đáng ngờ.

**Hãy thận trọng:**
- Kiểm tra kỹ URL trước khi truy cập
- Không nhập thông tin nhạy cảm
- Tìm hiểu thêm về trang web này"""
        else:
            return f"""✅ **URL này an toàn**

🔍 {total}/{total} engine xác nhận URL này an toàn.

**Tuy nhiên:**
- Luôn cảnh giác với các trang web mới
- Kiểm tra kỹ URL và HTTPS certificate
- Không nhập thông tin nhạy cảm nếu không cần thiết"""

    def _fallback_cve_response(self, cve_data: Dict) -> str:
        """Fallback response when LLM fails"""
        cve_id = cve_data.get('cve_id', 'Unknown')
        severity = cve_data.get('severity', 'Unknown')
        cvss = cve_data.get('cvss_score', 'N/A')

        return f"""📋 **CVE: {cve_id}**

**Độ nghiêm trọng:** {severity.upper() if severity else 'Unknown'}
**CVSS Score:** {cvss}

**Khuyến nghị:**
{'⚠️ KHẮC PHỤC NGAY - Rủi ro cao' if severity in ['critical', 'high'] else '✅ Có thể lên lịch bảo trì' if severity == 'low' else '📅 KHẮC PHỤC SỚM'}"""

    def _fallback_password_response(self, password_result: Dict) -> str:
        """Fallback response when LLM fails"""
        strength = password_result.get('strength', 'Unknown')
        score = password_result.get('strength_score', 0)

        if score < 50:
            return f"""🔴 **Mật khẩu YẾU!**

Điểm: {score}/100

**Nên cải thiện:**
- Tăng độ dài lên ít nhất 12 ký tự
- Thêm chữ hoa, số, ký tự đặc biệt
- Sử dụng password manager để tạo mật khẩu ngẫu nhiên"""
        elif score < 80:
            return f"""🟡 **Mật khẩu ỔN**

Điểm: {score}/100

**Có thể cải thiện:**
- Thêm độ dài hoặc độ phức tạp
- Sử dụng mật khẩu khác cho mỗi tài khoản"""
        else:
            return f"""✅ **Mật khẩu MẠNH!**

Điểm: {score}/100

Mật khẩu của bạn đáp ứng các tiêu chuẩn bảo mật tốt!"""


def get_response_enhancer_singleton():
    """
    Get or create the singleton ResponseEnhancer instance.

    Returns:
        ResponseEnhancer instance
    """
    global _response_enhancer_instance

    if _response_enhancer_instance is None:
        try:
            from backend.llm.gemini_service import get_gemini_service_singleton
            llm = get_gemini_service_singleton()
            _response_enhancer_instance = ResponseEnhancer(llm)
        except Exception as e:
            logger.error(f"Failed to initialize Response Enhancer: {e}")
            _response_enhancer_instance = None

    return _response_enhancer_instance


# Global singleton instance
_response_enhancer_instance = None
