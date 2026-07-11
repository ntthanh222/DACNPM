"""
Cache Manager for CyberSec Assistant

Provides Redis-based caching for frequently accessed data like dashboard statistics.
Improves performance by reducing database queries for expensive computations.
"""

import json
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import timedelta

logger = logging.getLogger(__name__)

# Global Redis client (will be initialized on first use)
_redis_client = None


def get_redis_client():
    """
    Get or create Redis client instance.

    Returns:
        Redis client instance or None if Redis is unavailable
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_db = int(os.environ.get('REDIS_DB', 0))

        _redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2
        )

        # Test connection
        _redis_client.ping()
        logger.info("✅ Redis cache initialized successfully")
        return _redis_client

    except ImportError:
        logger.warning("Redis package not installed - caching disabled")
        return None
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} - caching disabled")
        return None


async def get_cached_data(cache_key: str, ttl: int = 600) -> Optional[Dict[str, Any]]:
    """
    Get data from cache if available and not expired.

    Args:
        cache_key: Unique key for the cached data
        ttl: Time to live in seconds (default: 10 minutes)

    Returns:
        Cached data as dictionary, or None if not found/expired
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return None

        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ Cache hit for key: {cache_key}")
            return json.loads(cached_data)
        else:
            logger.debug(f"❌ Cache miss for key: {cache_key}")
            return None

    except Exception as e:
        logger.error(f"Error reading from cache: {e}")
        return None


async def set_cached_data(cache_key: str, data: Dict[str, Any], ttl: int = 600) -> bool:
    """
    Store data in cache with expiration.

    Args:
        cache_key: Unique key for the cached data
        data: Data to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: 10 minutes)

    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return False

        serialized_data = json.dumps(data)
        redis_client.setex(cache_key, ttl, serialized_data)
        logger.debug(f"✅ Data cached with key: {cache_key} (TTL: {ttl}s)")
        return True

    except Exception as e:
        logger.error(f"Error writing to cache: {e}")
        return False


async def invalidate_cache(cache_key: str) -> bool:
    """
    Invalidate (delete) cached data.

    Args:
        cache_key: Key to invalidate

    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return False

        redis_client.delete(cache_key)
        logger.debug(f"🗑️ Cache invalidated for key: {cache_key}")
        return True

    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return False


async def invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., "user_stats:*")

    Returns:
        Number of keys invalidated
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return 0

        keys = redis_client.keys(pattern)
        if keys:
            count = redis_client.delete(*keys)
            logger.info(f"🗑️ Invalidated {count} cache keys matching pattern: {pattern}")
            return count
        return 0

    except Exception as e:
        logger.error(f"Error invalidating cache pattern: {e}")
        return 0


async def get_or_compute(
    cache_key: str,
    compute_fn: callable,
    ttl: int = 600,
    force_refresh: bool = False
) -> Any:
    """
    Get data from cache, or compute and cache if not available.

    Args:
        cache_key: Unique key for the cached data
        compute_fn: Async function to compute data if not cached
        ttl: Time to live in seconds (default: 10 minutes)
        force_refresh: Force recomputation even if cached

    Returns:
        Computed or cached data
    """
    # Try to get from cache (unless force refresh)
    if not force_refresh:
        cached = await get_cached_data(cache_key, ttl)
        if cached is not None:
            return cached

    # Compute data
    logger.debug(f"🔄 Computing data for key: {cache_key}")
    try:
        data = await compute_fn()

        # Cache the result
        if data is not None:
            await set_cached_data(cache_key, data, ttl)

        return data

    except Exception as e:
        logger.error(f"Error computing data for cache key {cache_key}: {e}")
        raise


async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics and health.

    Returns:
        Dictionary with cache statistics
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return {
                'cache_enabled': False,
                'status': 'unavailable'
            }

        # Get Redis info
        info = redis_client.info('stats')
        key_count = redis_client.dbsize()

        return {
            'cache_enabled': True,
            'status': 'available',
            'total_keys': key_count,
            'total_connections': info.get('total_connections_received', 0),
            'total_commands': info.get('total_commands_processed', 0),
            'cache_hit_rate': calculate_hit_rate(info),
            'memory_used': info.get('used_memory_human', 0)
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            'cache_enabled': False,
            'status': 'error',
            'error': str(e)
        }


def calculate_hit_rate(redis_info: Dict) -> str:
    """
    Calculate cache hit rate from Redis info.

    Args:
        redis_info: Redis info dictionary

    Returns:
        Hit rate as percentage string
    """
    try:
        hits = redis_info.get('keyspace_hits', 0)
        misses = redis_info.get('keyspace_misses', 0)
        total = hits + misses

        if total == 0:
            return "0.0%"

        hit_rate = (hits / total) * 100
        return f"{hit_rate:.1f}%"

    except Exception:
        return "N/A"


# ============================================================================
# Convenience Functions for Dashboard Statistics
# ============================================================================

async def get_dashboard_stats(
    user_id: str,
    compute_fn: callable,
    ttl: int = 600,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get or compute dashboard statistics for a user.

    Args:
        user_id: User ID for cache key
        compute_fn: Async function to compute dashboard stats
        ttl: Cache TTL in seconds (default: 10 minutes)
        force_refresh: Force recomputation

    Returns:
        Dashboard statistics dictionary
    """
    cache_key = f"dashboard_stats:{user_id}"
    return await get_or_compute(cache_key, compute_fn, ttl, force_refresh)


async def get_admin_stats(
    compute_fn: callable,
    ttl: int = 300,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get or compute admin statistics.

    Args:
        compute_fn: Async function to compute admin stats
        ttl: Cache TTL in seconds (default: 5 minutes)
        force_refresh: Force recomputation

    Returns:
        Admin statistics dictionary
    """
    cache_key = "admin_stats:global"
    return await get_or_compute(cache_key, compute_fn, ttl, force_refresh)


async def invalidate_user_cache(user_id: str) -> bool:
    """
    Invalidate all cache keys for a specific user.

    Args:
        user_id: User ID to invalidate

    Returns:
        True if successful, False otherwise
    """
    pattern = f"*:{user_id}"
    return await invalidate_pattern(pattern) > 0


# ============================================================================
# Development Note
# ============================================================================

"""
PRODUCTION CONFIGURATION:

For production deployments, ensure Redis is properly configured:

1. Install Redis server:
   - Ubuntu/Debian: apt-get install redis-server
   - Docker: Use docker-compose Redis service
   - Cloud: Use AWS ElastiCache, Azure Cache, etc.

2. Configure environment variables:
   - REDIS_HOST: Redis server host (default: localhost)
   - REDIS_PORT: Redis server port (default: 6379)
   - REDIS_DB: Redis database number (default: 0)

3. Monitor cache performance:
   - Track cache hit rates with get_cache_stats()
   - Adjust TTL based on data freshness requirements
   - Monitor Redis memory usage

4. Cache invalidation strategy:
   - Automatic expiration via TTL
   - Manual invalidation on data updates
   - Pattern-based invalidation for bulk updates

Example TTL values:
- Dashboard stats: 600s (10 minutes)
- User sessions: 3600s (1 hour)
- Static content: 86400s (24 hours)
- Real-time data: 60s (1 minute) or no caching
"""
