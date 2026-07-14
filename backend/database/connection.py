"""
Database connection with graceful degradation.

This module provides database connectivity with automatic fallback
when database is unavailable, ensuring the chatbot continues to function.
"""

import logging
import os
import re
import time
import threading
from functools import wraps
try:
    from supabase import create_client
    from supabase.lib.client_options import SyncClientOptions
    SUPABASE_SDK_AVAILABLE = True
except (ImportError, RuntimeError) as exc:
    # Rasa SDK 3.6.2 is pinned to websockets<11, while newer Supabase
    # Realtime clients require websockets>=11. Keep action startup healthy
    # and use the existing in-memory/offline fallback when those runtimes
    # cannot coexist in the action image.
    create_client = None
    SyncClientOptions = None
    SUPABASE_SDK_AVAILABLE = False
    logging.getLogger(__name__).warning("Supabase SDK unavailable: %s", exc)
from backend.core.config import settings

# Configure logging at module level (before try/except block)
logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 not available - raw SQL migrations will not work")

def retry_on_connection_error(max_retries=3, delay=1):
    """Decorator to retry database operations on connection errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator

def _test_supabase_connection(client, test_tables=None):
    """Test Supabase connection by trying multiple tables in order."""
    if test_tables is None:
        test_tables = ['users', 'chat_history']
    last_error = None
    for table in test_tables:
        try:
            client.table(table).select('id').limit(1).execute()
            return True, table
        except Exception as e:
            last_error = e
            continue
    return False, last_error


def _create_supabase_client(supabase_url, supabase_key):
    """Create a client compatible with both legacy and modern Supabase keys."""
    if not SUPABASE_SDK_AVAILABLE:
        raise RuntimeError("Supabase SDK is unavailable in this runtime")

    if supabase_key.startswith(("sb_publishable_", "sb_secret_")):
        # Modern keys are valid only in the `apikey` header. supabase-py also
        # sets a Bearer header by default, so suppress it until a user JWT is set.
        options = SyncClientOptions()
        options.headers["Authorization"] = ""
        client = create_client(supabase_url, supabase_key, options)
        client.options.headers.pop("Authorization", None)
        client.auth._headers.pop("Authorization", None)
        return client

    return create_client(supabase_url, supabase_key)

def get_supabase_client():
    """Get Supabase client with public key for user operations"""
    try:
        if not SUPABASE_SDK_AVAILABLE:
            return None
        if not settings.supabase_url or not settings.supabase_key:
            logger.warning("Supabase credentials not configured")
            return None

        client = _create_supabase_client(settings.supabase_url, settings.supabase_key)

        # Return client directly without connection test to avoid flooding
        # Connection will be validated on first use
        logger.debug("✅ Supabase client initialized")
        return client

    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None

def get_supabase_admin_client():
    """
    Get Supabase client with service role for admin operations.

    SECURITY WARNING: This client bypasses Row Level Security (RLS).
    Only use this after verifying admin role via JWT in deps.py.
    The service role key must be set via environment variable only.
    """
    try:
        if not SUPABASE_SDK_AVAILABLE:
            return None
        # SECURITY: Service role key must come from environment variable
        service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or getattr(settings, 'supabase_service_role_key', None)
        if not service_role_key:
            logger.error("❌ SUPABASE_SERVICE_ROLE_KEY environment variable not set")
            return None

        if not settings.supabase_url:
            logger.warning("Supabase URL not configured")
            return None

        client = _create_supabase_client(settings.supabase_url, service_role_key)

        # Return client directly without connection test to avoid flooding
        # Connection will be validated on first use
        logger.debug("✅ Supabase admin client initialized (service role)")
        return client

    except Exception as e:
        logger.error(f"Failed to create Supabase admin client: {e}")
        return None

def get_raw_postgres_connection():
    """Get raw PostgreSQL connection for database migrations and admin operations"""
    if not PSYCOPG2_AVAILABLE:
        logger.error("psycopg2 not available - cannot create raw PostgreSQL connection")
        raise ImportError("psycopg2 is required for database migrations. Install it with: pip install psycopg2-binary")

    try:
        # Extract PostgreSQL host from Supabase URL
        # Format: https://[project_ref].supabase.co
        if not settings.supabase_url:
            raise ValueError("SUPABASE_URL not configured")

        # Parse the Supabase URL to get the project reference
        url_match = re.match(r'https?://([^.]+)\.supabase\.co', settings.supabase_url)
        if not url_match:
            raise ValueError(f"Invalid Supabase URL format: {settings.supabase_url}")

        project_ref = url_match.group(1)
        postgres_host = f"db.{project_ref}.supabase.co"

        # Use the database settings from config, or construct from Supabase URL
        db_host = getattr(settings, 'db_host', postgres_host)
        db_port = getattr(settings, 'db_port', 5432)
        db_name = getattr(settings, 'db_name', 'postgres')
        db_user = getattr(settings, 'db_user', 'postgres')
        db_password = getattr(settings, 'db_password', settings.supabase_service_role_key)

        if not db_password:
            raise ValueError("Database password not configured - set DB_PASSWORD or SUPABASE_SERVICE_ROLE_KEY")

        # Create the PostgreSQL connection
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )

        logger.info(f"Raw PostgreSQL connection established to {db_host}:{db_port}/{db_name}")
        return connection

    except Exception as e:
        logger.error(f"Failed to create raw PostgreSQL connection: {e}")
        raise

# Global connection status
DATABASE_AVAILABLE = False
_connection_recovery_attempts = 0
_max_recovery_attempts = 5

def is_database_available() -> bool:
    """Check if database is available for operations"""
    return DATABASE_AVAILABLE

def _attempt_connection_recovery():
    """Attempt to recover database connection"""
    global DATABASE_AVAILABLE, supabase, supabase_admin, _connection_recovery_attempts

    if _connection_recovery_attempts >= _max_recovery_attempts:
        logger.warning("❌ Maximum connection recovery attempts reached. Database may be permanently unavailable.")
        return False

    _connection_recovery_attempts += 1
    logger.info(f"🔄 Attempting database connection recovery ({_connection_recovery_attempts}/{_max_recovery_attempts})...")

    try:
        # Force re-initialize clients
        new_supabase = get_supabase_client()
        new_supabase_admin = get_supabase_admin_client()

        db_ok = False
        if new_supabase:
            ok, err = _test_supabase_connection(new_supabase)
            if ok:
                db_ok = True
        if not db_ok and new_supabase_admin:
            ok, err = _test_supabase_connection(new_supabase_admin)
            if ok:
                db_ok = True

        if db_ok:
            supabase = new_supabase
            supabase_admin = new_supabase_admin
            DATABASE_AVAILABLE = True
            _connection_recovery_attempts = 0
            logger.info("✅ Database connection recovered and verified successfully")
            return True
        else:
            logger.warning("⚠️ Connection recovery failed - connection test failed on new clients")
            return False

    except Exception as e:
        logger.error(f"❌ Connection recovery failed: {e}")
        return False

# Import local PostgreSQL support
try:
    from backend.database.local_connection import (
        get_local_client, get_local_admin_client, is_local_available,
        LocalPostgreSQLClient
    )
    LOCAL_PG_AVAILABLE = True
    logger.info("✅ Local PostgreSQL support available")
except ImportError as e:
    LOCAL_PG_AVAILABLE = False
    logger.warning(f"Local PostgreSQL support not available: {e}")

# Singleton instances with error handling and auto-recovery
try:
    logger.info("Initializing database connections...")

    supabase = get_supabase_client()
    supabase_admin = get_supabase_admin_client()

    # Check if at least basic connection works by performing a real query test
    db_ok = False
    if supabase:
        ok, err = _test_supabase_connection(supabase)
        if ok:
            db_ok = True
    if not db_ok and supabase_admin:
        ok, err = _test_supabase_connection(supabase_admin)
        if ok:
            db_ok = True

    if db_ok:
        DATABASE_AVAILABLE = True
        logger.info("✅ Database available and connection verified")
    else:
        # Try local PostgreSQL as fallback
        if LOCAL_PG_AVAILABLE and is_local_available():
            logger.info("🔄 Supabase not working, using local PostgreSQL...")
            supabase = get_local_client()
            supabase_admin = get_local_admin_client()
            DATABASE_AVAILABLE = True
            logger.info("✅ Local PostgreSQL connection established")
        else:
            logger.warning("❌ Database not available - running in offline mode")
            logger.warning("💡 Tip: Check your internet connection and Supabase credentials")

except Exception as e:
    logger.error(f"❌ Failed to initialize database connections: {e}")

    # Try local PostgreSQL as fallback
    try:
        if LOCAL_PG_AVAILABLE and is_local_available():
            logger.info("🔄 Trying local PostgreSQL fallback...")
            supabase = get_local_client()
            supabase_admin = get_local_admin_client()
            DATABASE_AVAILABLE = True
            logger.info("✅ Local PostgreSQL fallback successful")
        else:
            raise
    except:
        logger.warning("⚠️ Running in offline mode - chatbot will work without database persistence")
        # Create None clients
        supabase = None
        supabase_admin = None
        DATABASE_AVAILABLE = False

# In-memory fallback for chat history when database is unavailable
_in_memory_chat_history = {}

def save_chat_fallback(user_id: str, user_message: str, bot_response: str, intent: str = None):
    """
    Fallback function to save chat history in memory when database is unavailable.
    """
    if not DATABASE_AVAILABLE:
        import json
        from datetime import datetime

        if user_id not in _in_memory_chat_history:
            _in_memory_chat_history[user_id] = []

        _in_memory_chat_history[user_id].append({
            'timestamp': datetime.now().isoformat(),
            'user_message': user_message,
            'bot_response': bot_response,
            'intent': intent
        })

        logger.debug(f"💾 Saved chat to memory for user {user_id} (database unavailable)")

def get_chat_history_fallback(user_id: str, limit: int = 10):
    """
    Fallback function to get chat history from memory when database is unavailable.
    """
    if not DATABASE_AVAILABLE:
        if user_id in _in_memory_chat_history:
            history = _in_memory_chat_history[user_id][-limit:]
            logger.debug(f"📋 Retrieved {len(history)} messages from memory for user {user_id}")
            return history
        return []
    return None

def clear_chat_history_fallback(user_id: str):
    """
    Fallback function to clear chat history from memory.
    """
    if user_id in _in_memory_chat_history:
        count = len(_in_memory_chat_history[user_id])
        _in_memory_chat_history[user_id] = []
        logger.debug(f"🗑️ Cleared {count} messages from memory for user {user_id}")
        return count
    return 0

def _monitor_database_status():
    """Background thread to monitor database availability"""
    global DATABASE_AVAILABLE

    while True:
        time.sleep(30)  # Check every 30 seconds
        try:
            # If supabase is None or database unavailable, attempt recovery
            if not supabase or not DATABASE_AVAILABLE:
                if _attempt_connection_recovery():
                    if not DATABASE_AVAILABLE:
                        logger.info("✅ Database connection recovered")
                        DATABASE_AVAILABLE = True
                else:
                    # Recovery failed
                    if DATABASE_AVAILABLE:
                        logger.warning("⚠️ Database connection lost")
                        DATABASE_AVAILABLE = False
            else:
                # Test existing connection
                try:
                    if supabase.table('users').select('id').limit(1).execute():
                        if not DATABASE_AVAILABLE:
                            logger.info("✅ Database connection recovered")
                            DATABASE_AVAILABLE = True
                    else:
                        if DATABASE_AVAILABLE:
                            logger.warning("⚠️ Database connection lost")
                            DATABASE_AVAILABLE = False
                except Exception as test_error:
                    if DATABASE_AVAILABLE:
                        logger.warning(f"⚠️ Database connection test failed: {test_error}")
                        DATABASE_AVAILABLE = False
        except Exception as e:
            if DATABASE_AVAILABLE:
                logger.warning(f"⚠️ Database monitor error: {e}")
                DATABASE_AVAILABLE = False

# Always start monitor thread - it will detect recovery when database comes online
monitor_thread = threading.Thread(target=_monitor_database_status, daemon=True)
monitor_thread.start()
logger.info("🔄 Database monitor thread started")

logger.info(f"📊 Database Status: {'Available (Degraded)' if DATABASE_AVAILABLE else 'Offline'}")
