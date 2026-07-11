"""
Chat History Repository - Specific implementation with fallback storage

Demonstrates how to extend FallbackRepository for continuous operation
even when database is unavailable.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from backend.repositories.base_repository import FallbackRepository
from backend.database.models import ChatHistory, ChatHistoryCreate
from backend.database.connection import (
    save_chat_fallback,
    get_chat_history_fallback,
    clear_chat_history_fallback
)


class ChatHistoryRepository(FallbackRepository[ChatHistory]):
    """
    Repository for chat history operations with fallback capability.

    Inherits fallback capabilities from FallbackRepository and adds
    domain-specific methods for chat history management.
    """

    def __init__(self):
        """Initialize the chat history repository."""
        super().__init__('chat_history', ChatHistory)

    def _save_to_fallback(self, entity_data: Dict[str, Any]) -> None:
        """
        Save chat message to in-memory fallback storage.

        Args:
            entity_data: Chat message data to save
        """
        save_chat_fallback(
            str(entity_data.get('user_id')),
            entity_data.get('user_message', ''),
            entity_data.get('bot_response', ''),
            entity_data.get('intent')
        )

    def _get_from_fallback(self, **identifiers) -> Optional[Dict[str, Any]]:
        """
        Get chat message from fallback storage.

        Args:
            **identifiers: Identifiers (user_id, message_id, etc.)

        Returns:
            Chat message data or None if not found
        """
        # Fallback storage doesn't support individual message retrieval
        # Return None to indicate not found in fallback
        return None

    def _get_all_from_fallback(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all chat messages from fallback storage.

        Args:
            limit: Maximum messages to return

        Returns:
            List of chat message data
        """
        if 'user_id' not in identifiers:
            return []

        user_id = str(identifiers.get('user_id'))
        fallback_history = get_chat_history_fallback(user_id, limit)

        # Convert fallback format to expected format
        result = []
        for item in fallback_history:
            result.append({
                'user_id': identifiers.get('user_id'),
                'user_message': item.get('user_message', ''),
                'bot_response': item.get('bot_response', ''),
                'intent': item.get('intent'),
                'created_at': datetime.fromisoformat(item.get('timestamp', datetime.now().isoformat()))
            })

        return result

    def _delete_from_fallback(self, **identifiers) -> bool:
        """
        Delete chat messages from fallback storage.

        Args:
            **identifiers: Identifiers (user_id, etc.)

        Returns:
            True if deleted successfully
        """
        if 'user_id' in identifiers:
            user_id = str(identifiers.get('user_id'))
            deleted_count = clear_chat_history_fallback(user_id)
            return deleted_count > 0
        return False

    def get_user_history(self, user_id: UUID, limit: int = 100) -> List[ChatHistory]:
        """
        Get chat history for a specific user.

        Args:
            user_id: User ID to get history for
            limit: Maximum messages to return

        Returns:
            List of chat history entries
        """
        # Store user_id for fallback access
        self.identifiers = {'user_id': user_id}

        if not self._is_client_available():
            self.logger.warning(f"Database unavailable - using fallback chat history for user {user_id}")
            return self.find_all(limit=limit)

        try:
            client = self._get_client()
            response = client.table(self.table_name).select('*')\
                .eq('user_id', str(user_id))\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()

            return [ChatHistory(**item) for item in response.data]

        except Exception as e:
            self._handle_error(e, f"fetching chat history for user {user_id}")
            # Fallback to in-memory storage
            return self.find_all(limit=limit)

    def create_message(self, chat_create: ChatHistoryCreate) -> Optional[ChatHistory]:
        """
        Create a new chat message.

        Args:
            chat_create: Chat message creation data

        Returns:
            Created chat history or None if failed
        """
        # Convert Pydantic model to dictionary
        chat_data = {
            'user_id': str(chat_create.user_id),
            'user_message': chat_create.user_message,
            'bot_response': chat_create.bot_response,
            'intent': chat_create.intent,
            'entities': chat_create.entities
        }

        result = self.create(chat_data)

        # If database save failed, fallback will be handled by create()
        if not result:
            # Return a pseudo ChatHistory for compatibility
            return ChatHistory(
                id=None,
                user_id=chat_create.user_id,
                user_message=chat_create.user_message,
                bot_response=chat_create.bot_response,
                intent=chat_create.intent,
                entities=chat_create.entities,
                created_at=datetime.now()
            )

        return result

    def delete_user_history(self, user_id: UUID) -> int:
        """
        Delete all chat history for a specific user.

        Args:
            user_id: User ID to delete history for

        Returns:
            Number of messages deleted
        """
        # Store user_id for fallback access
        self.identifiers = {'user_id': user_id}

        if not self._is_client_available():
            self.logger.warning(f"Database unavailable - clearing fallback history for user {user_id}")
            return clear_chat_history_fallback(str(user_id))

        try:
            client = self._get_client()
            response = client.table(self.table_name).delete()\
                .eq('user_id', str(user_id))\
                .execute()

            deleted_count = len(response.data)
            self.logger.info(f"Deleted {deleted_count} chat messages for user {user_id}")
            return deleted_count

        except Exception as e:
            self._handle_error(e, f"deleting chat history for user {user_id}")
            # Fallback to clearing in-memory history
            return clear_chat_history_fallback(str(user_id))

    def get_conversation_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get statistics about user's conversations.

        Args:
            user_id: User ID to get stats for

        Returns:
            Dictionary with conversation statistics
        """
        if not self._is_client_available():
            return {
                'total_messages': 0,
                'total_intents': 0,
                'most_common_intent': None
            }

        try:
            client = self._get_client()
            response = client.table(self.table_name).select('intent')\
                .eq('user_id', str(user_id))\
                .execute()

            messages = response.data
            intent_counts = {}

            for msg in messages:
                intent = msg.get('intent')
                if intent:
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1

            most_common = max(intent_counts.items(), key=lambda x: x[1]) if intent_counts else (None, 0)

            return {
                'total_messages': len(messages),
                'total_intents': len(intent_counts),
                'most_common_intent': most_common[0]
            }

        except Exception as e:
            self._handle_error(e, f"getting conversation stats for user {user_id}")
            return {
                'total_messages': 0,
                'total_intents': 0,
                'most_common_intent': None
            }


# Singleton instance for application-wide use
chat_history_repository = ChatHistoryRepository()