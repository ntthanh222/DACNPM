"""
Rate Limiter and SSE Connection Manager for CyberSec Assistant

Provides protection against DDoS attacks and SSE connection abuse.
Implements connection limits per user/IP to prevent slowloris attacks.
"""

import asyncio
import time
import logging
from typing import Dict, Optional
from fastapi import HTTPException
from uuid import UUID
import json

logger = logging.getLogger(__name__)

# ============================================================================
# In-Memory Connection Tracking (can be replaced with Redis for production)
# ============================================================================

class SSEConnectionTracker:
    """
    Tracks Server-Sent Events (SSE) connections to prevent abuse.

    SECURITY: Prevents slowloris attacks by limiting concurrent SSE
    connections per user/IP. Stores connection counts with automatic expiry.
    """

    def __init__(self, max_connections_per_user: int = 3, connection_timeout: int = 3600):
        """
        Initialize SSE connection tracker.

        Args:
            max_connections_per_user: Maximum concurrent SSE connections per user/IP
            connection_timeout: Connection timeout in seconds (default: 1 hour)
        """
        self.max_connections_per_user = max_connections_per_user
        self.connection_timeout = connection_timeout

        # In-memory storage (use Redis in production for distributed systems)
        self._connections: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def increment_connection(self, user_id: str) -> int:
        """
        Increment connection count for a user.

        Args:
            user_id: User identifier (UUID or IP address)

        Returns:
            Current connection count after increment

        Raises:
            HTTPException: 429 if connection limit exceeded
        """
        async with self._lock:
            current_time = int(time.time())

            # Clean up expired connections first
            self._cleanup_expired_connections(current_time)

            # Get current connection count
            if user_id not in self._connections:
                self._connections[user_id] = {
                    'count': 0,
                    'last_seen': current_time
                }

            # Check if limit would be exceeded
            if self._connections[user_id]['count'] >= self.max_connections_per_user:
                logger.warning(f"❌ SSE connection limit exceeded for user {user_id}")
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many concurrent SSE connections. Maximum: {self.max_connections_per_user}. Please close some connections and try again."
                )

            # Increment connection count
            self._connections[user_id]['count'] += 1
            self._connections[user_id]['last_seen'] = current_time

            logger.debug(f"✅ SSE connection incremented for user {user_id}: {self._connections[user_id]['count']}/{self.max_connections_per_user}")
            return self._connections[user_id]['count']

    async def decrement_connection(self, user_id: str) -> int:
        """
        Decrement connection count for a user.

        Args:
            user_id: User identifier

        Returns:
            Current connection count after decrement
        """
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id]['count'] = max(0, self._connections[user_id]['count'] - 1)
                self._connections[user_id]['last_seen'] = int(time.time())

                logger.debug(f"🔽 SSE connection decremented for user {user_id}: {self._connections[user_id]['count']}/{self.max_connections_per_user}")

                # Clean up if no connections remaining
                if self._connections[user_id]['count'] == 0:
                    del self._connections[user_id]
                    return 0

                return self._connections[user_id]['count']
            return 0

    def _cleanup_expired_connections(self, current_time: int):
        """Remove expired connection entries."""
        expired_users = []
        for user_id, data in self._connections.items():
            if current_time - data['last_seen'] > self.connection_timeout:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self._connections[user_id]
            logger.debug(f"🧹 Cleaned up expired SSE connections for user {user_id}")

    async def get_connection_count(self, user_id: str) -> int:
        """
        Get current connection count for a user.

        Args:
            user_id: User identifier

        Returns:
            Current connection count
        """
        async with self._lock:
            if user_id in self._connections:
                return self._connections[user_id]['count']
            return 0

    def get_stats(self) -> dict:
        """
        Get connection tracker statistics.

        Returns:
            Dictionary with tracker statistics
        """
        total_connections = sum(data['count'] for data in self._connections.values())
        active_users = len(self._connections)

        return {
            'total_connections': total_connections,
            'active_users': active_users,
            'max_connections_per_user': self.max_connections_per_user,
            'connection_timeout': self.connection_timeout
        }


# ============================================================================
# Rate Limiter for API Endpoints
# ============================================================================

class RateLimiter:
    """
    Rate limiter for API endpoints to prevent abuse.

    Provides sliding window rate limiting with configurable thresholds.
    Can be extended with Redis for distributed systems.
    """

    def __init__(self, requests_per_minute: int = 30, window_size: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            window_size: Time window in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size

        # In-memory storage (use Redis in production)
        self._requests: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (user_id, IP address, etc.)

        Returns:
            True if request is allowed, False otherwise

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        async with self._lock:
            current_time = time.time()

            # Initialize request tracking
            if identifier not in self._requests:
                self._requests[identifier] = []

            # Clean up old requests outside the time window
            self._requests[identifier] = [
                req_time for req_time in self._requests[identifier]
                if current_time - req_time < self.window_size
            ]

            # Check if limit would be exceeded
            if len(self._requests[identifier]) >= self.requests_per_minute:
                logger.warning(f"❌ Rate limit exceeded for {identifier}")
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per {self.window_size} seconds."
                )

            # Add current request
            self._requests[identifier].append(current_time)
            return True

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with rate limiter statistics
        """
        total_requests = sum(len(requests) for requests in self._requests.values())
        active_identifiers = len(self._requests)

        return {
            'total_tracked_requests': total_requests,
            'active_identifiers': active_identifiers,
            'requests_per_minute': self.requests_per_minute,
            'window_size': self.window_size
        }


# ============================================================================
# Global Instances
# ============================================================================

# SSE connection tracker (max 3 connections per user, 1 hour timeout)
sse_tracker = SSEConnectionTracker(max_connections_per_user=3, connection_timeout=3600)

# API rate limiter (30 requests per minute)
api_rate_limiter = RateLimiter(requests_per_minute=30, window_size=60)


# ============================================================================
# Convenience Functions
# ============================================================================

async def check_sse_limit(user_id: str) -> int:
    """
    Check and increment SSE connection limit for a user.

    Args:
        user_id: User identifier

    Returns:
        Current connection count after increment

    Raises:
        HTTPException: 429 if connection limit exceeded
    """
    return await sse_tracker.increment_connection(user_id)


async def release_sse_connection(user_id: str) -> int:
    """
    Release SSE connection for a user.

    Args:
        user_id: User identifier

    Returns:
        Current connection count after decrement
    """
    return await sse_tracker.decrement_connection(user_id)


async def check_api_rate_limit(identifier: str) -> bool:
    """
    Check API rate limit for an identifier.

    Args:
        identifier: Unique identifier (user_id, IP address, etc.)

    Returns:
        True if request is allowed

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    return await api_rate_limiter.check_rate_limit(identifier)


def get_sse_stats() -> dict:
    """Get SSE connection tracker statistics."""
    return sse_tracker.get_stats()


def get_rate_limiter_stats() -> dict:
    """Get rate limiter statistics."""
    return api_rate_limiter.get_stats()


# ============================================================================
# Development Note
# ============================================================================

"""
PRODUCTION UPGRADE GUIDE:

For production deployments, replace in-memory storage with Redis:

1. Install Redis client: pip install redis
2. Replace _connections dict with Redis operations:
   - Use INCR for connection counting
   - Use EXPIRE for automatic cleanup
   - Use Redis transactions for atomic operations

Example Redis implementation:
```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def increment_connection(user_id: str) -> int:
    key = f"sse_connections:{user_id}"
    count = redis_client.incr(key)
    redis_client.expire(key, 3600)  # 1 hour timeout
    return count
```

Benefits of Redis:
- Distributed systems support
- Automatic cleanup with TTL
- Better performance for high traffic
- Shared state across multiple server instances
"""
