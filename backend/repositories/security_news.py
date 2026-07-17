from typing import Optional, List
from uuid import UUID
from datetime import datetime
from backend.database.connection import supabase_admin, is_database_available
from backend.database.models import SecurityNews, SecurityNewsCreate, SecurityNewsUpdate

# Force use of local PostgreSQL for development if available
try:
    from backend.database.local_connection import get_local_admin_client, is_local_available
    if is_local_available():
        supabase_admin = get_local_admin_client()
        print("🔄 Using local PostgreSQL connection for security_news CRUD...")
except ImportError:
    pass  # Use Supabase client as normal


def _is_missing_is_deleted_error(error: Exception) -> bool:
    message = str(error).lower()
    return "is_deleted" in message and ("does not exist" in message or "could not find" in message)


def _news_select_query():
    return supabase_admin.table('news_articles').select('*')


def get_news_item(news_id: UUID) -> Optional[SecurityNews]:
    """Get a news item by ID"""
    try:
        if not supabase_admin:
            return None
        response = supabase_admin.table('news_articles').select('*').eq('id', str(news_id)).execute()
        if response.data:
            return SecurityNews(**response.data[0])
        return None
    except Exception as e:
        print(f"Error fetching news item {news_id}: {e}")
        return None


def get_all_news(limit: int = 50, source: Optional[str] = None) -> List[SecurityNews]:
    """Get all security news, optionally filtered by source"""
    try:
        if not supabase_admin:
            return []
        try:
            query = _news_select_query().eq('is_deleted', False)

            if source:
                query = query.eq('source', source)

            response = query.not_.is_('published_at', 'null')\
                .order('published_at', desc=True).limit(limit).execute()
        except Exception as e:
            if not _is_missing_is_deleted_error(e):
                raise
            query = _news_select_query()
            if source:
                query = query.eq('source', source)
            response = query.not_.is_('published_at', 'null')\
                .order('published_at', desc=True).limit(limit).execute()
        return [SecurityNews(**item) for item in response.data]
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


def get_latest_news(limit: int = 10) -> List[SecurityNews]:
    """Get the latest security news"""
    try:
        if not supabase_admin:
            return []
        try:
            response = _news_select_query().eq('is_deleted', False)\
                .not_.is_('published_at', 'null')\
                .order('published_at', desc=True).limit(limit).execute()
        except Exception as e:
            if not _is_missing_is_deleted_error(e):
                raise
            response = _news_select_query().not_.is_('published_at', 'null')\
                .order('published_at', desc=True).limit(limit).execute()
        return [SecurityNews(**item) for item in response.data]
    except Exception as e:
        print(f"Error fetching latest news: {e}")
        return []


def create_news_item(news: SecurityNewsCreate) -> SecurityNews:
    """Create a new news item"""
    if not is_database_available():
        print("Database unavailable - cannot create news item")
        raise Exception("Database unavailable")
    try:
        if not supabase_admin:
            raise Exception("Database client unavailable")
        response = supabase_admin.table('news_articles').insert({
            'title': news.title,
            'url': news.url,
            'source': news.source,
            'description': news.description,
            'published_at': news.published_at
        }).execute()
        if response.data:
            return SecurityNews(**response.data[0])
        raise Exception("No data returned from insert operation")
    except Exception as e:
        print(f"Error creating news item: {e}")
        raise


def update_news_item(news_id: UUID, news_update: SecurityNewsUpdate) -> Optional[SecurityNews]:
    """Update a news item with proper validation"""
    if not is_database_available():
        print("Database unavailable - cannot update news item")
        return None
    try:
        if not supabase_admin:
            return None
        update_data = news_update.model_dump(exclude_unset=True)
        if update_data:
            response = supabase_admin.table('news_articles').update(update_data)\
                .eq('id', str(news_id)).execute()
            if response.data:
                return SecurityNews(**response.data[0])
        return None
    except Exception as e:
        print(f"Error updating news item {news_id}: {e}")
        return None


def delete_news_item(news_id: UUID) -> bool:
    """Delete a news item"""
    if not is_database_available():
        print("Database unavailable - cannot delete news item")
        return False
    try:
        if not supabase_admin:
            return False
        response = supabase_admin.table('news_articles').delete().eq('id', str(news_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting news item {news_id}: {e}")
        return False
