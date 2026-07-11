"""
Conversation memory management for LLM context.

This module handles loading and formatting conversation history from the database
to provide context for LLM responses, enabling multi-turn conversations.
"""

import logging
from typing import List, Dict, Optional
from uuid import UUID
from database.crud.chat_history import get_user_chat_history
from config import settings

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation history for LLM context.

    Loads chat history from database and formats it for LLM consumption,
    ensuring the chatbot can understand and maintain context across
    multiple turns of conversation.
    """

    def __init__(self, memory_window: Optional[int] = None):
        """
        Initialize conversation memory manager.

        Args:
            memory_window: Number of recent messages to include (default from config)
        """
        self.memory_window = memory_window or settings.llm_memory_window
        logger.info(f"ConversationMemory initialized with window: {self.memory_window}")

    def load_history(self, user_id: UUID, limit: Optional[int] = None) -> List[Dict]:
        """
        Load conversation history from database.

        Args:
            user_id: User UUID to load history for
            limit: Override default memory window

        Returns:
            List of message dicts with 'role' and 'content' keys
            Format: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
        """
        try:
            limit = limit or self.memory_window
            history = get_user_chat_history(user_id, limit=limit)

            if not history:
                logger.info(f"No conversation history found for user {user_id}")
                return []

            # Format database records to LLM conversation format
            # Database returns newest first, so we reverse for chronological order
            formatted = []
            for item in reversed(history):
                # Add user message
                if item.user_message:
                    formatted.append({
                        'role': 'user',
                        'content': item.user_message
                    })

                # Add assistant response
                if item.bot_response:
                    formatted.append({
                        'role': 'assistant',
                        'content': item.bot_response
                    })

            logger.info(f"✅ Loaded {len(formatted)} messages for user {user_id}")
            return formatted

        except Exception as e:
            logger.error(f"❌ Error loading conversation history: {e}")
            return []

    def format_history(self, history: List[Dict]) -> str:
        """
        Format conversation history as readable text.

        Args:
            history: List of message dicts

        Returns:
            str: Formatted conversation history
        """
        if not history:
            return "Không có lịch sử hội thoại."

        parts = []
        for item in history:
            role = "👤 Người dùng" if item['role'] == 'user' else "🤖 Trợ lý"
            parts.append(f"{role}: {item['content']}")

        return "\n".join(parts)

    def format_history_for_llm(self, history: List[Dict]) -> List[Dict]:
        """
        Format history for direct LLM API consumption.

        Some LLM APIs accept conversation history directly as a list of messages.
        This method ensures the format is correct for such APIs.

        Args:
            history: List of message dicts

        Returns:
            List of message dicts in standard format
        """
        return [
            {'role': msg['role'], 'content': msg['content']}
            for msg in history
        ]

    def get_context_window(self, user_id: UUID) -> Dict[str, any]:
        """
        Get complete context window for a user.

        Args:
            user_id: User UUID

        Returns:
            Dict with history, count, and metadata
        """
        history = self.load_history(user_id)

        return {
            'history': history,
            'count': len(history),
            'window_size': self.memory_window,
            'has_context': len(history) > 0
        }

    def trim_history(self, history: List[Dict], max_messages: int = None) -> List[Dict]:
        """
        Trim history to maximum number of messages.

        Args:
            history: Original history list
            max_messages: Maximum messages to keep (default: memory window)

        Returns:
            Trimmed history list
        """
        if not max_messages:
            max_messages = self.memory_window

        if len(history) <= max_messages:
            return history

        # Keep the most recent messages
        trimmed = history[-max_messages:]
        logger.info(f"Trimmed history from {len(history)} to {len(trimmed)} messages")
        return trimmed


# Global instance
_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    """
    Get or create global conversation memory instance.

    Returns:
        ConversationMemory: Global conversation memory manager
    """
    global _conversation_memory
    if _conversation_memory is None:
        logger.info("Initializing global conversation memory...")
        _conversation_memory = ConversationMemory()
    return _conversation_memory
