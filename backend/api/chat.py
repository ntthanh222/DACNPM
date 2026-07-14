from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
from backend.repositories.chat_history import (
    get_chat_message,
    get_user_chat_history,
    create_chat_message,
    delete_chat_message,
    delete_user_chat_history
)
from backend.database.models import ChatHistory, ChatHistoryCreate
from backend.api.deps import get_current_user_id, get_optional_user_id, require_current_user_id

router = APIRouter()

@router.post("/", response_model=ChatHistory, status_code=201)
async def create_chat(
    chat: ChatHistoryCreate,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Create a new chat message - users can only create messages for themselves"""
    if chat.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only create chat messages for yourself.")
    return create_chat_message(chat)

# Fixed route ordering: specific routes before parameterized routes (Bugs 4 & 5)
@router.get("/user/{user_id}", response_model=List[ChatHistory])
async def read_user_chat_history(
    user_id: UUID,
    limit: int = 100,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Get all chat history for a user - users can only access their own history"""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only view your own chat history.")
    return get_user_chat_history(user_id, limit)

@router.get("/{message_id}", response_model=ChatHistory)
async def read_chat_message(
    message_id: UUID,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Get a chat message by ID - users can only access their own messages"""
    message = get_chat_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Chat message not found")
    if message.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only view your own chat messages.")
    return message

@router.delete("/user/{user_id}")
async def delete_all_user_chats(
    user_id: UUID,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Delete all chat history for a user - users can only delete their own history"""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only delete your own chat history.")
    count = delete_user_chat_history(user_id)
    return {"message": f"Deleted {count} chat messages"}

@router.delete("/{message_id}")
async def delete_chat(
    message_id: UUID,
    current_user_id: UUID = Depends(require_current_user_id)
):
    """Delete a chat message - users can only delete their own messages"""
    message = get_chat_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Chat message not found")
    if message.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied. You can only delete your own chat messages.")
    success = delete_chat_message(message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat message not found")
    return {"message": "Chat message deleted successfully"}
