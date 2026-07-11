"""
Hybrid Chatbot - Rasa + LLM integration.

This module implements the hybrid orchestrator that intelligently routes requests:
- Specific security actions (phishing, CVE, password) → Rasa
- General queries and conversation → LLM with RAG and conversation memory
"""

import logging
from typing import Dict, Optional, List
from uuid import UUID, uuid4
import httpx

from llm.gemini_service import get_gemini_service_singleton
from llm.conversation_memory import get_conversation_memory
from rag.retriever import get_retriever
from database.crud.chat_history import create_chat_message
from database.models import ChatHistoryCreate
from config import settings

logger = logging.getLogger(__name__)


class HybridChatbot:
    """
    Hybrid chatbot combining Rasa for specific actions and LLM for conversation.

    Routing logic:
    1. Classify intent using Rasa
    2. If specific action intent (phishing, CVE, password) → Rasa
    3. If general query or low confidence → LLM with RAG + memory
    """

    # Intents that should be handled by Rasa (specific security tools)
    RASA_INTENTS = {
        'check_phishing',
        'check_password',
        'lookup_cve',
        'get_security_news',
        'greet',
        'goodbye',
        'thanks'
    }

    def __init__(self):
        """Initialize hybrid chatbot with all required components."""
        try:
            # Initialize LLM service
            self.llm_service = get_gemini_service_singleton()
            logger.info("✅ LLM service initialized")

            # Initialize conversation memory
            self.conversation_memory = get_conversation_memory()
            logger.info("✅ Conversation memory initialized")

            # RAG retriever (lazy load on first use)
            self.retriever = None

            # Rasa integration (reuse existing Rasa chatbot for classification)
            self.rasa_url = f"http://{settings.rasa_server_host}:{settings.rasa_server_port}"
            logger.info(f"✅ Hybrid chatbot initialized (Rasa at {self.rasa_url})")

        except Exception as e:
            logger.error(f"❌ Failed to initialize hybrid chatbot: {e}")
            raise

    def _init_rag(self):
        """Lazy initialize RAG retriever."""
        if self.retriever is None:
            try:
                self.retriever = get_retriever()
                logger.info("✅ RAG retriever initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize RAG: {e}")
                self.retriever = False  # Mark as failed but don't crash

    async def get_response(self, message: str, user_id: Optional[UUID] = None) -> Dict:
        """
        Main entry point - route message to appropriate service.

        Args:
            message: User's message
            user_id: Optional user UUID for personalization

        Returns:
            Dict with response, intent, confidence, and metadata
        """
        try:
            # Step 1: Quick Rasa classification
            rasa_classification = await self._classify_with_rasa(message, user_id)
            intent = rasa_classification.get('intent', 'unknown')
            confidence = rasa_classification.get('confidence', 0.0)

            logger.info(f"Rasa classification: intent={intent}, confidence={confidence}")

            # Step 2: Route based on intent
            if intent in self.RASA_INTENTS and confidence > 0.7:
                # Rasa handles specific actions
                logger.info(f"📡 Routing to RASA for intent: {intent}")
                return await self._handle_with_rasa(message, user_id, rasa_classification)
            else:
                # LLM handles general queries
                logger.info(f"🧠 Routing to LLM for general conversation")
                return await self._handle_with_llm(message, user_id)

        except Exception as e:
            logger.error(f"❌ Error in hybrid chatbot: {e}")
            return self._get_error_response(message, str(e))

    async def _classify_with_rasa(self, message: str, user_id: Optional[UUID]) -> Dict:
        """
        Quick Rasa call for intent classification only.

        Uses /model/parse endpoint which returns intent + entities
        without triggering actions (unlike /webhooks/rest/webhook).
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Use /model/parse for intent classification (NOT webhook)
                # /model/parse returns: {"intent": {"name": "...", "confidence": 0.xx}, "entities": [...]}
                # /webhooks/rest/webhook only returns: [{"text": "...", "recipient_id": "..."}]
                response = await client.post(
                    f"{self.rasa_url}/model/parse",
                    json={"text": message}
                )

                if response.status_code == 200:
                    data = response.json()
                    intent_data = data.get('intent', {})
                    return {
                        'intent': intent_data.get('name', 'unknown'),
                        'confidence': intent_data.get('confidence', 0.0),
                        'entities': data.get('entities', [])
                    }

        except Exception as e:
            logger.warning(f"Rasa classification failed: {e}")

        # Return unknown classification on failure
        return {'intent': 'unknown', 'confidence': 0.0, 'entities': []}

    async def _handle_with_rasa(
        self,
        message: str,
        user_id: Optional[UUID],
        classification: Dict
    ) -> Dict:
        """
        Let Rasa handle the full response for specific actions.

        After classification via /model/parse, sends message to /webhooks/rest/webhook
        to trigger Rasa custom actions (phishing check, CVE lookup, etc.)
        """
        try:
            intent = classification.get('intent', 'unknown')
            confidence = classification.get('confidence', 0.5)

            # Send to Rasa webhook to trigger actual actions
            response_text = "Xin lỗi, tôi không hiểu."
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.rasa_url}/webhooks/rest/webhook",
                    json={
                        "sender": str(user_id) if user_id else str(uuid4()),
                        "message": message
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        # Rasa may return multiple messages, join them
                        response_parts = [item.get('text', '') for item in data if item.get('text')]
                        if response_parts:
                            response_text = "\n\n".join(response_parts)
                elif response.status_code == 502:
                    # Rasa service may be temporarily unavailable
                    response_text = "Dịch vụ Rasa đang tạm thời không khả dụng. Xin vui lòng thử lại sau hoặc sử dụng tính năng tự động của LLM."
                    logger.warning("Rasa returned 502 Bad Gateway, showing fallback message")
                elif response.status_code == 404:
                    # Rasa endpoint not found
                    response_text = "Rasa không được cấu hình đúng. Xin vui lòng liên hệ quản trị viên."
                    logger.error("Rasa endpoint not found")
                elif response.status_code >= 500:
                    # Server error
                    response_text = "Rasa đang gặp sự cố. Xin vui lòng thử lại sau."
                    logger.error(f"Rasa server error: {response.status_code}")

            # Save to database if user provided
            if user_id:
                try:
                    chat_record = ChatHistoryCreate(
                        user_id=user_id,
                        user_message=message,
                        bot_response=response_text,
                        intent=intent,
                        entities=None
                    )
                    create_chat_message(chat_record)
                    logger.info(f"💾 Saved Rasa response for user {user_id}")
                except Exception as db_error:
                    logger.error(f"Failed to save Rasa response: {db_error}")

            return {
                'response': response_text,
                'intent': intent,
                'confidence': confidence,
                'source': 'rasa',
                'suggested_actions': self._get_suggested_actions(intent)
            }

        except httpx.TimeoutException:
            logger.error("Rasa request timed out")
            return await self._handle_with_llm(message, user_id)
        except httpx.ConnectError:
            logger.error("Cannot connect to Rasa server")
            return await self._handle_with_llm(message, user_id)
        except Exception as e:
            logger.error(f"Error handling with Rasa: {e}")
            # Fallback to LLM if Rasa fails
            logger.info("Rasa failed, falling back to LLM")
            return await self._handle_with_llm(message, user_id)

    def _get_suggested_actions(self, intent: str) -> list:
        """Get suggested follow-up actions based on detected intent."""
        suggestions = {
            'check_phishing': ["Kiểm tra URL khác", "Mẹo phòng chống phishing"],
            'check_password': ["Kiểm tra mật khẩu khác", "Mẹo tạo mật khẩu mạnh"],
            'lookup_cve': ["Tra cứu CVE khác", "Xem tin tức bảo mật"],
            'get_security_news': ["Tra cứu CVE", "Kiểm tra URL"],
            'greet': ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE"],
            'goodbye': [],
            'thanks': ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE"],
        }
        return suggestions.get(intent, ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE"])

    async def _handle_with_llm(self, message: str, user_id: Optional[UUID]) -> Dict:
        """
        Handle with LLM for intelligent conversation.

        Integrates:
        - RAG context for domain knowledge
        - Conversation history for multi-turn context
        - System prompt for security assistant behavior
        """
        try:
            # Initialize RAG if needed
            self._init_rag()

            # Step 1: Retrieve RAG context
            rag_context = ""
            retrieved_docs = []
            if self.retriever:
                try:
                    retrieved_docs = self.retriever.retrieve(message, n_results=3)
                    if retrieved_docs:
                        rag_context = self.retriever.format_context(retrieved_docs, max_length=1500)
                        logger.info(f"🔍 Retrieved {len(retrieved_docs)} RAG documents")
                except Exception as rag_error:
                    logger.warning(f"RAG retrieval failed: {rag_error}")

            # Step 2: Load conversation history
            history = []
            if user_id:
                history = self.conversation_memory.load_history(user_id)

            # Step 3: Build system prompt for security assistant
            system_prompt = self._get_system_prompt()

            # Step 4: Generate LLM response
            logger.info(f"🧠 Generating LLM response with {len(history)} history messages")
            llm_response = self.llm_service.generate_response(
                message=message,
                context=rag_context if rag_context else None,
                history=history if history else None,
                system_prompt=system_prompt
            )

            # Step 5: Save to database
            if user_id:
                try:
                    chat_record = ChatHistoryCreate(
                        user_id=user_id,
                        user_message=message,
                        bot_response=llm_response,
                        intent='llm_response',
                        entities=None
                    )
                    create_chat_message(chat_record)
                    logger.info(f"💾 Saved LLM response for user {user_id}")
                except Exception as db_error:
                    logger.error(f"Failed to save LLM response: {db_error}")

            return {
                'response': llm_response,
                'intent': 'llm_response',
                'confidence': 0.9,
                'source': 'llm',
                'suggested_actions': ["Kiểm tra URL", "Đánh giá mật khẩu", "Tra cứu CVE"],
                'rag_enabled': bool(rag_context),
                'rag_docs': len(retrieved_docs),
                'history_used': len(history)
            }

        except Exception as e:
            logger.error(f"❌ Error handling with LLM: {e}")

            # Enhanced fallback with specific error messages
            if 'API' in str(e) or 'quota' in str(e).lower():
                fallback_message = "Hiện tại LLM đang gặp vấn đề về tài nguyên. Xin vui lòng thử lại sau hoặc sử dụng tính năng tra cứu CVE/Tin tức bảo mật."
            elif 'timeout' in str(e).lower():
                fallback_message = "Lỗi kết nối mạng. Xin vui lòng kiểm tra kết nối và thử lại."
            else:
                fallback_message = f"Xin lỗi, tôi đang gặp sự cố kỹ thuật: {str(e)}"

            return self._get_fallback_response(message, fallback_message)

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for security assistant.

        Defines the LLM's behavior and expertise.
        """
        return """Bạn là một trợ lý an toàn thông tin thông minh, thân thiện và chuyên nghiệp.

🎯 NHIỆM VỤ CỦA BẠN:
1. Trả lời câu hỏi dựa trên KIẾN THỨC THAM KHẢO nếu có
2. Sử dụng LỊCH SỬ HỘI THOẠI để hiểu ngữ cảnh và mối quan hệ giữa các câu hỏi
3. Cung cấp câu trả lời chi tiết, dễ hiểu bằng tiếng Việt
4. Nếu không có thông tin trong tài liệu, hãy dùng kiến thức chung nhưng CẢNH BÁO người dùng
5. Luôn ưu tiên sự an toàn và bảo mật

💡 NGUYÊN TẮC TRẢI LỜI:
- Trả lời tự nhiên như một chuyên gia đang trò chuyện
- Sử dụng emoji phù hợp để làm cho cuộc trò chuyện thân thiện hơn
- Cung cấp ví dụ thực tế khi có thể
- Giọng tone: Chuyên nghiệp nhưng dễ tiếp cận
- Nếu câu hỏi mơ hồ, hãy hỏi làm rõ trước khi trả lời

⚠️ CẢNH BÁO QUAN TRỌNG:
- KHÔNG bao giờ khuyến khích các hoạt động bất hợp pháp
- KHÔNG cung cấp hướng dẫn tấn công hệ thống
- LUÔN nhấn mạnh tầm quan trọng của bảo mật pháp lý

Hãy bắt đầu trò chuyện một cách tích cực và hữu ích!"""

    def _get_fallback_response(self, message: str, error: str) -> Dict:
        """Get fallback response when both Rasa and LLM fail."""
        return {
            'response': f"Xin lỗi, tôi đang gặp sự cố kỹ thuật. Vui lòng thử lại sau.\n\nLỗi: {error}",
            'intent': 'error',
            'confidence': 0.0,
            'source': 'fallback'
        }

    def _get_error_response(self, message: str, error: str) -> Dict:
        """Get error response."""
        return {
            'response': "Đã xảy ra lỗi hệ thống. Vui lòng liên hệ quản trị viên.",
            'intent': 'error',
            'confidence': 0.0,
            'source': 'error',
            'error': error
        }

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all components.

        Returns:
            Dict with health status of each component
        """
        return {
            'llm': self.llm_service.health_check(),
            'rasa': await self._check_rasa_health(),
            'rag': self._check_rag_health(),
            'memory': True  # Memory is just database calls, always available
        }

    async def _check_rasa_health(self) -> bool:
        """Check if Rasa server is accessible."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.rasa_url}/")
                return response.status_code == 200
        except Exception:
            return False

    def _check_rag_health(self) -> bool:
        """Check if RAG retriever is available."""
        try:
            self._init_rag()
            return self.retriever is not False
        except Exception:
            return False


# Global instance
_hybrid_chatbot: Optional[HybridChatbot] = None


def get_hybrid_chatbot() -> HybridChatbot:
    """
    Get or create global hybrid chatbot instance.

    Returns:
        HybridChatbot: Global hybrid chatbot instance
    """
    global _hybrid_chatbot
    if _hybrid_chatbot is None:
        logger.info("Initializing global hybrid chatbot...")
        _hybrid_chatbot = HybridChatbot()
    return _hybrid_chatbot
