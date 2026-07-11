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
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from backend.services.rasa_client import get_rasa_client
from backend.services.rag_service import get_rag_service
from backend.database.models import ChatHistoryCreate
from backend.database.crud.chat_history import create_chat_message

logger = logging.getLogger(__name__)


class ChatbotService:
    """Service for chatbot business logic orchestration"""

    def __init__(self):
        self.rasa_client = get_rasa_client()
        self.rag_service = get_rag_service()
        self.user_repository = None

    async def process_message(
        self,
        message: str,
        user_id: Optional[UUID] = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
        """
        Process user message and generate response.

        Args:
            message: Sanitized user message
            user_id: User UUID (None for anonymous users)
            save_to_db: Whether to save chat to database

        Returns:
            Dictionary with response, intent, confidence, and metadata
        """
        if not user_id:
            logger.warning("No user_id provided, using anonymous mode")
            return await self._get_fallback_response(message, anonymous=True)

        # Try RAG-enhanced Rasa response first
        response_data = await self._get_rasa_response(message, user_id)

        if not save_to_db:
            return response_data

        try:
            chat_record = ChatHistoryCreate(
                user_id=user_id,
                user_message=message,
                bot_response=response_data['response'],
                intent=response_data.get('intent'),
                entities=None
            )
            create_chat_message(chat_record)
            logger.info(f"Saved chat message for user {user_id}")
        except Exception as db_error:
            logger.error(f"Failed to save chat to database: {db_error}")

        return response_data

    async def _get_rasa_response(self, message: str, user_id: UUID) -> Dict[str, Any]:
        """
        Get response from Rasa with RAG enhancement.

        Args:
            message: User message
            user_id: User identifier

        Returns:
            Response dictionary with all metadata
        """
        try:
            # Enhance message with RAG context if available
            enhanced_message, retrieved_docs = await self.rag_service.enhance_message(message)

            # Get response from Rasa
            rasa_response = await self.rasa_client.send_message(
                enhanced_message,
                str(user_id)
            )

            if not rasa_response:
                logger.warning("Rasa returned no response, using fallback")
                return await self._get_fallback_response(message, with_rag=True)

            return {
                'response': rasa_response,
                'intent': None,  # Rasa doesn't return intent in REST response
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
        Generate fallback response when Rasa is unavailable.

        Args:
            message: User message
            anonymous: Whether user is anonymous
            with_rag: Whether to try RAG enhancement

        Returns:
            Response dictionary with fallback content
        """
        # Try RAG-enhanced fallback first
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

        # Use pattern matching fallback
        return self._pattern_matching_fallback(message, anonymous)

    def _pattern_matching_fallback(self, message: str, anonymous: bool = False) -> Dict[str, Any]:
        """
        Pattern-based fallback response when Rasa and RAG are unavailable.

        Args:
            message: User message
            anonymous: Whether user is anonymous

        Returns:
            Response dictionary based on pattern matching
        """
        message_lower = message.lower()

        # Greeting patterns
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

        # URL/Phishing patterns
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

        # Password patterns
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

        # CVE patterns
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

        # Default fallback
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
        Get suggested actions based on message content.

        Args:
            message: User message to analyze

        Returns:
            List of suggested action labels
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
        """Validate user message"""
        if not message or not message.strip():
            return False
        if len(message) > 5000:
            return False
        return True

    def sanitize_message(self, message: str) -> str:
        """Sanitize user message to prevent XSS"""
        from ..utils.validators import sanitize_input
        return sanitize_input(message)

    async def get_conversation_history(self, user_id: UUID, limit: int = 100) -> List[Any]:
        """Get conversation history for a user"""
        if hasattr(self, 'user_repository') and self.user_repository is not None:
            return await self.user_repository.get_conversation_history(user_id, limit)
        from backend.database.crud.chat_history import get_user_chat_history
        return get_user_chat_history(user_id, limit)

    async def clear_conversation_history(self, user_id: UUID) -> bool:
        """Clear conversation history for a user"""
        if self.user_repository is not None and hasattr(self.user_repository, 'clear_conversation_history'):
            return await self.user_repository.clear_conversation_history(user_id)
        from backend.database.crud.chat_history import delete_user_chat_history
        delete_user_chat_history(user_id)
        return True


# Global chatbot service instance
_chatbot_service: Optional[ChatbotService] = None


def get_chatbot_service() -> ChatbotService:
    """Get global chatbot service instance (singleton pattern)"""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
        logger.info("Chatbot service initialized")
    return _chatbot_service
