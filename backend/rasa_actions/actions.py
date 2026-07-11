"""
Enhanced Custom Actions for CyberSec Assistant
Integrates Phase 1 database foundation with comprehensive security capabilities
"""
import asyncio
import logging
from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from uuid import UUID, uuid4
from datetime import datetime
from backend.database.connection import supabase_admin

logger = logging.getLogger(__name__)


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
from backend.rasa_actions.utils import (
    scan_url_virustotal,
    lookup_cve,
    calculate_password_entropy,
    get_security_news,
    create_security_scan_record,
    cache_cve_lookup,
    get_cached_cve
)

class ActionSetUserId(Action):
    """Action to set user_id slot from sender_id"""

    def name(self) -> Text:
        return "action_set_user_id"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get user_id from sender_id (set by Rasa from REST API 'sender' field)
        user_id = tracker.sender_id

        if user_id:
            return [{"slot": "user_id", "value": user_id}]

        return []

class ActionGetChatHistory(Action):
    """Enhanced action to retrieve user's chat history with Phase 1 integration"""

    def name(self) -> Text:
        return "action_get_chat_history"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get or set user_id slot from sender_id
        user_id = tracker.get_slot("user_id")
        if not user_id and tracker.sender_id:
            user_id = tracker.sender_id

        if not user_id:
            dispatcher.utter_message(text="Vui lòng đăng nhập để xem lịch sử trò chuyện.")
            return []

        # Validate UUID before database query to prevent crashes
        if not _validate_uuid(user_id):
            logger.warning(f"Invalid user_id format (not UUID): {user_id}")
            dispatcher.utter_message(text="Vui lòng đăng nhập để xem lịch sử trò chuyện.")
            return []

        try:
            # Get chat history from Supabase with enhanced filtering
            response = supabase_admin.table('chat_history').select('*')\
                .eq('user_id', str(user_id))\
                .order('created_at', desc=True)\
                .limit(20)\
                .execute()

            chat_history = response.data

            if not chat_history:
                dispatcher.utter_message(text="Không tìm thấy lịch sử trò chuyện nào.")
                return []

            # Group by conversation session for better organization
            message = "📋 **Lịch sử trò chuyện gần đây:**\n\n"

            # Show recent conversations with context
            for i, chat in enumerate(chat_history[:10], 1):
                timestamp = datetime.fromisoformat(chat['created_at'].replace('Z', '+00:00')).strftime('%d/%m %H:%M')
                intent_display = chat.get('intent', 'general')

                intent_emoji = {
                    'check_phishing': '🔍',
                    'check_password': '🔐',
                    'lookup_cve': '📋',
                    'ask_security_tips': '🛡️',
                    'get_security_news': '📰',
                    'assess_vulnerability': '🔬',
                    'incident_response': '🚨',
                    'auth_help': '🔑'
                }.get(intent_display, '💬')

                message += f"{intent_emoji} **{timestamp}** - {intent_display}\n"
                message += f"   Bạn: {chat['user_message'][:60]}...\n"
                message += f"   Bot: {chat['bot_response'][:60]}...\n\n"

            dispatcher.utter_message(text=message)

        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            dispatcher.utter_message(
                text="Hiện tại tôi không thể truy xuất lịch sử trò chuyện. "
                     "Vui lòng thử lại sau hoặc bắt đầu cuộc trò chuyện mới."
            )

        return []

class ActionCheckPhishing(Action):
    """Enhanced action to check URL for phishing with Phase 2 LLM-in-the-loop integration"""

    def name(self) -> Text:
        return "action_check_phishing"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get or set user_id slot from sender_id
        user_id = tracker.get_slot("user_id")
        if not user_id and tracker.sender_id:
            user_id = tracker.sender_id

        # Extract URL from entity or slot
        latest_message = tracker.latest_message
        entities = {}
        if latest_message and latest_message.get('entities'):
            entities = {e['entity']: e['value'] for e in latest_message['entities']}

        url = entities.get('url') or tracker.get_slot("url")

        if not url:
            dispatcher.utter_message(text="Vui lòng cung cấp URL cần kiểm tra.")
            return []

        dispatcher.utter_message(text="🔍 **Đang phân tích URL...**\n\nĐang quét trên nhiều engine bảo mật. Vui lòng đợi khoảng 30 giây...")

        # Call shared URL scanning utility
        from backend.utils.url_scanner import check_phishing_url as scan_url
        result = scan_url(url)

        # Check for API errors
        if 'error' in result:
            error_msg = f"❌ **Lỗi khi quét URL:** {result.get('error', 'Unknown error')}"
            dispatcher.utter_message(text=error_msg)
            return []

        try:
            # Get user security context for personalization
            user_context = self._get_user_security_context(user_id)

            # Phase 2.1: Use ResponseEnhancer for LLM-in-the-loop
            try:
                from backend.llm.response_enhancer import get_response_enhancer_singleton
                enhancer = get_response_enhancer_singleton()

                if enhancer:
                    # Prepare data for enhancer
                    stats = result.get('stats', {})
                    detected_total = stats.get('malicious', 0) + stats.get('suspicious', 0) + stats.get('harmless', 0)
                    enhanced_data = {
                        'url': url,
                        'malicious': stats.get('malicious', 0),
                        'suspicious': stats.get('suspicious', 0),
                        'total': detected_total,
                        'risk_level': result.get('risk_level', 'UNKNOWN'),
                        'risk_score': result.get('risk_score', 0),  # Use correct value from scanner
                        'recommendation': result.get('recommendation', '')
                    }

                    # Get enhanced response
                    bot_response = enhancer.enhance_phishing_response(
                        raw_result=enhanced_data,
                        user_context=user_context
                    )
                else:
                    # Fallback to standard response
                    bot_response = self._format_standard_phishing_response(url, result)

            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"LLM enhancement failed, using fallback: {e}")
                bot_response = self._format_standard_phishing_response(url, result)

            dispatcher.utter_message(text=bot_response)

            # Store scan result in database if user is authenticated
            stats = result.get('stats', {})
            if user_id:
                scan_record = {
                    "stats": stats,
                    "status": result.get('risk_level', 'UNKNOWN'),
                    "risk_score": result.get('risk_score', 0),
                    "scan_timestamp": datetime.now().isoformat()
                }
                create_security_scan_record(str(user_id), "url_scan", url, scan_record)

        except Exception as e:
            bot_response = f"❌ **Lỗi khi xử lý kết quả quét:** {str(e)}"
            dispatcher.utter_message(text=bot_response)

        return []

    def _get_user_security_context(self, user_id: Any) -> Dict[str, Any]:
        """Get user security context from database for personalization"""
        try:
            if not user_id:
                return {}

            from backend.database.crud.users import get_user
            user = get_user(user_id)

            if user and user.security_context:
                return user.security_context

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get user context: {e}")

        return {}

    def _format_standard_phishing_response(self, url: str, result: Dict) -> str:
        """Fallback standard response when LLM is unavailable"""
        stats = result.get('stats', {})
        malicious = stats.get('malicious', 0)
        suspicious = stats.get('suspicious', 0)
        harmless = stats.get('harmless', 0)
        detected_total = malicious + suspicious + harmless
        risk_level = result.get('risk_level', 'UNKNOWN')
        scan_source = result.get('scan_source', 'unknown')

        if malicious > 0 or suspicious > 0:
            risk_emoji = "🔴 RẤT CAO" if malicious > 0 else "🟡 TRUNG BÌNH"
            risk_percentage = ((malicious + suspicious) / detected_total * 100) if detected_total > 0 else 0

            bot_response = f"⚠️ **KẾT QUẢ QUÉT URL:** {url}\n\n"
            bot_response += f"📊 **Thống kê quét:**\n"
            bot_response += f"• 🚫 Độc hại: {malicious}/{detected_total} engines\n"
            bot_response += f"• ⚠️ Đáng ngờ: {suspicious}/{detected_total} engines\n"
            bot_response += f"• ✅ An toàn: {harmless}/{detected_total} engines\n"
            bot_response += f"• 📈 Tỷ lệ rủi ro: {risk_percentage:.1f}%\n"
            bot_response += f"• 🎯 Mức độ rủi ro: {risk_emoji}\n"
            bot_response += f"• 📈 Nguồn: {scan_source}\n\n"
            bot_response += f"🚨 **CẢNH BÁO:** URL này có thể nguy hiểm! Không nên truy cập.\n\n"

            if result.get('recommendation'):
                bot_response += f"**Khuyến nghị:** {result['recommendation']}\n\n"

            if malicious > 0:
                bot_response += f"**Đã phát hiện:**\n"
                bot_response += f"• Phát hiện bởi {malicious} engine chống virus\n"
                if suspicious > 0:
                    bot_response += f"• Đánh dấu đáng ngờ bởi {suspicious} engine\n"

            bot_response += f"\n**Khuyến nghị bảo mật:**\n"
            bot_response += f"• KHÔNG truy cập URL này\n"
            bot_response += f"• Báo cáo URL cho cơ quan chức năng\n"
            bot_response += f"• Kiểm tra thiết bị nếu đã truy cập\n"
            bot_response += f"• Quét malware toàn bộ hệ thống"

        else:
            bot_response = f"✅ **KẾT QUẢ QUÉT URL:** {url}\n\n"
            bot_response += f"📊 **Thống kê quét:**\n"
            bot_response += f"• 🚫 Độc hại: 0/{detected_total} engines\n"
            bot_response += f"• ⚠️ Đáng ngờ: 0/{detected_total} engines\n"
            bot_response += f"• ✅ An toàn: {harmless}/{detected_total} engines\n"
            bot_response += f"• 📈 Tỷ lệ rủi ro: 0.0%\n"
            bot_response += f"• 🎯 Mức độ rủi ro: 🟢 THẤP\n"
            bot_response += f"• 📈 Nguồn: {scan_source}\n\n"
            bot_response += f"✓ **URL này an toàn** theo kết quả quét hiện tại.\n\n"

            if result.get('recommendation'):
                bot_response += f"**Khuyến nghị:** {result['recommendation']}\n\n"

            bot_response += f"**Lưu ý:** Kết quả quét có thể thay đổi theo thời gian. Luôn cảnh giác khi truy cập các trang web mới."

        return bot_response


class ActionLookupCVE(Action):
    """Enhanced action to lookup CVE details with Phase 2 personalization"""

    def name(self) -> Text:
        return "action_lookup_cve"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get or set user_id slot from sender_id
        user_id = tracker.get_slot("user_id")
        if not user_id and tracker.sender_id:
            user_id = tracker.sender_id

        # Extract CVE ID from entity or slot
        latest_message = tracker.latest_message
        entities = {}
        if latest_message and latest_message.get('entities'):
            entities = {e['entity']: e['value'] for e in latest_message['entities']}

        cve_id = entities.get('cve_id') or tracker.get_slot("cve_id")

        if not cve_id:
            dispatcher.utter_message(text="Vui lòng cung cấp ID CVE cần tra cứu (ví dụ: CVE-2024-1234).")
            return []

        # Ensure CVE ID is in correct format
        if not cve_id.upper().startswith('CVE-'):
            cve_id = f"CVE-{cve_id}"
        else:
            cve_id = cve_id.upper()

        dispatcher.utter_message(text="🔍 **Đang tra cứu CVE...**\n\nĐang tìm kiếm thông tin chi tiết về lỗ hổng...")

        # Check cache first
        cached_result = get_cached_cve(cve_id)
        result = None
        if cached_result:
            response_data = cached_result["response_data"]
            cvss_score = cached_result.get("cvss_score")
            severity = cached_result.get("severity")
            dispatcher.utter_message(text="✅ **Đã tìm thấy trong cache** - Sử dụng dữ liệu đã lưu.")
        else:
            # Use shared CVE lookup utility
            from backend.utils.cve_lookup import check_cve
            result = check_cve(cve_id)
            if 'error' in result:
                error_msg = f"❌ **Lỗi khi tra cứu CVE:** {result.get('error', 'Unknown error')}"
                dispatcher.utter_message(text=error_msg)
                return []
            response_data = result.get('response_data', {})
            cvss_score = result.get('cvss_score')
            severity = result.get('severity')

        try:
            if not response_data:
                dispatcher.utter_message(text=f"❌ **Không tìm thấy thông tin** cho CVE: {cve_id}")
                return []

            # Get user security context for personalization (Phase 2.2)
            user_context = self._get_user_security_context(user_id)
            user_role = user_context.get('role_level', 'beginner') if user_context else 'beginner'

            # Phase 2.1 & 2.2: Use ResponseEnhancer with personalization
            try:
                from backend.llm.response_enhancer import get_response_enhancer_singleton
                enhancer = get_response_enhancer_singleton()

                if enhancer:
                    # Prepare CVE data for enhancer
                    cve_enhanced_data = {
                        'cve_id': cve_id,
                        'cvss_score': cvss_score,
                        'severity': severity,
                        'description': response_data.get('description', 'Không có mô tả'),
                        'affected_products': response_data.get('affected_products', []),
                        'references': response_data.get('references', [])
                    }

                    # Get enhanced response
                    bot_response = enhancer.enhance_cve_response(
                        cve_data=cve_enhanced_data,
                        user_context=user_context
                    )

                    # Phase 2.2: Add role-specific details
                    if user_role == 'security_analyst':
                        bot_response += self._get_technical_details(response_data)
                    elif user_role == 'sysadmin':
                        bot_response += self._get_sysadmin_guidance(cve_id, response_data)
                    elif user_role == 'developer':
                        bot_response += self._get_developer_guidance(response_data)

                else:
                    # Fallback to standard response
                    bot_response = self._format_standard_cve_response(
                        cve_id, cvss_score, severity, response_data
                    )

            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"LLM enhancement failed: {e}")
                bot_response = self._format_standard_cve_response(
                    cve_id, cvss_score, severity, response_data
                )

            dispatcher.utter_message(text=bot_response)

            # Cache the result
            if not cached_result:
                cache_cve_lookup(cve_id, response_data)

        except Exception as e:
            dispatcher.utter_message(text=f"❌ **Lỗi khi xử lý CVE:** {str(e)}")

        return []

    def _get_user_security_context(self, user_id: Any) -> Dict[str, Any]:
        """Get user security context for personalization"""
        try:
            if not user_id:
                return {}

            from backend.database.crud.users import get_user
            user = get_user(user_id)

            if user and user.security_context:
                return user.security_context

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get user context: {e}")

        return {}

    def _get_technical_details(self, response_data: Dict) -> str:
        """Add technical details for security analysts"""
        details = "\n\n🔬 **Technical Details:**\n\n"

        if response_data.get('cvss_vector'):
            details += f"**CVSS Vector:** {response_data['cvss_vector']}\n"

        if response_data.get('cwe'):
            details += f"**CWE:** {response_data['cwe']}\n"

        if response_data.get('exploitability'):
            details += f"**Exploitability:** {response_data['exploitability']}\n"

        return details

    def _get_sysadmin_guidance(self, cve_id: str, response_data: Dict) -> str:
        """Add system administration guidance"""
        guidance = "\n\n🖥️ **SysAdmin Guidance:**\n\n"

        if response_data.get('affected_systems'):
            guidance += "**Affected Systems:**\n"
            for system in response_data['affected_systems'][:3]:
                guidance += f"• {system}\n"

        guidance += "\n**Patch Commands:**\n"
        guidance += "```bash\n# Check package version\n"
        guidance += "# Apply update when available\n```\n"

        return guidance

    def _get_developer_guidance(self, response_data: Dict) -> str:
        """Add developer-specific guidance"""
        guidance = "\n\n💻 **Developer Guidance:**\n\n"

        if response_data.get('vulnerable_libraries'):
            guidance += "**Affected Libraries:**\n"
            for lib in response_data['vulnerable_libraries']:
                guidance += f"• {lib}\n"

        guidance += "\n**Fix:** Update to latest stable version.\n"

        return guidance

    def _format_standard_cve_response(self, cve_id: str, cvss_score: str,
                                       severity: str, response_data: Dict) -> str:
        """Fallback standard CVE response"""
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢',
            'none': '🔵'
        }.get(severity, '⚪')

        bot_response = f"📋 **CVE: {cve_id}**\n\n"
        bot_response += f"{severity_emoji} **Severity:** {severity.upper() if severity else 'Unknown'}\n"
        bot_response += f"📈 **CVSS:** {cvss_score if cvss_score != 'N/A' else 'N/A'}\n\n"

        if response_data.get('description'):
            bot_response += f"📝 {response_data['description']}\n\n"

        # Severity-based recommendations
        if cvss_score and cvss_score != 'N/A':
            try:
                score = float(cvss_score)
                if score >= 9.0:
                    bot_response += "⚠️ **KHẮC PHỤC NGAY** - Rủi ro cực kỳ cao\n"
                elif score >= 7.0:
                    bot_response += "📅 **KHẮC PHỤC SỚM** - Rủi ro cao\n"
                elif score >= 4.0:
                    bot_response += "✅ **Lên lịch khắc phục** - Rủi ro trung bình\n"
                else:
                    bot_response += "ℹ️ **Theo dõi** - Rủi ro thấp\n"
            except ValueError:
                pass

        return bot_response

class ActionCheckPasswordStrength(Action):
    """New action to check password strength with comprehensive analysis"""

    def name(self) -> Text:
        return "action_check_password_strength"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get or set user_id slot from sender_id
        user_id = tracker.get_slot("user_id")
        if not user_id and tracker.sender_id:
            user_id = tracker.sender_id

        # Extract password from entity or slot
        latest_message = tracker.latest_message
        entities = {}
        if latest_message and latest_message.get('entities'):
            entities = {e['entity']: e['value'] for e in latest_message['entities']}

        password = entities.get('password') or tracker.get_slot("password")

        if not password:
            dispatcher.utter_message(text="Vui lòng cung cấp mật khẩu cần kiểm tra.")
            return []

        # Use shared password checking utility
        from backend.utils.password_checker import check_password_strength as check_pwd
        result = check_pwd(password)

        if 'error' in result:
            dispatcher.utter_message(text=f"❌ **Lỗi:** {result.get('error', 'Unknown error')}")
            return []

        # NEW: Enhance response with LLM (Phase 1.5: LLM-in-the-loop)
        try:
            from backend.llm.response_enhancer import get_response_enhancer_singleton
            from backend.database.crud.users import get_user

            enhancer = get_response_enhancer_singleton()

            # Get user context for personalization
            user_context = None
            if user_id:
                try:
                    user = get_user(UUID(user_id)) if isinstance(user_id, str) else get_user(user_id)
                    if user:
                        user_context = {
                            'role': user.role,
                            'role_level': user.security_context.get('role_level', 'beginner') if user.security_context else 'beginner',
                            'preferences': user.security_context.get('preferences', {}) if user.security_context else {}
                        }
                except Exception as user_error:
                    logger.warning(f"Failed to get user context for password check: {user_error}")

            # Enhanced response using LLM
            if enhancer:
                bot_response = enhancer.enhance_password_response(
                    password_result=result,
                    user_context=user_context
                )
            else:
                # Fallback to manual formatting if enhancer unavailable
                bot_response = self._fallback_password_format(result)

        except Exception as enhance_error:
            logger.warning(f"Failed to enhance password response: {enhance_error}, using fallback")
            bot_response = self._fallback_password_format(result)

        dispatcher.utter_message(text=bot_response)

        # Store password check result in Phase 1 database if user is authenticated
        if user_id:
            scan_record = {
                "password_analysis": {
                    "strength": result.get('strength'),
                    "score": result.get('strength_score'),
                    "entropy": result.get('entropy'),
                    "crack_time": result.get('crack_time')
                },
                "scan_timestamp": datetime.now().isoformat()
            }
            # Note: We don't store actual password for security
            create_security_scan_record(str(user_id), "password_check", "PASSWORD_REDACTED", scan_record)

        return []

    @staticmethod
    def _fallback_password_format(result: Dict[str, Any]) -> str:
        """
        Fallback password formatting when LLM enhancement fails.
        Provides clear, structured password analysis.
        """
        strength_text = result.get('strength', 'Unknown')
        strength_emoji = {
            'RẤT MẠNH': '🟢',
            'MẠNH': '🔵',
            'TRUNG BÌNH': '🟡',
            'YẾU': '🔴'
        }.get(strength_text, '⚪')

        bot_response = f"🔐 **PHÂN TÍCH ĐỘ MẠNH MẬT KHẨU**\n\n"
        bot_response += f"{strength_emoji} **Đánh giá tổng quan:** {strength_text}\n"
        bot_response += f"📊 **Điểm số:** {result.get('strength_score', 0)}/100\n"
        bot_response += f"🔢 **Entropy:** {result.get('entropy', 0)} bits\n"
        bot_response += f"⏱️ **Thời gian crack estim:** {result.get('crack_time', 'Unknown')}\n\n"

        bot_response += f"📋 **Chi tiết phân tích:**\n"
        bot_response += f"• Độ dài: {result.get('password_length', 0)} ký tự {'✅' if result.get('password_length', 0) >= 12 else '❌'}\n"
        bot_response += f"• Chữ thường: {'Có' if result.get('has_lower') else 'Không'} {'✅' if result.get('has_lower') else '❌'}\n"
        bot_response += f"• Chữ hoa: {'Có' if result.get('has_upper') else 'Không'} {'✅' if result.get('has_upper') else '❌'}\n"
        bot_response += f"• Số: {'Có' if result.get('has_digit') else 'Không'} {'✅' if result.get('has_digit') else '❌'}\n"
        bot_response += f"• Ký tự đặc biệt: {'Có' if result.get('has_special') else 'Không'} {'✅' if result.get('has_special') else '❌'}\n"
        bot_response += f"• Charset size: {result.get('charset_size', 0)} ký tự có thể\n\n"

        # Show breach warning if applicable
        if result.get('breached_count'):
            bot_response += f"🚨 **CẢNH BÁO:** Mật khẩu này đã bị lộ trong {result.get('breached_count')} vụ dữ liệu bị hack!\n\n"

        # Show recommendations
        feedback = result.get('feedback', [])
        if feedback:
            bot_response += f"💡 **Khuyến nghị cải thiện:**\n"
            for i, rec in enumerate(feedback, 1):
                bot_response += f"{i}. {rec}\n"
            bot_response += "\n"

        # Add security tips
        if result.get('strength_score', 0) < 50:
            bot_response += f"🛡️ **Mẹo bảo mật:**\n"
            bot_response += f"• Sử dụng password manager (Bitwarden, 1Password)\n"
            bot_response += f"• Tạo mật khẩu ngẫu nhiên 16+ ký tự\n"
            bot_response += f"• Không bao giờ reuse mật khẩu\n"
            bot_response += f"• Bật 2FA cho tất cả tài khoản quan trọng\n"

        return bot_response

class ActionGetSecurityNews(Action):
    """New action to fetch latest security news with Phase 1 integration"""

    def name(self) -> Text:
        return "action_get_security_news"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="📰 **Đang cập nhật tin tức bảo mật...**")

        # Fetch security news
        news_items = get_security_news(limit=5)

        if not news_items:
            dispatcher.utter_message(text="❌ Không thể tải tin tức bảo mật lúc này. Vui lòng thử lại sau.")
            return []

        bot_response = f"📰 **TIN TỨC BẢO MẬT MỚI NHẤT**\n\n"

        for i, news in enumerate(news_items, 1):
            bot_response += f"📌 **Tin {i}:** {news.get('title', 'No title')}\n"
            bot_response += f"📝 {news.get('summary', 'No summary available')}\n"
            bot_response += f"🔗 Nguồn: {news.get('source', 'Unknown')}\n"

            if news.get('url'):
                bot_response += f"🌐 Link: {news['url']}\n"

            bot_response += "\n"

        # Add security tips at the end
        bot_response += f"🛡️ **Mẹo bảo mật hàng ngày:**\n"
        bot_response += f"• Luôn cập nhật phần mềm và hệ điều hành\n"
        bot_response += f"• Sử dụng mật khẩu mạnh và duy nhất\n"
        bot_response += f"• Bật xác thực 2 yếu tố (2FA)\n"
        bot_response += f"• Cảnh giác với email và tin nhắn đáng ngờ\n"
        bot_response += f"• Backup dữ liệu quan trọng thường xuyên"

        dispatcher.utter_message(text=bot_response)
        return []

class ActionAssessVulnerability(Action):
    """New action to provide vulnerability assessment guidance"""

    def name(self) -> Text:
        return "action_assess_vulnerability"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        bot_response = f"🔬 **ĐÁNH GIÁ LỖ HỔNG BẢO MẬT**\n\n"

        bot_response += f"📋 **Các loại lỗ hổng phổ biến:**\n\n"

        bot_response += f"1. **Injection (SQLi, Command Injection)**\n"
        bot_response += f"   • Input validation không đủ\n"
        bot_response += f"   • Concatenation trực tiếp database queries\n"
        bot_response += f"   • OWASP A03:2021 - Injection\n\n"

        bot_response += f"2. **Cross-Site Scripting (XSS)**\n"
        bot_response += f"   • Output encoding thiếu\n"
        bot_response += f"   • DOM manipulation không an toàn\n"
        bot_response += f"   • OWASP A03:2021 - Injection\n\n"

        bot_response += f"3. **Authentication & Authorization**\n"
        bot_response += f"   • Weak password policies\n"
        bot_response += f"   • Session management kém\n"
        bot_response += f"   • Missing access controls\n"
        bot_response += f"   • OWASP A07:2021 - Identification and Authentication Failures\n\n"

        bot_response += f"4. **Sensitive Data Exposure**\n"
        bot_response += f"   • Lack of encryption\n"
        bot_response += f"   • Insecure data storage\n"
        bot_response += f"   • Information leakage\n"
        bot_response += f"   • OWASP A02:2021 - Cryptographic Failures\n\n"

        bot_response += f"🔍 **Phương pháp đánh giá:**\n"
        bot_response += f"• Code review static analysis\n"
        bot_response += f"• Dynamic application security testing\n"
        bot_response += f"• Penetration testing\n"
        bot_response += f"• Dependency vulnerability scanning\n\n"

        bot_response += f"🛠️ **Công cụ hỗ trợ:**\n"
        bot_response += f"• OWASP ZAP, Burp Suite (web security)\n"
        bot_response += f"• Nessus, OpenVAS (vulnerability scanning)\n"
        bot_response += f"• SonarQube, Snyk (code analysis)\n"
        bot_response += f"• NVD, CVE database (vulnerability lookup)\n\n"

        bot_response += f"💡 **Khuyến nghị:**\n"
        bot_response += f"• Thực hiện security assessment định kỳ\n"
        bot_response += f"• Sử dụng automated scanning tools\n"
        bot_response += f"• Conduct penetration testing annually\n"
        bot_response += f"• Keep dependencies updated\n"
        bot_response += f"• Implement security monitoring"

        dispatcher.utter_message(text=bot_response)
        return []

class ActionProvideIncidentResponse(Action):
    """New action to provide incident response guidance"""

    def name(self) -> Text:
        return "action_provide_incident_response"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        bot_response = f"🚨 **PHẢN ỨNG SỰ CỐ BẢO MẬT**\n\n"

        bot_response += f"⏰ **BƯỚC 1: NGAY LẬP TỨC (0-15 phút)**\n"
        bot_response += f"1️⃣ **Ngăn chặn tiếp tục**\n"
        bot_response += f"   • Ngắt kết nối mạng nếu nghi ngờ malware\n"
        bot_response += f"   • Đổi mật khẩu tất cả tài khoản quan trọng\n"
        bot_response += f"   • Bật 2FA cho tất cả tài khoản\n"
        bot_response += f"   • Liên hệ bank/credit card companies nếu liên quan tài chính\n\n"

        bot_response += f"2️⃣ **Đánh giá sơ bộ**\n"
        bot_response += f"   • Xác định phạm vi ảnh hưởng\n"
        bot_response += f"   • Kiểm tra logs và activity\n"
        bot_response += f"   • Document timeline và evidence\n\n"

        bot_response += f"🔧 **BƯỚC 2: KHÔI PHỤC (15-60 phút)**\n"
        bot_response += f"1️⃣ **Isolate systems**\n"
        bot_response += f"   • Tách các hệ thống bị ảnh hưởng\n"
        bot_response += f"   • Scan với antivirus updated\n"
        bot_response += f"   • Change all credentials\n\n"

        bot_response += f"2️⃣ **Backup & Restore**\n"
        bot_response += f"   • Restore từ backup sạch (nếu có)\n"
        bot_response += f"   • Verify backup integrity\n"
        bot_response += f"   • Test systems trước khi đưa vào production\n\n"

        bot_response += f"📋 **BƯỚC 3: PHÂN TÍCH (1-4 giờ)**\n"
        bot_response += f"1️⃣ **Investigation**\n"
        bot_response += f"   • Root cause analysis\n"
        bot_response += f"   • Impact assessment\n"
        bot_response += f"   • Data breach notification (nếu cần)\n\n"

        bot_response += f"2️⃣ **Documentation**\n"
        bot_response += f"   • Incident report\n"
        bot_response += f"   • Timeline và actions taken\n"
        bot_response += f"   • Lessons learned\n\n"

        bot_response += f"🛡️ **BƯỚC 4: PHÒNG NGỪA (Tương lai)**\n"
        bot_response += f"• Patch và harden systems\n"
        bot_response += f"• Update security policies\n"
        bot_response += f"• Conduct security awareness training\n"
        bot_response += f"• Implement monitoring and alerting\n\n"

        bot_response += f"📞 **Cần hỗ trợ ngay**:\n"
        bot_response += f"• Contact security team/IT department\n"
        bot_response += f"• Report to relevant authorities (nếu cần)\n"
        bot_response += f"• Notify affected parties (nếu data breach)"

        dispatcher.utter_message(text=bot_response)
        return []

class ActionProvideAuthHelp(Action):
    """New action to provide authentication help and guidance"""

    def name(self) -> Text:
        return "action_provide_auth_help"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        bot_response = f"🔑 **HƯỚNG DẪN XÁC THỰC VÀ BẢO MẬT TÀI KHOẢN**\n\n"

        bot_response += f"🔐 **Xác thực 2 yếu tố (2FA/MFA)**\n\n"
        bot_response += f"**Cách bật 2FA cho các dịch vụ phổ biến:**\n\n"

        bot_response += f"1️⃣ **Google Account**\n"
        bot_response += f"   • Settings > Security > 2-Step Verification\n"
        bot_response += f"   • Sử dụng Google Authenticator thay vì SMS\n\n"

        bot_response += f"2️⃣ **Facebook**\n"
        bot_response += f"   • Settings > Security and Login > Two-Factor Authentication\n"
        bot_response += f"   • Ưu tiên Authenticator app\n\n"

        bot_response += f"3️⃣ **Banking Apps**\n"
        bot_response += f"   • Settings > Security > Enable 2FA\n"
        bot_response += f"   • Sử dụng hardware token khi có thể\n\n"

        bot_response += f"✅ **Best Practices:**\n"
        bot_response += f"• Sử dụng authenticator apps (Google Auth, Authy)\n"
        bot_response += f"• Backup codes được lưu an toàn\n"
        bot_response += f"• Regular audit của connected devices\n"
        bot_response += f"• Tránh SMS 2FA (vulnerable to SIM swapping)\n"
        bot_response += f"• Không share 2FA codes với bất kỳ ai\n\n"

        bot_response += f"🛡️ **Password Manager:**\n"
        bot_response += f"**Khuyến nghị:**\n"
        bot_response += f"• Bitwarden (free, open source)\n"
        bot_response += f"• 1Password (paid, user-friendly)\n"
        bot_response += f"• KeePassXC (free, offline)\n\n"

        bot_response += f"**Features quan trọng:**\n"
        bot_response += f"• Cross-platform sync\n"
        bot_response += f"• Secure sharing (nếu cần)\n"
        bot_response += f"• Emergency access\n"
        bot_response += f"• Security audit\n\n"

        bot_response += f"🔑 **Additional Security:**\n"
        bot_response += f"• Biometric authentication (fingerprint, face ID)\n"
        bot_response += f"• Hardware keys (YubiKey)\n"
        bot_response += f"• Security questions (nếu không thể tránh)\n"
        bot_response += f"• Account recovery options verified"

        dispatcher.utter_message(text=bot_response)
        return []


# ============================================================================
# NATIVE RASA FALLBACK ACTIONS (Phase 1.1)
# ============================================================================

class ActionDefaultFallback(Action):
    """
    Native Rasa Fallback Action - triggered when confidence < threshold

    This action replaces the hybrid routing layer's fallback logic by calling
    LLM directly from Rasa when intent confidence is low.
    """

    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        try:
            # Get user message
            message = ""
            if tracker.latest_message:
                message = tracker.latest_message.get('text', '')

            # Get user context
            user_id = tracker.get_slot("user_id") or tracker.sender_id

            # Format conversation history from tracker events
            history = self._format_conversation_history(tracker)

            # Get RAG context
            rag_context = self._get_rag_context(message)

            # Get user security context for personalization
            security_context = self._get_user_security_context(user_id)

            # Call LLM with full context
            from backend.llm.gemini_service import get_gemini_service_singleton
            llm = get_gemini_service_singleton()

            # Build security-aware system prompt
            system_prompt = self._build_security_system_prompt(security_context)

            # Generate LLM response
            response = llm.generate_response(
                message=message,
                context=rag_context,
                history=history,
                system_prompt=system_prompt
            )

            # Send response
            dispatcher.utter_message(text=response)

            # Log fallback to intent_analytics for active learning
            self._log_fallback_query(user_id, message, response)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Fallback action error: {e}")
            dispatcher.utter_message(
                text="Xin lỗi, tôi không hiểu yêu cầu của bạn. "
                     "Bạn có thể hỏi về kiểm tra URL, mật khẩu, CVE hoặc các vấn đề bảo mật khác."
            )

        return []

    def _format_conversation_history(self, tracker: Tracker) -> List[Dict[str, str]]:
        """Format Rasa tracker events into conversation history for LLM"""
        history = []

        # Get recent events from tracker
        events = list(tracker.events)[-10:]  # Last 10 events

        for event in events:
            if event.get('event') == 'user':
                text = event.get('text', '')
                if text:
                    history.append({'role': 'user', 'content': text})
            elif event.get('event') == 'bot':
                text = event.get('text', '')
                if text:
                    history.append({'role': 'assistant', 'content': text})

        return history

    def _get_rag_context(self, message: str) -> str:
        """Retrieve relevant security context from RAG"""
        try:
            from backend.rag.retriever import get_retriever

            retriever = get_retriever()
            if retriever:
                docs = retriever.retrieve(message, n_results=3)
                if docs:
                    # Use retriever's format_context method to properly format documents
                    return retriever.format_context(docs, max_length=1000)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"RAG retrieval failed: {e}")

        return ""

    def _get_user_security_context(self, user_id: Any) -> Dict[str, Any]:
        """Get user security context from database"""
        try:
            if not user_id:
                return {}

            from backend.database.crud.users import get_user
            user = get_user(user_id)

            if user and user.security_context:
                return user.security_context

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get user context: {e}")

        return {}

    def _build_security_system_prompt(self, security_context: Dict[str, Any]) -> str:
        """Build security-aware system prompt with user context"""
        base_prompt = """Bạn là CyberSec Assistant, trợ lý AI chuyên về an ninh mạng hỗ trợ người dùng Việt Nam.

**Nhiệm vụ:**
- Trả lời câu hỏi về bảo mật mạng một cách dễ hiểu
- Cung cấp hướng dẫn an toàn, thực tế
- Cảnh báo về rủi ro bảo mật một cách rõ ràng
- Giọng văn: thân thiện, chuyên nghiệp, dễ hiểu

**Phạm vi:**
- Kiểm tra URL an toàn (phishing, malware)
- Đánh giá độ mạnh mật khẩu
- Tra cứu CVE và lỗ hổng bảo mật
- Cung cấp mẹo bảo mật hàng ngày
- Hướng dẫn phản hồi sự cố bảo mật

**Quy tắc:**
- Luôn cảnh báo về rủi ro một cách rõ ràng
- Cung cấp hướng dẫn cụ thể, khả thi
- Sử dụng emoji để làm cho thông tin dễ đọc hơn
- Giữ câu trả lời ngắn gọn, súc tích (dưới 300 chữ)"""

        if security_context:
            role = security_context.get('role_level', 'beginner')
            interests = security_context.get('security_interests', [])

            base_prompt += f"\n\n**Người dùng là:** {role}"
            if interests:
                base_prompt += f"\n**Quan tâm:** {', '.join(interests)}"

        return base_prompt

    def _log_fallback_query(self, user_id: Any, message: str, response: str):
        """Log fallback queries to intent_analytics for active learning"""
        try:
            # Include all columns for the enhanced schema
            insert_data = {
                'query': message,
                'predicted_intent': 'nlu_fallback',
                'confidence': 0.0,
                'fallback_used': True,
                'review_status': 'pending',
                'added_to_training': False
            }
            # Only add user_id if it exists (nullable field)
            if user_id:
                insert_data['user_id'] = str(user_id)

            supabase_admin.table('intent_analytics').insert(insert_data).execute()
        except Exception as e:
            # Silently fail - analytics shouldn't break the chat flow
            import logging
            logger = logging.getLogger(__name__)
            # Only log unexpected errors, not schema/cache issues
            if 'review_status' not in str(e) and 'schema cache' not in str(e):
                logger.warning(f"Failed to log fallback: {e}")


class ActionAskUrl(Action):
    """Action to ask for URL when required slot is missing"""

    def name(self) -> Text:
        return "action_ask_url"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(
            text="🔍 **Vui lòng cung cấp URL cần kiểm tra:**\n\n"
                  "Nhập URL bạn muốn quét (ví dụ: https://example.com)"
        )
        return []


class ActionAskPassword(Action):
    """Action to ask for password when required slot is missing"""

    def name(self) -> Text:
        return "action_ask_password"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(
            text="🔐 **Vui lòng nhập mật khẩu cần đánh giá:**\n\n"
                  "⚠️ Lưu ý: Mật khẩu của bạn chỉ được sử dụng để tính toán độ mạnh "
                  "và KHÔNG được lưu trữ."
        )
        return []


class ActionAskCveId(Action):
    """Action to ask for CVE ID when required slot is missing"""

    def name(self) -> Text:
        return "action_ask_cve_id"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(
            text="📋 **Vui lòng nhập CVE ID cần tra cứu:**\n\n"
                  "Định dạng: CVE-YYYY-NNNN (ví dụ: CVE-2024-1234)"
        )
        return []


# ============================================================================
# KNOWLEDGE BASE ACTION (Phase 3.2: Semantic Graph Search)
# ============================================================================

class ActionKnowledgeBaseQuery(Action):
    """
    Knowledge Base Action for complex security queries.

    Enables semantic graph search for questions like:
    - "Router Cisco IOS 15.1 có bị CVE-2024-1234 ảnh hưởng không?"
    - "Which devices are affected by this CVE?"
    - "What patches are available?"
    """

    def name(self) -> Text:
        return "action_knowledge_base_query"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        try:
            # Get user message
            message = ""
            if tracker.latest_message:
                message = tracker.latest_message.get('text', '')

            # Extract entities
            latest_message = tracker.latest_message
            entities = {}
            if latest_message and latest_message.get('entities'):
                entities = {e['entity']: e['value'] for e in latest_message['entities']}

            # Get user context
            user_id = tracker.get_slot("user_id") or tracker.sender_id
            security_context = self._get_user_security_context(user_id)

            # Import knowledge base
            from backend.knowledge_base.graph_client import get_knowledge_base_singleton
            kg = get_knowledge_base_singleton()

            # Determine query type based on entities and message
            response = self._process_knowledge_query(message, entities, kg, security_context)

            dispatcher.utter_message(text=response)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Knowledge base query error: {e}")
            dispatcher.utter_message(
                text="Xin lỗi, tôi gặp sự cố khi truy vấn cơ sở kiến thức. "
                     "Vui lòng thử lại hoặc hỏi một cách khác."
            )

        return []

    def _get_user_security_context(self, user_id: Any) -> Dict[str, Any]:
        """Get user security context for personalization"""
        try:
            if not user_id:
                return {}

            from backend.database.crud.users import get_user
            user = get_user(user_id)

            if user and user.security_context:
                return user.security_context

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get user context: {e}")

        return {}

    def _process_knowledge_query(
        self,
        message: str,
        entities: Dict[str, str],
        kg: 'SecurityKnowledgeGraph',
        user_context: Dict[str, Any]
    ) -> str:
        """Process knowledge base query and return response"""

        message_lower = message.lower()

        # Check if query is about CVE affecting a device
        if 'cve' in message_lower and ('router' in message_lower or 'firewall' in message_lower or
                                         'server' in message_lower or 'device' in message_lower):
            return self._handle_cve_device_query(message, entities, kg)

        # Check if query is about device vulnerabilities
        if 'vulnerability' in message_lower or 'lỗ hổng' in message_lower:
            if 'router' in message_lower or 'firewall' in message_lower or 'server' in message_lower:
                return self._handle_device_vulnerability_query(message, entities, kg)

        # Check if query is about patch availability
        if 'patch' in message_lower or 'bản vá' in message_lower or 'khắc phục' in message_lower:
            return self._handle_patch_query(message, entities, kg)

        # Check if asking about a specific CVE's impact
        cve_entity = entities.get('cve_id')
        if cve_entity and ('ảnh hưởng' in message_lower or 'affect' in message_lower):
            return self._handle_cve_impact_query(cve_entity, kg)

        # Default: try to extract information and provide helpful response
        return self._handle_general_kb_query(message, entities, kg, user_context)

    def _handle_cve_device_query(
        self,
        message: str,
        entities: Dict[str, str],
        kg: 'SecurityKnowledgeGraph'
    ) -> str:
        """Handle query: "CVE-XXX affects device XYZ?" """
        cve_id = entities.get('cve_id')
        if not cve_id:
            # Try to extract CVE from message
            import re
            cve_match = re.search(r'CVE-\d{4}-\d{4,}', message, re.IGNORECASE)
            if cve_match:
                cve_id = cve_match.group(0)
            else:
                return "❌ Vui lòng cung cấp CVE ID để kiểm tra."

        # Extract device info from message
        device_type = None
        vendor = None

        if 'router' in message.lower() or 'cisco' in message.lower():
            device_type = 'router'
            if 'cisco' in message.lower():
                vendor = 'Cisco'
        elif 'firewall' in message.lower():
            device_type = 'firewall'
        elif 'server' in message.lower():
            device_type = 'server'

        # Query CVE impact
        affected_devices = kg.query_cve_device_impact(cve_id)

        if not affected_devices:
            return f"""📋 **CVE: {cve_id.upper()}**

❌ Không tìm thấy thông tin về các thiết bị bị ảnh hưởng.

Có thể:
• CVE ID không chính xác
• Chưa có dữ liệu về thiết bị bị ảnh hưởng
• CVE chưa được phân tích trong cơ sở kiến thức"""

        # Filter by device type if specified
        if device_type:
            affected_devices = [d for d in affected_devices if d['device_type'] == device_type]
        if vendor:
            affected_devices = [d for d in affected_devices if d['vendor'] == vendor]

        response = f"📋 **CVE: {cve_id.upper()}** - Thiết bị bị ảnh hưởng\n\n"

        if not affected_devices:
            response += f"✅ {device_type or 'Thiết bị'} của bạn KHÔNG bị ảnh hưởng bởi CVE này."
        else:
            response += f"⚠️ **CÓ {len(affected_devices)} thiết bị bị ảnh hưởng:**\n\n"

            for device in affected_devices[:5]:
                details = device.get('details', {})
                severity_emoji = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(details.get('severity'), '⚪')

                response += f"• {severity_emoji} **{device['vendor']} {device['device_type']}** ({device['os_version']})\n"
                response += f"  Severity: {details.get('severity', 'Unknown').upper()} (CVSS: {details.get('cvss', 'N/A')})\n"

                if details.get('patched_versions'):
                    response += f"  ✅ Patch available: {', '.join(details['patched_versions'][:2])}\n"

                response += "\n"

        return response

    def _handle_device_vulnerability_query(
        self,
        message: str,
        entities: Dict[str, str],
        kg: 'SecurityKnowledgeGraph'
    ) -> str:
        """Handle query: "What vulnerabilities affect router XYZ?" """
        # Extract device info
        device_type = None
        vendor = None
        os_version = None

        if 'router' in message.lower():
            device_type = 'router'
            if 'cisco' in message.lower():
                vendor = 'Cisco'
            elif 'juniper' in message.lower():
                vendor = 'Juniper'
        elif 'firewall' in message.lower():
            device_type = 'firewall'
            if 'palo' in message.lower() or 'pan' in message.lower():
                vendor = 'Palo Alto'
            elif 'fortinet' in message.lower() or 'forti' in message.lower():
                vendor = 'Fortinet'
        elif 'server' in message.lower():
            device_type = 'server'
            if 'windows' in message.lower():
                vendor = 'Windows'
            elif 'linux' in message.lower() or 'ubuntu' in message.lower():
                vendor = 'Linux'

        # Query vulnerabilities
        vulns = kg.query_device_vulnerabilities(device_type, vendor, os_version)

        if not vulns:
            return f"""🔍 **Lỗ hổng bảo mật**

{'✅ Không tìm thấy lỗ hổng nào' if device_type else 'Vui lòng cung cấp thông tin thiết bị'} cho {vendor or ''} {device_type or ''} {os_version or ''}.

**Tip:** Hãy thử hỏi cụ thể hơn:
• "Router Cisco IOS 15.1 có lỗ hổng nào?"
• "Firewall Palo Alto có bị CVE nào ảnh hưởng?"
            """

        response = f"🔍 **Lỗ hổng bảo mật:** {vendor or 'Thiết bị'} {device_type or ''}\n\n"

        # Group by severity
        critical_vulns = [v for v in vulns if v.get('details', {}).get('severity') == 'critical']
        high_vulns = [v for v in vulns if v.get('details', {}).get('severity') == 'high']
        other_vulns = [v for v in vulns if v.get('details', {}).get('severity') not in ['critical', 'high']]

        if critical_vulns:
            response += f"🔴 **CRITICAL ({len(critical_vulns)}):**\n"
            for v in critical_vulns[:3]:
                response += f"• {v['cve_id']} - {v.get('details', {}).get('description', 'N/A')}\n"
            response += "\n"

        if high_vulns:
            response += f"🟠 **HIGH ({len(high_vulns)}):**\n"
            for v in high_vulns[:3]:
                response += f"• {v['cve_id']} - {v.get('details', {}).get('description', 'N/A')}\n"
            response += "\n"

        if other_vulns and len(other_vulns) <= 5:
            response += f"🟡 **OTHER ({len(other_vulns)}):**\n"
            for v in other_vulns[:3]:
                response += f"• {v['cve_id']}\n"

        return response

    def _handle_patch_query(
        self,
        message: str,
        entities: Dict[str, str],
        kg: 'SecurityKnowledgeGraph'
    ) -> str:
        """Handle query: "Is patch available for CVE-XXX?" """
        cve_id = entities.get('cve_id')

        if not cve_id:
            import re
            cve_match = re.search(r'CVE-\d{4}-\d{4,}', message, re.IGNORECASE)
            if cve_match:
                cve_id = cve_match.group(0)
            else:
                return "❌ Vui lòng cung cấp CVE ID để kiểm tra patch."

        patch_info = kg.query_patch_availability(cve_id)

        if not patch_info.get('found'):
            return f"❌ Không tìm thấy thông tin cho CVE: {cve_id.upper()}"

        response = f"📋 **Patch Availability: {cve_id.upper()}**\n\n"
        response += f"**Severity:** {patch_info.get('severity', 'Unknown').upper()}\n"
        response += f"**CVSS:** {patch_info.get('cvss', 'N/A')}\n\n"

        if patch_info.get('patch_available'):
            patched = patch_info.get('patched_versions', [])
            response += f"✅ **PATCH CÓ SẴN**\n\n"
            response += f"**Phiên bản đã patch:**\n"
            for version in patched:
                response += f"• {version}\n"
        else:
            response += f"❌ **CHƯA CÓ PATCH**\n\n"
            response += f"Hiện tại chưa có bản vá cho CVE này.\n"
            response += f"**Khuyến nghị:** Monitor và chờ thông báo từ vendor."

        return response

    def _handle_cve_impact_query(
        self,
        cve_id: str,
        kg: 'SecurityKnowledgeGraph'
    ) -> str:
        """Handle query: "Which devices are affected by CVE-XXX?" """
        affected = kg.query_cve_device_impact(cve_id)

        response = f"📋 **CVE: {cve_id.upper()}** - Thiết bị bị ảnh hưởng\n\n"

        if not affected:
            response += "Không tìm thấy thiết bị nào bị ảnh hưởng trong cơ sở kiến thức."
        else:
            response += f"⚠️ **{len(affected)} thiết bị bị ảnh hưởng:**\n\n"

            for device in affected:
                response += f"• **{device['vendor']} {device['device_type']}** ({device['os_version']})\n"

        return response

    def _handle_general_kb_query(
        self,
        message: str,
        entities: Dict[str, str],
        kg: 'SecurityKnowledgeGraph',
        user_context: Dict[str, Any]
    ) -> str:
        """Handle general knowledge base query with LLM assistance"""
        try:
            # Try to use LLM to understand and answer
            from backend.llm.gemini_service import get_gemini_service_singleton

            llm = get_gemini_service_singleton()

            system_prompt = """Bạn là trợ lý bảo mật mạng với quyền truy cập vào Knowledge Base.

Hãy trả lời câu hỏi của người dùng về:
- CVE và lỗ hổng bảo mật
- Thiết bị bị ảnh hưởng
- Bản vá và khắc phục

Nếu không có đủ thông tin, hãy yêu cầu người dùng cung cấp thêm chi tiết."""

            # Build context about available knowledge
            context = "Knowledge Base có thông tin về:\n"
            context += "- CVE và severity/CVSS scores\n"
            context += "- Thiết bị bị ảnh hưởng (Router, Firewall, Server)\n"
            context += "- Các vendor: Cisco, Juniper, Palo Alto, Fortinet, Windows, Linux\n"
            context += "- Bản vá có sẵn\n\n"
            context += f"Câu hỏi: {message}"

            response = llm.generate_response(
                message=message,
                context=context,
                system_prompt=system_prompt
            )

            return response

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"LLM KB query failed: {e}")

            return """🔍 **Knowledge Base Query**

Tôi có thể giúp bạn tìm hiểu về:
• CVE và lỗ hổng bảo mật cụ thể
• Thiết bị bị ảnh hưởng bởi CVE
• Bản vá có sẵn cho từng CVE

**Ví dụ câu hỏi:**
• "CVE-2024-1234 ảnh hưởng thiết bị nào?"
• "Router Cisco IOS 15.1 có lỗ hổng nào?"
• "Patch cho CVE-2024-1234 có sẵn chưa?"

Hãy hỏi cụ thể hơn để tôi có thể giúp bạn!"""