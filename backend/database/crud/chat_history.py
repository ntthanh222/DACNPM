"""
CRUD operations for chat history with graceful fallback.

This module provides database operations with automatic fallback to in-memory
storage when database is unavailable, ensuring continuous operation.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from database.connection import supabase, supabase_admin, is_database_available, save_chat_fallback, get_chat_history_fallback
from database.models import ChatHistory, ChatHistoryCreate
import logging

logger = logging.getLogger(__name__)


def get_chat_message(message_id: UUID) -> Optional[ChatHistory]:
    """Get a chat message by ID"""
    if not is_database_available():
        logger.warning("Database unavailable - cannot retrieve specific message by ID")
        return None

    try:
        # Use supabase_admin to bypass RLS restrictions
        client = supabase_admin if supabase_admin else supabase
        response = client.table('chat_history').select('*').eq('id', str(message_id)).execute()
        if response.data:
            return ChatHistory(**response.data[0])
        return None
    except Exception as e:
        logger.error(f"Error fetching chat message {message_id}: {e}")
        return None


def get_user_chat_history(user_id: UUID, limit: int = 100) -> List[ChatHistory]:
    """Get all chat history for a user"""
    if not is_database_available():
        logger.warning("Database unavailable - using in-memory fallback")
        fallback_history = get_chat_history_fallback(str(user_id), limit)
        # Convert fallback format to ChatHistory objects
        result = []
        for item in fallback_history:
            result.append(ChatHistory(
                id=None,  # No ID in memory mode
                user_id=user_id,
                user_message=item['user_message'],
                bot_response=item['bot_response'],
                intent=item.get('intent'),
                entities=None,
                created_at=datetime.fromisoformat(item['timestamp'])
            ))
        return result

    try:
        # Use supabase_admin to bypass RLS restrictions
        client = supabase_admin if supabase_admin else supabase
        response = client.table('chat_history').select('*').eq('user_id', str(user_id))\
            .order('created_at', desc=True).limit(limit).execute()
        return [ChatHistory(**item) for item in response.data]
    except Exception as e:
        logger.error(f"Error fetching chat history for user {user_id}: {e}")
        logger.warning("Falling back to in-memory history")
        return []


def create_chat_message(chat: ChatHistoryCreate) -> Optional[ChatHistory]:
    """Create a new chat message"""
    if not is_database_available():
        logger.warning("Database unavailable - saving to memory")
        save_chat_fallback(
            str(chat.user_id),
            chat.user_message,
            chat.bot_response,
            chat.intent
        )
        # Return a pseudo ChatHistory object for compatibility
        return ChatHistory(
            id=None,
            user_id=chat.user_id,
            user_message=chat.user_message,
            bot_response=chat.bot_response,
            intent=chat.intent,
            entities=chat.entities,
            created_at=datetime.now()
        )

    try:
        # Use supabase_admin to bypass RLS restrictions
        client = supabase_admin if supabase_admin else supabase
        response = client.table('chat_history').insert({
            'user_id': str(chat.user_id),
            'user_message': chat.user_message,
            'bot_response': chat.bot_response,
            'intent': chat.intent,
            'entities': chat.entities
        }).execute()
        if response.data:
            return ChatHistory(**response.data[0])
        raise Exception("No data returned from insert operation")
    except Exception as e:
        logger.error(f"Error creating chat message: {e}")
        logger.warning("Falling back to in-memory storage")
        save_chat_fallback(
            str(chat.user_id),
            chat.user_message,
            chat.bot_response,
            chat.intent
        )
        return ChatHistory(
            id=None,
            user_id=chat.user_id,
            user_message=chat.user_message,
            bot_response=chat.bot_response,
            intent=chat.intent,
            entities=chat.entities,
            created_at=datetime.now()
        )


def delete_chat_message(message_id: UUID) -> bool:
    """Delete a chat message"""
    if not is_database_available():
        logger.warning("Database unavailable - cannot delete specific message")
        return False

    try:
        # Use supabase_admin to bypass RLS restrictions
        client = supabase_admin if supabase_admin else supabase
        response = client.table('chat_history').delete().eq('id', str(message_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Error deleting chat message {message_id}: {e}")
        return False


def delete_user_chat_history(user_id: UUID) -> int:
    """Delete all chat history for a user"""
    if not is_database_available():
        logger.warning("Database unavailable - clearing in-memory history")
        from database.connection import clear_chat_history_fallback
        return clear_chat_history_fallback(str(user_id))

    try:
        # Use supabase_admin to bypass RLS restrictions
        client = supabase_admin if supabase_admin else supabase
        response = client.table('chat_history').delete().eq('user_id', str(user_id)).execute()
        return len(response.data)
    except Exception as e:
        logger.error(f"Error deleting chat history for user {user_id}: {e}")
        logger.warning("Falling back to clearing in-memory history")
        from database.connection import clear_chat_history_fallback
        return clear_chat_history_fallback(str(user_id))
