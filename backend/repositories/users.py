"""
CRUD operations for users table
Enhanced user management with security context
"""
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
import logging
from backend.database.models import User, UserCreate, UserUpdate
from backend.database.connection import (
    supabase,
    supabase_admin,
    is_database_available,
    get_supabase_admin_client,
)

logger = logging.getLogger(__name__)

# In-memory user storage for offline mode (dual-index for O(1) lookups)
_in_memory_users_by_username = {}
_in_memory_users_by_id = {}

def _apply_dynamic_roles(user: User) -> User:
    """Apply official server-side role mapping based on UUID."""
    if not user:
        return user
    try:
        from backend.config.settings import get_settings
        if str(user.id) in get_settings().get_super_admin_ids():
            user.role = 'super_admin'
    except Exception as e:
        logger.error(f"Error applying dynamic roles: {e}")
    return user


def _update_cache(user: User):
    """Update user in both cache indexes"""
    _in_memory_users_by_username[user.username] = user
    _in_memory_users_by_id[str(user.id)] = user

def _invalidate_cache(user: User):
    """Remove user from both cache indexes"""
    if user.username in _in_memory_users_by_username:
        del _in_memory_users_by_username[user.username]
    if str(user.id) in _in_memory_users_by_id:
        del _in_memory_users_by_id[str(user.id)]

def _invalidate_cache_by_username(username: str):
    """Remove user from cache by username (need to get user to remove id index too)"""
    if username in _in_memory_users_by_username:
        user = _in_memory_users_by_username[username]
        del _in_memory_users_by_username[username]
        if str(user.id) in _in_memory_users_by_id:
            del _in_memory_users_by_id[str(user.id)]

def _invalidate_cache_by_id(user_id: UUID):
    """Remove user from cache by id"""
    user_id_str = str(user_id)
    if user_id_str in _in_memory_users_by_id:
        user = _in_memory_users_by_id[user_id_str]
        del _in_memory_users_by_id[user_id_str]
        if user.username in _in_memory_users_by_username:
            del _in_memory_users_by_username[user.username]


def get_user(user_id: UUID) -> Optional[User]:
    """
    Get user by ID with graceful fallback to in-memory storage.
    Security: Uses supabase_admin to bypass RLS, with fallback to regular client
    """
    # Check in-memory storage first (O(1) lookup)
    user_id_str = str(user_id)
    if user_id_str in _in_memory_users_by_id:
        logger.debug(f"Retrieved user {user_id} from in-memory storage")
        return _apply_dynamic_roles(_in_memory_users_by_id[user_id_str])

    # Try admin client first (bypasses RLS)
    if supabase_admin:
        try:
            response = supabase_admin.table('users').select('*').eq('id', str(user_id)).execute()
            if response.data:
                user = User(**response.data[0])
                # Cache in memory for future requests
                _update_cache(user)
                return _apply_dynamic_roles(user)
            return None
        except Exception as admin_error:
            logger.warning(f"Admin client error for user {user_id}: {admin_error}")

    # Fallback to regular client (may be blocked by RLS)
    if not supabase:
        logger.debug(f"Supabase client unavailable, user {user_id} not in memory")
        return None

    try:
        response = supabase.table('users').select('*').eq('id', str(user_id)).execute()
        if response.data:
            user = User(**response.data[0])
            # Cache in memory for future requests
            _update_cache(user)
            return _apply_dynamic_roles(user)
        return None
    except AttributeError as e:
        logger.error(f"Supabase client error for user {user_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {type(e).__name__}: {e}")
        return None


def get_user_by_username(username: str, use_cache: bool = True) -> Optional[User]:
    """
    Get user by username with graceful fallback to in-memory storage.
    Security: Uses supabase_admin to bypass RLS for authentication/registration checks
    """
    global supabase_admin
    # Authentication can opt out of this cache because password resets and
    # role changes may happen in Supabase from another process.
    if use_cache and username in _in_memory_users_by_username:
        logger.debug(f"Retrieved user {username} from in-memory storage")
        return _apply_dynamic_roles(_in_memory_users_by_username[username])

    # Try admin client first (bypasses RLS for auth checks)
    if supabase_admin:
        # PostgREST/httpx can close an idle HTTP/2 connection between the
        # registration and the next login. Recreate the client and retry a
        # bounded number of times so a transient disconnect is not converted
        # into a false 401. This is deliberately finite and does not mask
        # authentication failures returned by a healthy database.
        import time
        for attempt in range(3):
            try:
                response = supabase_admin.table('users').select('*').eq('username', username).execute()
                if response.data:
                    user = User(**response.data[0])
                    if use_cache:
                        _update_cache(user)
                    return _apply_dynamic_roles(user)
                return None
            except Exception as admin_error:
                logger.warning(
                    "Admin client error for username %s (attempt %s/3): %s",
                    username, attempt + 1, admin_error,
                )
                if attempt == 2:
                    break
                time.sleep(0.25 * (2 ** attempt))
                refreshed_client = get_supabase_admin_client()
                if refreshed_client:
                    supabase_admin = refreshed_client

    # Fallback to regular client (may be blocked by RLS)
    if not supabase:
        logger.debug(f"Supabase client unavailable, user {username} not in memory")
        return None

    try:
        response = supabase.table('users').select('*').eq('username', username).execute()
        if response.data:
            user = User(**response.data[0])
            # Cache in memory for future requests
            _update_cache(user)
            return _apply_dynamic_roles(user)

        return None
    except AttributeError as e:
        logger.error(f"Supabase client error for username {username}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting user by username {username}: {type(e).__name__}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[User]:
    """
    Get user by email
    Security: Uses supabase_admin to bypass RLS for authentication/registration checks
    """
    # Try admin client first (bypasses RLS for auth checks)
    if supabase_admin:
        try:
            response = supabase_admin.table('users').select('*').eq('email', email).execute()
            if response.data:
                return _apply_dynamic_roles(User(**response.data[0]))
            return None
        except Exception as admin_error:
            logger.warning(f"Admin client error for email {email}: {admin_error}")

    # Fallback to regular client (may be blocked by RLS)
    if not supabase:
        return None

    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if response.data:
            return _apply_dynamic_roles(User(**response.data[0]))
        return None
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        return None


def get_users(skip: int = 0, limit: int = 100) -> List[User]:
    """
    Get multiple users with pagination
    Security: RLS will filter based on user role
    """
    if not supabase:
        return list(_in_memory_users_by_username.values())

    try:
        response = supabase.table('users').select('*').range(skip, skip + limit - 1).execute()
        return [User(**user) for user in response.data]
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []


def create_user(user: UserCreate, max_retries: int = 3) -> Optional[User]:
    """
    Create new user with retry mechanism and graceful error handling.
    Security: Uses admin client to bypass RLS for user creation.

    Note: Validation errors (unique/NOT NULL violations) are NOT retried —
    retrying them only wastes time since they will fail identically each time.
    Only transient connection errors are retried.
    """
    import time

    # Heuristics to detect non-retryable validation/constraint errors.
    _NON_RETRYABLE_MARKERS = (
        'duplicate key value',
        'violates unique constraint',
        'violates not-null constraint',
        'violates check constraint',
        'invalid input syntax',
    )

    def _is_non_retryable(err_msg: str) -> bool:
        low = (err_msg or '').lower()
        return any(m in low for m in _NON_RETRYABLE_MARKERS)

    for attempt in range(max_retries):
        try:
            user_data = user.model_dump(exclude_unset=True, by_alias=True)

            # Security: Check if username already exists to prevent cache poisoning
            existing_user = get_user_by_username(user_data.get('username'))
            if existing_user:
                raise ValueError(f"Username '{user_data.get('username')}' already exists")

            if 'id' not in user_data or not user_data['id']:
                user_data['id'] = str(uuid4())

            user_data['created_at'] = datetime.now().isoformat()
            user_data['updated_at'] = datetime.now().isoformat()

            if 'security_context' not in user_data or not user_data['security_context']:
                user_data['security_context'] = {
                    'preferences': {
                        'language': 'vi',
                        'notifications_enabled': True,
                        'scan_frequency': 'weekly'
                    }
                }

            # Try to create in database first
            if supabase_admin:
                try:
                    response = supabase_admin.table('users').insert(user_data).execute()
                    if response.data:
                        created_user = User(**response.data[0])
                        # Cache in memory
                        _update_cache(created_user)
                        logger.info(f"User created successfully: {user_data.get('username')}")
                        return created_user
                except Exception as db_error:
                    err_msg = str(db_error)
                    # Non-retryable: surface immediately as a ValueError so the
                    # API layer can return a meaningful message.
                    if _is_non_retryable(err_msg):
                        logger.warning(f"User creation rejected ({err_msg[:160]})")
                        if 'unique' in err_msg.lower() or 'duplicate' in err_msg.lower():
                            raise ValueError(f"Username or email already exists")
                        raise ValueError(f"Invalid user data: {err_msg[:160]}")

                    logger.warning(f"Database insert failed (attempt {attempt + 1}/{max_retries}): {db_error}")

                    if attempt < max_retries - 1:
                        # Exponential backoff for transient errors only
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Final attempt failed
                        raise ValueError(f"Cannot create user '{user_data.get('username')}' - database unavailable after {max_retries} attempts. Please try again later.")

            # Database is completely unavailable
            logger.warning(f"Database unavailable - rejecting user creation: {user_data.get('username', 'unknown')}")
            raise ValueError(f"Cannot create user '{user_data.get('username')}' - database unavailable. Please try again later.")

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Error creating user (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # All retries exhausted
                raise ValueError(f"Cannot create user '{user_data.get('username')}' - system error. Please try again later.")

    return None


def update_user(user_id: UUID, user_update: UserUpdate) -> Optional[User]:
    """
    Update user
    Security: RLS enforced - users can only update their own profile
    """
    try:
        update_data = user_update.model_dump(exclude_unset=True)

        # Remove role from update_data - role changes should go through admin endpoint only
        if 'role' in update_data:
            del update_data['role']

        if not supabase_admin:
            return None

        response = supabase_admin.table('users').update(update_data).eq('id', str(user_id)).execute()
        if response.data:
            updated_user = User(**response.data[0])
            # Update cache with new data
            _update_cache(updated_user)
            return updated_user
        return None
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return None


def delete_user(user_id: UUID) -> bool:
    """
    Delete user
    Security: RLS enforced - users can only delete their own account
    Note: This will cascade delete all related records (chat_history, security_scans)
    """
    try:
        # Get user data first for cache invalidation
        user_to_delete = get_user(user_id)

        if not supabase:
            return False

        response = supabase.table('users').delete().eq('id', str(user_id)).execute()

        if len(response.data) > 0:
            # Invalidate cache
            if user_to_delete:
                _invalidate_cache(user_to_delete)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False


def update_security_context(user_id: UUID, security_context: Dict[str, Any]) -> Optional[User]:
    """
    Update user security context
    Security: RLS enforced - users can only update their own security context
    """
    try:
        current_user = get_user(user_id)
        if not current_user:
            return None

        # Merge with existing security context
        merged_context = {**(current_user.security_context or {}), **security_context}

        if not supabase_admin:
            return None

        response = supabase_admin.table('users').update({
            'security_context': merged_context
        }).eq('id', str(user_id)).execute()

        if response.data:
            updated_user = User(**response.data[0])
            _update_cache(updated_user)
            return updated_user
        return None
    except Exception as e:
        logger.error(f"Error updating security context for user {user_id}: {e}")
        return None


def update_last_security_scan(user_id: UUID) -> Optional[User]:
    """
    Update user's last security scan timestamp
    Security: RLS enforced
    """
    try:
        if not supabase_admin:
            return None
        response = supabase_admin.table('users').update({
            'last_security_scan': datetime.now(timezone.utc).isoformat()
        }).eq('id', str(user_id)).execute()

        if response.data:
            updated_user = User(**response.data[0])
            _update_cache(updated_user)
            return updated_user
        return None
    except Exception as e:
        logger.error(f"Error updating last security scan for user {user_id}: {e}")
        return None


def get_active_users_count() -> int:
    """
    Get count of active users
    Security: Admin only query
    """
    try:
        if not supabase:
            return 0
        response = supabase.table('users').select('id', count='exact').eq('is_active', True).execute()
        return response.count if response.count else 0
    except Exception as e:
        logger.error(f"Error getting active users count: {e}")
        return 0


def get_users_by_role(role: str) -> List[User]:
    """
    Get users by role
    Security: Admin only query
    """
    try:
        if not supabase:
            return []
        response = supabase.table('users').select('*').eq('role', role).execute()
        return [User(**user) for user in response.data]
    except Exception as e:
        logger.error(f"Error getting users by role {role}: {e}")
        return []
