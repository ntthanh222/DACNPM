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
from backend.repositories.chat_history import create_chat_message

logger = logging.getLogger(__name__)


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
        Queries the Rasa NLU server with the user's message, enhanced with RAG context.

        Args:
            message (str): The raw message.
            user_id (UUID): Authenticated user's unique identifier.

        Returns:
            Dict[str, Any]: Response dictionary with answer, intent details, and RAG metadata.
        """
        try:
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
