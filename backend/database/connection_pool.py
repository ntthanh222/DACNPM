"""
Database connection pool manager for optimized database operations.

Provides connection pooling, query monitoring, and performance optimization
for database interactions.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)


class ConnectionPoolConfig:
    """Configuration for database connection pool."""

    def __init__(self,
                 min_size: int = 5,
                 max_size: int = 20,
                 max_queries: int = 50000,
                 max_inactive_connection_lifetime: float = 300.0,
                 command_timeout: float = 30.0):
        self.min_size = min_size
        self.max_size = max_size
        self.max_queries = max_queries
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime
        self.command_timeout = command_timeout


class QueryStats:
    """Statistics for database queries."""

    def __init__(self):
        self.total_queries = 0
        self.slow_queries = 0
        self.failed_queries = 0
        self.total_execution_time = 0.0
        self.query_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        self.slow_query_threshold = 0.1  # 100ms

    def record_query(self, query: str, execution_time: float, success: bool = True):
        """Record query execution statistics."""
        self.total_queries += 1
        self.total_execution_time += execution_time

        if execution_time > self.slow_query_threshold:
            self.slow_queries += 1

        if not success:
            self.failed_queries += 1

        # Add to history
        query_info = {
            "query": query[:200],  # Truncate long queries
            "execution_time": execution_time,
            "success": success,
            "timestamp": datetime.now()
        }

        self.query_history.append(query_info)

        # Maintain history size
        if len(self.query_history) > self.max_history_size:
            self.query_history.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        avg_execution_time = (
            self.total_execution_time / self.total_queries
            if self.total_queries > 0
            else 0.0
        )

        return {
            "total_queries": self.total_queries,
            "slow_queries": self.slow_queries,
            "failed_queries": self.failed_queries,
            "avg_execution_time": avg_execution_time,
            "success_rate": (
                (self.total_queries - self.failed_queries) / self.total_queries * 100
                if self.total_queries > 0
                else 0.0
            ),
            "slow_query_rate": (
                self.slow_queries / self.total_queries * 100
                if self.total_queries > 0
                else 0.0
            )
        }

    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow queries from history."""
        slow_queries = [
            q for q in self.query_history
            if q["execution_time"] > self.slow_query_threshold
        ]
        return sorted(slow_queries, key=lambda x: x["execution_time"], reverse=True)[:limit]


class DatabaseConnectionPool:
    """Database connection pool with monitoring and optimization."""

    def __init__(self, config: Optional[ConnectionPoolConfig] = None):
        self.config = config or ConnectionPoolConfig()
        self.pool = None
        self.query_stats = QueryStats()
        self._is_initialized = False

    async def initialize(self, database_url: str):
        """Initialize connection pool."""
        if self._is_initialized:
            return

        try:
            # This would use asyncpg or similar in production
            # For now, it's a mock implementation
            logger.info(f"Initializing database connection pool with config: {self.config}")
            logger.info(f"Min size: {self.config.min_size}, Max size: {self.config.max_size}")

            # Mock pool initialization
            # In production:
            # self.pool = await asyncpg.create_pool(
            #     database_url,
            #     min_size=self.config.min_size,
            #     max_size=self.config.max_size,
            #     max_queries=self.config.max_queries,
            #     max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
            #     command_timeout=self.config.command_timeout
            # )

            self._is_initialized = True
            logger.info("Database connection pool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self._is_initialized = False
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire_connection(self):
        """Acquire connection from pool."""
        if not self._is_initialized:
            raise RuntimeError("Connection pool not initialized")

        # In production, this would be: async with self.pool.acquire() as connection:
        connection = None  # Mock connection
        try:
            yield connection
        finally:
            pass  # Connection automatically returned to pool

    async def execute_query(self, query: str, params: List[Any] = None) -> Dict[str, Any]:
        """Execute query and track performance."""
        start_time = time.time()
        success = False

        try:
            async with self.acquire_connection() as connection:
                # In production, execute actual query
                # result = await connection.fetchrow(query, *params)
                result = {}  # Mock result

                success = True
                return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

        finally:
            execution_time = time.time() - start_time
            self.query_stats.record_query(query, execution_time, success)

    async def execute_query_many(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute query returning multiple rows."""
        start_time = time.time()
        success = False

        try:
            async with self.acquire_connection() as connection:
                # In production, execute actual query
                # results = await connection.fetch(query, *params)
                results = []  # Mock results

                success = True
                return results

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

        finally:
            execution_time = time.time() - start_time
            self.query_stats.record_query(query, execution_time, success)

    async def execute_command(self, command: str, params: List[Any] = None) -> str:
        """Execute command (INSERT, UPDATE, DELETE)."""
        start_time = time.time()
        success = False

        try:
            async with self.acquire_connection() as connection:
                # In production, execute actual command
                # result = await connection.execute(command, *params)
                result = "INSERT 0 1"  # Mock result

                success = True
                return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise

        finally:
            execution_time = time.time() - start_time
            self.query_stats.record_query(command, execution_time, success)

    async def execute_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """Execute multiple operations in a transaction."""
        start_time = time.time()
        success = False

        try:
            async with self.acquire_connection() as connection:
                async with connection.transaction():
                    for operation in operations:
                        query = operation.get("query")
                        params = operation.get("params", [])

                        if operation.get("type") == "select":
                            await self.execute_query(query, params)
                        elif operation.get("type") == "select_many":
                            await self.execute_query_many(query, params)
                        else:
                            await self.execute_command(query, params)

                success = True
                return True

        except Exception as e:
            logger.error(f"Transaction execution failed: {e}")
            return False

        finally:
            execution_time = time.time() - start_time
            transaction_query = f"TRANSACTION ({len(operations)} operations)"
            self.query_stats.record_query(transaction_query, execution_time, success)

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = {
            "initialized": self._is_initialized,
            "config": {
                "min_size": self.config.min_size,
                "max_size": self.config.max_size,
                "max_queries": self.config.max_queries,
                "max_inactive_connection_lifetime": self.config.max_inactive_connection_lifetime,
                "command_timeout": self.config.command_timeout
            }
        }

        if self.pool:
            # In production, get actual pool stats
            # stats["pool_size"] = self.pool.get_size()
            # stats["available_connections"] = self.pool.get_idle_size()
            stats["pool_size"] = 0
            stats["available_connections"] = 0

        return stats

    def get_query_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        return self.query_stats.get_stats()

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return {
            "pool_stats": self.get_pool_stats(),
            "query_stats": self.get_query_stats(),
            "slow_queries": self.query_stats.get_slow_queries(),
            "generated_at": datetime.now().isoformat()
        }


# Global connection pool instance
_connection_pool: Optional[DatabaseConnectionPool] = None


def get_connection_pool() -> DatabaseConnectionPool:
    """Get global connection pool instance."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = DatabaseConnectionPool()
    return _connection_pool


async def initialize_database_pool(database_url: str, config: Optional[ConnectionPoolConfig] = None):
    """Initialize global database connection pool."""
    pool = get_connection_pool()
    if config:
        pool.config = config
    await pool.initialize(database_url)


async def close_database_pool():
    """Close global database connection pool."""
    global _connection_pool
    if _connection_pool:
        await _connection_pool.close()
        _connection_pool = None


@asynccontextmanager
async def database_transaction():
    """Context manager for database transactions."""
    pool = get_connection_pool()
    async with pool.acquire_connection() as connection:
        async with connection.transaction():
            yield connection