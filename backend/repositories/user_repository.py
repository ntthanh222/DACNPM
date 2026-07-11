"""
User repository implementation with caching and optimization.

Demonstrates how to extend the GenericRepository for specific entities.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from backend.repositories.generic_repository import GenericRepository, CacheStrategy, CacheManager

logger = logging.getLogger(__name__)


class UserRepository(GenericRepository[Dict[str, Any]]):
    """Repository for user entities with optimized caching."""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        # Initialize with user-specific cache strategy
        cache_strategy = CacheStrategy(
            enabled=True,
            ttl=1800,  # 30 minutes TTL for user data
            prefix="user_repo",
            use_l1_cache=True,  # Use in-memory cache
            use_l2_cache=True   # Use Redis cache
        )

        super().__init__(
            table_name="users",
            model_class=dict,  # Using dict for simplicity, could be Pydantic model
            cache_strategy=cache_strategy,
            cache_manager=cache_manager
        )

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email with caching."""
        cache_key = self._generate_cache_key("find_by_email", email=email)

        # Try cache first
        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return cached_result

        # Build optimized query
        query = """
            SELECT id, email, name, role, created_at, last_login
            FROM users
            WHERE email = $1 AND is_active = true
        """

        # Execute query
        result = await self._execute_query(query, [email])

        if result:
            # Cache the result
            await self.cache_manager.set(cache_key, result, self.cache_strategy)
            return result

        return None

    async def find_active_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Find active users with caching."""
        cache_key = self._generate_cache_key("find_active_users", limit=limit, offset=offset)

        # Try cache first
        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return cached_result

        # Build optimized query
        query = f"""
            SELECT id, email, name, role, created_at, last_login
            FROM users
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
        """

        # Execute query
        results = await self._execute_query(query, [], return_many=True)

        # Cache the results
        await self.cache_manager.set(cache_key, results, self.cache_strategy)

        return results

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        query = """
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = $1
        """

        result = await self._execute_query(query, [user_id], return_result=False)

        if result:
            # Invalidate user-specific caches
            await self._invalidate_entity_cache(user_id)
            # Also invalidate email-based cache (need to fetch email first)
            user = await self.find_by_id(user_id, fields=['email'])
            if user and 'email' in user:
                cache_key = self._generate_cache_key("find_by_email", email=user['email'])
                await self.cache_manager.delete(cache_key, self.cache_strategy)

        return result

    async def get_user_activity(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get user activity for the last N days."""
        cache_key = self._generate_cache_key("get_user_activity", user_id=user_id, days=days)

        # Try cache first (shorter TTL for activity data)
        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return cached_result

        # Build optimized query
        query = """
            SELECT
                DATE(action_timestamp) as date,
                COUNT(*) as action_count,
                ARRAY_AGG(DISTINCT action_type) as action_types
            FROM user_activity
            WHERE user_id = $1
                AND action_timestamp >= CURRENT_TIMESTAMP - INTERVAL '{days} days'
            GROUP BY DATE(action_timestamp)
            ORDER BY date DESC
        """

        # Execute query
        results = await self._execute_query(query, [user_id], return_many=True)

        # Cache with shorter TTL for activity data
        short_lived_strategy = CacheStrategy(
            enabled=True,
            ttl=300,  # 5 minutes
            prefix=self.cache_strategy.prefix,
            use_l1_cache=True,
            use_l2_cache=False  # Only use L1 cache for frequently changing data
        )
        await self.cache_manager.set(cache_key, results, short_lived_strategy)

        return results

    async def get_user_stats(self) -> Dict[str, Any]:
        """Get aggregate user statistics with caching."""
        cache_key = self._generate_cache_key("get_user_stats")

        # Try cache first
        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return cached_result

        # Build optimized aggregate query
        query = """
            SELECT
                COUNT(*) as total_users,
                COUNT(*) FILTER (WHERE is_active = true) as active_users,
                COUNT(*) FILTER (WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days') as new_users_30d,
                COUNT(*) FILTER (WHERE last_login >= CURRENT_TIMESTAMP - INTERVAL '7 days') as active_users_7d,
                COUNT(*) FILTER (WHERE role = 'admin') as admin_count,
                COUNT(*) FILTER (WHERE role = 'user') as user_count
            FROM users
        """

        # Execute query
        result = await self._execute_query(query, [])

        if result:
            # Cache statistics
            await self.cache_manager.set(cache_key, result, self.cache_strategy)
            return result

        return {}

    async def search_users(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search users by name or email."""
        # Don't cache search results as they're less predictable
        query = """
            SELECT id, email, name, role
            FROM users
            WHERE is_active = true
                AND (name ILIKE $1 OR email ILIKE $1)
            ORDER BY
                CASE
                    WHEN name ILIKE $1 THEN 1
                    WHEN email ILIKE $1 THEN 2
                    ELSE 3
                END
            LIMIT $2
        """

        search_pattern = f"%{search_term}%"
        results = await self._execute_query(query, [search_pattern, limit], return_many=True)

        return results

    async def _execute_query(self, query: str, params: List[Any], return_result: bool = True, return_many: bool = False) -> Any:
        """Execute database query (mock implementation)."""
        # This is a mock implementation
        # In production, this would use asyncpg or similar database driver

        logger.debug(f"Executing query: {query[:100]}...")
        logger.debug(f"Parameters: {params}")

        # Mock implementation - returns sample data
        if return_many:
            return []  # Return empty list for multiple results
        elif return_result:
            return {}  # Return empty dict for single result
        else:
            return True  # Return success status

    async def bulk_update_last_login(self, user_ids: List[str]) -> int:
        """Bulk update last login for multiple users."""
        if not user_ids:
            return 0

        # Build optimized bulk update query
        query = """
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = ANY($1)
        """

        result = await self._execute_query(query, [user_ids], return_result=False)

        if result:
            # Invalidate caches for all affected users
            for user_id in user_ids:
                await self._invalidate_entity_cache(user_id)

            # Invalidate list caches
            await self._invalidate_list_caches()

        return len(user_ids) if result else 0

    async def get_users_by_role(self, role: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get users by specific role with caching."""
        cache_key = self._generate_cache_key("get_users_by_role", role=role, limit=limit, offset=offset)

        # Try cache first
        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return cached_result

        # Build optimized query
        query = f"""
            SELECT id, email, name, created_at, last_login
            FROM users
            WHERE role = '{role}' AND is_active = true
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
        """

        # Execute query
        results = await self._execute_query(query, [], return_many=True)

        # Cache the results
        await self.cache_manager.set(cache_key, results, self.cache_strategy)

        return results

    def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository performance statistics."""
        cache_stats = self.get_cache_stats()

        return {
            "repository_type": "UserRepository",
            "table_name": self.table_name,
            "cache_enabled": self.cache_strategy.enabled,
            "cache_ttl": self.cache_strategy.ttl,
            "cache_stats": cache_stats
        }