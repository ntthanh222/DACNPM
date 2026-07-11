from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import UUID
from backend.database.crud.security_news import (
    get_news_item,
    get_all_news,
    get_latest_news,
    create_news_item,
    update_news_item,
    delete_news_item
)
from backend.database.models import SecurityNews, SecurityNewsCreate, SecurityNewsUpdate
from backend.api.deps import get_current_user_id, get_optional_user_id, require_current_user_id, require_admin_or_analyst

router = APIRouter()

@router.post("/", response_model=SecurityNews, status_code=201)
def create_news(
    news: SecurityNewsCreate,
    current_user_id: UUID = Depends(require_admin_or_analyst)
):
    """Create a new news item - requires admin or analyst role"""
    return create_news_item(news)

@router.get("/", response_model=List[SecurityNews])
def read_news(limit: int = 50, source: Optional[str] = None):
    """Get security news, optionally filtered by source - public endpoint"""
    return get_all_news(limit, source)

@router.get("/latest", response_model=List[SecurityNews])
def read_latest_news(limit: int = 10):
    """Get the latest security news - public endpoint"""
    return get_latest_news(limit)

@router.get("/{news_id}", response_model=SecurityNews)
def read_news_item(news_id: UUID):
    """Get a news item by ID - public endpoint"""
    news = get_news_item(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News item not found")
    return news

@router.put("/{news_id}", response_model=SecurityNews)
def update_news(
    news_id: UUID,
    news_update: SecurityNewsUpdate,
    current_user_id: UUID = Depends(require_admin_or_analyst)
):
    """Update a news item - requires admin or analyst role"""
    news = update_news_item(news_id, news_update)
    if not news:
        raise HTTPException(status_code=404, detail="News item not found")
    return news

@router.delete("/{news_id}")
def delete_news(
    news_id: UUID,
    current_user_id: UUID = Depends(require_admin_or_analyst)
):
    """Delete a news item - requires admin or analyst role"""
    success = delete_news_item(news_id)
    if not success:
        raise HTTPException(status_code=404, detail="News item not found")
    return {"message": "News item deleted successfully"}
