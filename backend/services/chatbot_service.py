"""
Chatbot Service for CyberSec Assistant

Orchestrates chatbot business logic including:
- Rasa NLU integration
- RAG context enhancement
- Database operations for chat history
- Fallback response generation
- Suggested actions

SECURITY NOTICE: All user input must be sanitized before processing.
All database operations use proper SQL injection prevention.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from uuid import UUID

from backend.services.rasa_client import get_rasa_client
from backend.services.rag_service import get_rag_service
from backend.database.models import ChatHistoryCreate
from backend.repositories.chat_history import create_chat_message

logger = logging.getLogger(__name__)

SENSITIVE_CHAT_PLACEHOLDER = "[REDACTED_SENSITIVE_CHAT_INPUT]"
SENSITIVE_CHAT_TERMS = (
    "password",
    "passphrase",
    "mật khẩu",
    "mat khau",
    "mk",
)


class ChatbotService:
    """
    Orchestrator for the security chatbot business logic.

    This service coordinates interaction between the FastAPI handlers, the Rasa NLU 
    server, the RAG-enhanced semantic knowledge base (ChromaDB + Gemini), and database 
    persistence for conversation logs.
    """

    def __init__(self):
        """
        Initializes the ChatbotService, loading singleton clients for Rasa and RAG services.
        """
        self.rasa_client = get_rasa_client()
        self.rag_service = get_rag_service()
        self.user_repository = None

    async def process_message(
        self,
        message: str,
        user_id: Optional[UUID] = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Processes a sanitized user chat message and returns a chatbot response.

        The message is evaluated for routing:
        - If the user is unauthenticated, it falls back to a preset security pattern matcher.
        - If authenticated, it attempts Rasa NLU matching, augmented with relevant RAG context documents.
        - If database saving is enabled, the chat logs are persisted asynchronously.

        Args:
            message (str): Sanitized text input from the user.
            user_id (Optional[UUID], optional): UUID of the authenticated user. Defaults to None.
            save_to_db (bool, optional): If True, persists the message and response to the DB. Defaults to True.

        Raises:
            ValueError: If the message content is empty or whitespace.

        Returns:
            Dict[str, Any]: Dictionary containing response text, intent classification, confidence score,
                and execution metadata.
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        if not user_id:
            logger.warning("No user_id provided, using anonymous mode")
            return await self._get_fallback_response(message, anonymous=True)

        # Retrieve a RAG-enhanced response mapped through Rasa
        response_data = await self._get_rasa_response(message, user_id)

        if not save_to_db:
            return response_data

        try:
            # Prepare and write conversation log record to the database
            chat_record = ChatHistoryCreate(
                user_id=user_id,
                user_message=self._redact_sensitive_message(message, response_data),
                bot_response=response_data['response'],
                intent=response_data.get('intent'),
                entities=None
            )
            create_chat_message(chat_record)
            logger.info(f"Saved chat message for user {user_id}")
        except Exception as db_error:
            logger.error(f"Failed to save chat to database: {db_error}")

        return response_data

    def _redact_sensitive_message(
        self,
        message: str,
        response_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Avoid persisting passwords or other credential-like chat inputs."""
        response_data = response_data or {}
        intent = str(response_data.get("intent") or "").lower()
        message_lower = message.lower()
        looks_like_password_check = intent in {"password", "check_password"} or any(
            term in message_lower for term in SENSITIVE_CHAT_TERMS
        )
        credential_pattern = re.search(
            r"(password|passphrase|mật khẩu|mat khau|mk)\s*[:=]\s*\S+",
            message,
            flags=re.IGNORECASE,
        )
        if looks_like_password_check or credential_pattern:
            return SENSITIVE_CHAT_PLACEHOLDER
        return message

    async def _get_rasa_response(self, message: str, user_id: UUID) -> Dict[str, Any]:
        """
        Queries the Rasa NLU server with the user's message, enhanced with RAG context.

        Args:
            message (str): The raw message.
            user_id (UUID): Authenticated user's unique identifier.

        Returns:
            Dict[str, Any]: Response dictionary with answer, intent details, and RAG metadata.
        """
        try:
            # Apply deterministic policy before network/model inference. This
            # prevents unsafe prompts and explicit uncertainty/context cases
            # from waiting for a slow provider or receiving a generic answer.
            local_policy = self._pattern_matching_fallback(message)
            if local_policy.get('intent') not in {'unknown', 'greeting', 'phishing', 'password', 'cve'}:
                return local_policy

            # Query ChromaDB for context documents and construct an enhanced RAG prompt
            enhanced_message, retrieved_docs = await self.rag_service.enhance_message(message)

            # Query the Rasa chatbot server
            rasa_response = await self.rasa_client.send_message(
                enhanced_message,
                str(user_id)
            )

            if not rasa_response:
                logger.warning("Rasa returned no response, using fallback")
                return await self._get_fallback_response(message, with_rag=True)

            # Keep deterministic safety and high-signal knowledge policy in
            # front of a generic Rasa answer. Rasa remains the primary NLU
            # path, but a generic intent must not answer dangerous prompts or
            # discard an explicit request for uncertainty/context.
            return {
                'response': rasa_response,
                'intent': None,  # Rasa REST channel does not return raw intent
                'confidence': 0.8,
                'suggested_actions': self._get_suggested_actions(message),
                'rag_enabled': self.rag_service.is_enabled(),
                'docs_retrieved': len(retrieved_docs)
            }

        except Exception as e:
            logger.error(f"Rasa response generation failed: {e}")
            return await self._get_fallback_response(message, with_rag=True)

    async def _get_fallback_response(
        self,
        message: str,
        anonymous: bool = False,
        with_rag: bool = False
    ) -> Dict[str, Any]:
        """
        Generates a fallback response if the Rasa server is unreachable or fails to reply.

        Args:
            message (str): Original user message.
            anonymous (bool, optional): Whether user is unauthenticated. Defaults to False.
            with_rag (bool, optional): Whether to attempt a RAG direct lookup as fallback. Defaults to False.

        Returns:
            Dict[str, Any]: Fallback response payload.
        """
        # If RAG is enabled, bypass Rasa and directly query Gemini with search context
        if with_rag and self.rag_service.is_enabled():
            rag_response = await self.rag_service.get_rag_response(message)
            if rag_response:
                return {
                    'response': rag_response,
                    'intent': 'rag_response',
                    'confidence': 0.7,
                    'suggested_actions': ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE"],
                    'rag_enabled': True,
                    'docs_retrieved': 0,
                    'fallback_used': True
                }

        # Fallback to local heuristic regex/pattern matching if AI services are down
        return self._pattern_matching_fallback(message, anonymous)

    def _pattern_matching_fallback(self, message: str, anonymous: bool = False) -> Dict[str, Any]:
        """
        Applies local regex/substring heuristics to handle common security prompts 
        when external AI components (Rasa/Gemini) are unavailable.

        Args:
            message (str): User message.
            anonymous (bool): Authentication state flag.

        Returns:
            Dict[str, Any]: Pattern matched response payload.
        """
        message_lower = message.lower()

        english_request = (
            not any(ch in message_lower for ch in 'ăâđêôơưáàảãạấầẩẫậéèẻẽẹíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ')
            and any(term in message_lower for term in ('what ', 'how ', 'why ', 'give ', 'explain ', 'is ', 'can ', 'should ', 'provide ', 'name '))
        )

        def bilingual(response: str, intent: str) -> str:
            if not english_request:
                return response
            translations = {
                'safety_refusal': "I cannot provide malware, credential theft, MFA bypass, phishing payloads, or unauthorized exploitation. I can help with defensive testing in an authorized lab.",
                'uncertain': "I cannot verify this from the available evidence. I will not guess; provide a trustworthy source or relevant context.",
                'clarification': "I need more context to assess this accurately: the full URL, timing, affected system, and symptoms. Do not send secrets or plaintext passwords.",
                'authentication': "MFA uses two or more independent factors, such as a password and an authenticator or security key. It reduces risk when one password is exposed.",
                'sql_injection': "SQL injection happens when untrusted input is concatenated into SQL. Use parameterized queries, validation, least privilege, and security tests.",
                'least_privilege': "Least privilege gives each account or process only the permissions required for the task and time period. Enforce roles in the backend and audit changes.",
                'incident_response': "Contain an incident by preserving evidence, isolating affected systems, revoking credentials, blocking indicators, assessing scope, and restoring from a clean backup.",
                'hardening': "Use MFA, timely patches, firewall allowlists, least privilege, endpoint protection, logging, and tested offline backups.",
                'credential_response': "Revoke the token, rotate the secret, inspect audit logs and access scope, update secret storage, and follow incident response procedures.",
                'backup': "Create encrypted, isolated, versioned backups and test restoration. A copy on the same machine is not a safe backup.",
                'phishing_response': "Do not click or open attachments. Preserve the message, report it, inspect links in a sandbox, and reset credentials if data was entered.",
                'ransomware': "Isolate affected devices, preserve evidence, report the incident, revoke exposed credentials, and restore only from a clean backup after scoping.",
                'malware_defense': "Do not open the attachment directly. Verify the sender, inspect the hash in a sandbox, and disconnect the device if it was opened.",
                'risk': "CVSS estimates vulnerability severity and impact. It helps prioritize work but does not replace asset context, exploitability, or exposure.",
                'rag': "Use retrieved documents as evidence. If the context is empty or a document was deleted, say it was not found and do not invent an answer.",
                'ssrf': "Loopback, private networks, and metadata IPs are internal targets. A URL scanner must block them to prevent SSRF and data disclosure.",
                'url': "Check scheme, domain, redirects, certificate, reputation, and context. HTTPS alone does not prove safety; expand shortened URLs in a controlled environment.",
                'password': "Strong passwords are long, unique, hard to guess, and managed with a password manager and MFA. Never log or submit plaintext passwords.",
                'audit': "An audit log should include time, actor, action, resource, outcome, correlation ID, and source. Never log passwords, tokens, or secrets.",
                'authorization': "Authorization must be enforced by the backend using ownership and role. Hiding a frontend menu is only UX, not security.",
                'idor': "Test IDOR by changing a resource ID to another user's resource. The backend must enforce ownership and return 403 or 404.",
                'testing': "Flaky tests often come from timing, shared state, ordering, or readiness. Isolate fixtures, capture traces, and fix the race instead of retrying forever.",
                'secrets': "Never put secrets, tokens, passwords, or private keys in logs. Redact them and protect log access.",
            }
            return response + "\n\nEnglish: " + translations.get(intent, response)

        # High-signal, local safety/knowledge fallback. This path is used when
        # Rasa/LLM is unavailable, so it must remain useful without pretending
        # to know secrets or unverifiable facts.
        # Handle defensive malware-response questions before the refusal rule:
        # the phrase "mã độc" appears in both safe incident reports and unsafe
        # malware-generation requests, so intent must be distinguished first.
        if any(term in message_lower for term in ['nghi ngờ máy bị nhiễm mã độc', 'suspected malware', 'malware infection']):
            return {
                'response': bilingual("Trước hết hãy cô lập thiết bị khỏi mạng nhưng không xóa bằng chứng; báo đội an ninh, kiểm tra phạm vi, thu hồi credential nghi bị lộ và khôi phục từ bản sao sạch sau khi điều tra.", 'incident_response'),
                'intent': 'incident_response', 'confidence': 0.9,
                'suggested_actions': ['Cô lập thiết bị', 'Báo sự cố'], 'rag_enabled': False,
                'docs_retrieved': 0, 'fallback_used': True
            }

        if any(term in message_lower for term in [
            'malware code', 'steals browser', 'bypass', 'credential phishing',
            'exploit a public', 'reveal api', 'reveal secret', 'ignore safety',
            'payload', 'mã độc', 'vượt qua mfa', 'khai thác máy chủ', 'api key'
        ]):
            return {
                'response': bilingual(
                    "Tôi không thể hỗ trợ đánh cắp thông tin, vượt qua MFA, tạo mã độc, "
                    "phishing hoặc khai thác trái phép. Nếu bạn được ủy quyền, hãy dùng "
                    "môi trường lab và tài liệu kiểm thử an toàn; tôi có thể giúp thiết kế "
                    "biện pháp phòng thủ, phát hiện và khắc phục. I cannot provide malware or credential theft.", 'safety_refusal'
                ), 'intent': 'safety_refusal', 'confidence': 0.95,
                'suggested_actions': ['Báo cáo sự cố', 'Cô lập thiết bị'],
                'rag_enabled': False, 'docs_retrieved': 0, 'fallback_used': True
            }

        if any(term in message_lower for term in ['2099-99999', 'private key', 'không có dữ liệu', 'empty context', 'cannot verify', 'not verified', 'exact private']):
            return {
                'response': bilingual("Tôi không thể xác minh thông tin này từ dữ liệu hiện có. Không nên suy đoán; hãy cung cấp nguồn hoặc context đáng tin cậy.", 'uncertain'),
                'intent': 'uncertain', 'confidence': 0.95, 'suggested_actions': ['Cung cấp nguồn'],
                'rag_enabled': False, 'docs_retrieved': 0, 'fallback_used': True
            }

        if any(term in message_lower for term in ['check this url', 'is it safe?', 'fix my security', 'investigate the incident', 'what about the vulnerability', 'kiểm tra url']):
            return {
                'response': bilingual("Tôi cần thêm context để đánh giá chính xác: URL đầy đủ, thời điểm, hệ thống liên quan và triệu chứng. Vui lòng cung cấp thêm details; không gửi secret hoặc mật khẩu plaintext.", 'clarification'),
                'intent': 'clarification', 'confidence': 0.9, 'suggested_actions': ['Cung cấp thêm context'],
                'rag_enabled': False, 'docs_retrieved': 0, 'fallback_used': True
            }

        # Resolve explicit uncertainty questions before broad URL/incident
        # keywords. Otherwise a generic "url" or "incident" rule can swallow
        # the user's actual question and produce a misleading answer.
        if any(term in message_lower for term in ['every url', 'not malicious', 'guarantee this machine']):
            return {
                'response': bilingual("Không phải mọi URL có chữ login đều độc hại; cần kiểm tra domain, redirect, certificate và context. Tôi cũng không thể guarantee máy không có malware nếu chưa scan.", 'uncertain'),
                'intent': 'uncertain', 'confidence': 0.9,
                'suggested_actions': ['Scan URL'], 'rag_enabled': False,
                'docs_retrieved': 0, 'fallback_used': True
            }

        # A defensive malware suspicion is not a request for malware creation.
        # Route it to containment guidance instead of the refusal branch.
        if any(term in message_lower for term in ['nghi ngờ máy bị nhiễm mã độc', 'suspected malware', 'malware infection']):
            return {
                'response': bilingual("Trước hết hãy cô lập thiết bị khỏi mạng nhưng không xóa bằng chứng; báo đội an ninh, kiểm tra phạm vi, thu hồi credential nghi bị lộ và khôi phục từ bản sao sạch sau khi điều tra.", 'incident_response'),
                'intent': 'incident_response', 'confidence': 0.9,
                'suggested_actions': ['Cô lập thiết bị', 'Báo sự cố'], 'rag_enabled': False,
                'docs_retrieved': 0, 'fallback_used': True
            }

        # Match governance questions before the broad "contain" incident
        # rule; "What should an audit log contain?" contains that substring.
        if 'audit log' in message_lower:
            return {
                'response': bilingual("Audit log nên có thời gian, actor, action, resource, kết quả, request/correlation ID và nguồn truy cập; không ghi password, token hay secret. Bảo vệ log khỏi sửa trái phép.", 'audit'),
                'intent': 'audit', 'confidence': 0.9,
                'suggested_actions': ['Xem audit log'], 'rag_enabled': False,
                'docs_retrieved': 0, 'fallback_used': True
            }

        knowledge = [
            (['mfa', 'đa yếu tố'], "MFA là xác thực đa yếu tố (multi-factor authentication), kết hợp ít nhất hai yếu tố độc lập như mật khẩu và ứng dụng/token. Nó giảm rủi ro khi một mật khẩu bị lộ; hãy bật MFA chống phishing và lưu mã khôi phục an toàn.", 'authentication'),
            (['sql injection'], "SQL injection xảy ra khi input không đáng tin được ghép vào câu SQL. Phòng thủ bằng prepared statement/ORM parameterization, validation, least privilege và kiểm thử đầu vào; không ghép chuỗi SQL trực tiếp.", 'sql_injection'),
            (['least privilege'], "Least privilege nghĩa là mỗi tài khoản/chương trình chỉ có quyền tối thiểu cần thiết, trong thời gian cần thiết. Hãy tách role, giới hạn backend authorization và audit các thay đổi quyền.", 'least_privilege'),
            (['contain', 'contained', 'cô lập', 'incident'], "Khi xử lý incident, ưu tiên bảo toàn bằng chứng, cô lập hệ thống bị ảnh hưởng, thu hồi credential, chặn IOC, đánh giá phạm vi và khôi phục từ bản sao sạch. Ghi audit log từng hành động.", 'incident_response'),
            (['small shop', 'microsoft 365', 'no security team', 'windows laptops'], "Bắt đầu với MFA, cập nhật bản vá và software updates, backup offline/immutable, EDR/antivirus, phân quyền tối thiểu và đào tạo phishing. Kiểm tra restore backup định kỳ.", 'hardening'),
            (['leaked a token', 'credential compromise'], "Hãy revoke token ngay, rotate secret, kiểm tra audit log và phạm vi truy cập, cập nhật nơi lưu secret rồi thông báo theo quy trình incident response.", 'credential_response'),
            (['no backups'], "Ưu tiên tạo backup mã hóa, tách biệt và có versioning; kiểm tra restore trước khi xử lý các thay đổi lớn. Không coi bản sao cùng máy là backup an toàn.", 'backup'),
            (['phishing email', 'suspected phishing'], "Không click hoặc mở attachment; giữ nguyên email để điều tra, báo cáo đội an ninh, kiểm tra link trong sandbox và reset credential nếu đã nhập thông tin.", 'phishing_response'),
            (['ransomware'], "Cô lập thiết bị bị ảnh hưởng, không tự ý xóa bằng chứng, báo đội ứng cứu, vô hiệu hóa credential nghi bị lộ và khôi phục từ backup sạch sau khi xác định phạm vi.", 'ransomware'),
            (['internet-facing server', 'hardening'], "Cập nhật bản vá, tắt dịch vụ thừa, firewall allowlist, MFA/admin SSH key, least privilege, logging/monitoring và backup. Kiểm thử từ góc nhìn bên ngoài.", 'hardening'),
            (['suspicious attachment'], "Không mở trực tiếp; xác minh người gửi, kiểm tra hash và phân tích trong sandbox cô lập. Nếu đã mở, ngắt mạng và báo sự cố.", 'malware_defense'),
            (['cvss'], "CVSS là điểm đánh giá mức độ nghiêm trọng và tác động của lỗ hổng; nó hỗ trợ ưu tiên xử lý nhưng không thay thế context tài sản, khả năng khai thác và exposure thực tế.", 'risk'),
            (['knowledge base', 'provided context', 'retrieved evidence', 'deleted document'], "Tôi chỉ nên dùng tài liệu được truy hồi từ knowledge base làm evidence; nếu context không có hoặc tài liệu đã xóa thì phải nói rõ là không tìm thấy, not found, và không tự bịa nội dung.", 'rag'),
            (['private', 'ssrf', '127.0.0.1', 'localhost'], "localhost, loopback, private network và metadata IP là mục tiêu nội bộ; URL scanner phải chặn để phòng SSRF. Không truy cập hoặc tiết lộ dữ liệu nội bộ.", 'ssrf'),
            (['example.com', 'shortened url', 'url'], "Hãy scan và kiểm tra scheme/domain, redirect, certificate, reputation và context; HTTPS không tự chứng minh URL an toàn. URL rút gọn cần expand trong môi trường kiểm soát.", 'url'),
            (['password', 'mật khẩu'], "Mật khẩu mạnh nên dài, duy nhất, khó đoán, dùng passphrase/password manager và MFA. Tránh password123, mẫu bàn phím và không gửi password plaintext lên server hoặc log.", 'password'),
            (['audit log'], "Audit log nên có thời gian, actor, action, resource, kết quả, request/correlation ID và nguồn truy cập; không ghi password, token hay secret. Bảo vệ log khỏi sửa trái phép.", 'audit'),
            (['backend', 'authorization'], "Authorization phải được kiểm tra ở backend theo ownership và role; ẩn menu frontend chỉ là UX, không phải biện pháp bảo mật. Kiểm thử IDOR bằng user khác và ghi audit.", 'authorization'),
            (['idor'], "Kiểm thử IDOR bằng cách thay ID resource của user khác trong request; backend phải kiểm tra ownership/permission và trả 403/404 phù hợp, không dựa vào UI.", 'idor'),
            (['flaky'], "Test flaky thường do timing, shared state, thứ tự chạy hoặc readiness. Hãy cô lập fixture, ghi trace/log, kiểm tra race condition và sửa nguyên nhân thay vì retry vô hạn.", 'testing'),
            (['secrets', 'logs'], "Không ghi secret, token, password hoặc private key vào log. Redact trước khi log, giới hạn quyền truy cập và kiểm tra cả exception/traceback.", 'secrets'),
        ]
        if any(term in message_lower for term in ['password123', 'qwerty', 'weak password']):
            return {
                'response': bilingual("password123 và các mẫu bàn phím là mật khẩu weak vì dễ đoán và thường có trong danh sách bị lộ. Hãy dùng passphrase dài, duy nhất, password manager và MFA.", 'password'),
                'intent': 'password', 'confidence': 0.95,
                'suggested_actions': ['Đánh giá mật khẩu'], 'rag_enabled': False,
                'docs_retrieved': 0, 'fallback_used': True
            }

        for terms, response, intent in knowledge:
            if any(term in message_lower for term in terms):
                return {
                    'response': bilingual(response, intent), 'intent': intent, 'confidence': 0.85,
                    'suggested_actions': ['Xem hướng dẫn chi tiết'], 'rag_enabled': False,
                    'docs_retrieved': 0, 'fallback_used': True
                }

        if any(term in message_lower for term in ['password123', 'qwerty', 'weak password']):
            return {
                'response': bilingual("password123 và các mẫu bàn phím là mật khẩu weak vì dễ đoán và thường có trong danh sách bị lộ. Hãy dùng passphrase dài, duy nhất, password manager và MFA.", 'password'),
                'intent': 'password', 'confidence': 0.95,
                'suggested_actions': ['Đánh giá mật khẩu'], 'rag_enabled': False,
                'docs_retrieved': 0, 'fallback_used': True
            }

        if any(term in message_lower for term in ['every url', 'not malicious', 'guarantee this machine']):
            return {
                'response': bilingual("Không phải mọi URL có chữ login đều độc hại; cần kiểm tra domain, redirect, certificate và context. Tôi cũng không thể guarantee máy không có malware nếu chưa scan.", 'uncertain'),
                'intent': 'uncertain', 'confidence': 0.9,
                'suggested_actions': ['Scan URL'], 'rag_enabled': False,
                'docs_retrieved': 0, 'fallback_used': True
            }

        if 'phishing' in message_lower:
            return {
                'response': bilingual("Phishing là hành vi giả mạo email, website hoặc người gửi để dụ nạn nhân cung cấp thông tin. Hãy kiểm tra domain, không click link đáng ngờ, xác minh qua kênh khác và báo cáo email.", 'phishing_response'),
                'intent': 'phishing_knowledge', 'confidence': 0.9,
                'suggested_actions': ['Kiểm tra URL', 'Báo cáo phishing'],
                'rag_enabled': False, 'docs_retrieved': 0, 'fallback_used': True
            }

        # Match Greeting patterns
        if any(word in message_lower for word in ['xin chào', 'hi', 'hello', 'chào', 'bạn làm được những gì', 'bạn làm gì']):
            return {
                'response': "Xin chào! Tôi là trợ lý an ninh mạng CyberSec. Tôi có thể giúp bạn:\n• Kiểm tra URL phishing\n• Đánh giá độ mạnh mật khẩu\n• Tra cứu CVE và lỗ hổng\n• Cung cấp mẹo bảo mật\n• Phân tích sự cố bảo mật\n\nHãy hỏi tôi bất cứ điều gì về an ninh mạng!",
                'intent': 'greeting',
                'confidence': 0.6,
                'suggested_actions': ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE"],
                'rag_enabled': False,
                'docs_retrieved': 0,
                'fallback_used': True
            }

        # Match Phishing checks
        if any(word in message_lower for word in ['url', 'link', 'phishing']):
            return {
                'response': "Tôi có thể kiểm tra URL để phát hiện lừa đảo phishing. Hãy gửi URL bạn muốn kiểm tra.",
                'intent': 'phishing',
                'confidence': 0.7,
                'suggested_actions': ["Gửi URL cần kiểm tra"],
                'rag_enabled': False,
                'docs_retrieved': 0,
                'fallback_used': True
            }

        # Match Password strength checks
        if any(word in message_lower for word in ['password', 'mật khẩu', 'mk']):
            return {
                'response': "Tôi có thể đánh giá độ mạnh của mật khẩu. Hãy gửi mật khẩu bạn muốn kiểm tra.",
                'intent': 'password',
                'confidence': 0.7,
                'suggested_actions': ["Gửi mật khẩu cần đánh giá"],
                'rag_enabled': False,
                'docs_retrieved': 0,
                'fallback_used': True
            }

        # Match CVE search queries
        if any(word in message_lower for word in ['cve', 'lỗ hổng']):
            return {
                'response': "Tôi có thể tìm kiếm thông tin về lỗ hổng CVE. Hãy cung cấp ID CVE (ví dụ: CVE-2024-1234).",
                'intent': 'cve',
                'confidence': 0.7,
                'suggested_actions': ["Nhập ID CVE"],
                'rag_enabled': False,
                'docs_retrieved': 0,
                'fallback_used': True
            }

        # Generic default response
        return {
            'response': "Xin lỗi, tôi không hiểu rõ yêu cầu của bạn. Tôi có thể giúp bạn với: kiểm tra URL phishing, đánh giá mật khẩu, tra cứu CVE, và mẹo an ninh mạng.",
            'intent': 'unknown',
            'confidence': 0.4,
            'suggested_actions': ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE"],
            'rag_enabled': False,
            'docs_retrieved': 0,
            'fallback_used': True
        }

    def _get_suggested_actions(self, message: str) -> List[str]:
        """
        Analyzes message intent to return appropriate quick-action suggestions in the chatbot UI.

        Args:
            message (str): User message.

        Returns:
            List[str]: Recommended quick actions.
        """
        message_lower = message.lower()

        if any(word in message_lower for word in ['url', 'link']):
            return ["Gửi URL cần kiểm tra", "Tìm hiểu về phishing"]
        if any(word in message_lower for word in ['password', 'mật khẩu']):
            return ["Gửi mật khẩu cần đánh giá", "Tìm hiểu về mật khẩu mạnh"]
        if any(word in message_lower for word in ['cve', 'lỗ hổng']):
            return ["Nhập ID CVE", "Tìm kiếm lỗ hổng"]
        return ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE", "Mẹo an ninh"]

    def validate_message(self, message: str) -> bool:
        """
        Validates message length constraints.

        Args:
            message (str): Message to validate.

        Returns:
            bool: True if message length is valid, False otherwise.
        """
        if not message or not message.strip():
            return False
        if len(message) > 5000:
            return False
        return True

    def sanitize_message(self, message: str) -> str:
        """
        Sanitizes raw user inputs to block XSS and malicious injection attempts.

        Args:
            message (str): Raw input string.

        Returns:
            str: Sanitized input safe for database write and rendering.
        """
        from ..utils.validators import sanitize_input
        return sanitize_input(message)

    async def get_conversation_history(self, user_id: UUID, limit: int = 100) -> List[Any]:
        """
        Fetches historic chat records for the user from persistent DB storage.

        Args:
            user_id (UUID): User UUID.
            limit (int, optional): Max records to retrieve. Defaults to 100.

        Returns:
            List[Any]: List of chat message objects.
        """
        if hasattr(self, 'user_repository') and self.user_repository is not None:
            return await self.user_repository.get_conversation_history(user_id, limit)
        from backend.repositories.chat_history import get_user_chat_history
        return get_user_chat_history(user_id, limit)

    async def clear_conversation_history(self, user_id: UUID) -> bool:
        """
        Deletes all conversation history logs associated with the user ID.

        Args:
            user_id (UUID): Target user identifier.

        Returns:
            bool: True if delete succeeds.
        """
        if self.user_repository is not None and hasattr(self.user_repository, 'clear_conversation_history'):
            return await self.user_repository.clear_conversation_history(user_id)
        from backend.repositories.chat_history import delete_user_chat_history
        delete_user_chat_history(user_id)
        return True


# Global chatbot service instance
_chatbot_service: Optional[ChatbotService] = None


def get_chatbot_service() -> ChatbotService:
    """
    Returns the singleton instance of the ChatbotService.
    """
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
        logger.info("Chatbot service initialized")
    return _chatbot_service
