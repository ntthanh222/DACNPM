"""
Generic repository with built-in caching and optimization.

Provides a base repository class with caching, connection pooling,
and query optimization for database operations.
"""

import asyncio
import logging
from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import json

# Generic type for model entities
T = TypeVar('T')

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Cache strategy configuration."""

    def __init__(self,
                 enabled: bool = True,
                 ttl: int = 3600,
                 prefix: str = "repo",
                 use_l1_cache: bool = True,
                 use_l2_cache: bool = True):
        self.enabled = enabled
        self.ttl = ttl  # Time to live in seconds
        self.prefix = prefix
        self.use_l1_cache = use_l1_cache
        self.use_l2_cache = use_l2_cache


class QueryOptimizer:
    """Query optimization utilities."""

    @staticmethod
    def optimize_select_fields(fields: List[str], table: str) -> str:
        """Optimize SELECT statement with specific fields."""
        if not fields or "*" in fields:
            return f"SELECT * FROM {table}"
        return f"SELECT {', '.join(fields)} FROM {table}"

    @staticmethod
    def add_pagination(query: str, limit: int = 20, offset: int = 0) -> str:
        """Add pagination to query."""
        return f"{query} LIMIT {limit} OFFSET {offset}"

    @staticmethod
    def add_ordering(query: str, order_by: str = "id", direction: str = "ASC") -> str:
        """Add ordering to query."""
        allowed_directions = ["ASC", "DESC"]
        if direction.upper() not in allowed_directions:
            direction = "ASC"
        return f"{query} ORDER BY {order_by} {direction}"

    @staticmethod
    def build_where_clause(conditions: Dict[str, Any]) -> tuple:
        """Build WHERE clause from conditions dictionary."""
        if not conditions:
            return "", []

        where_clauses = []
        params = []

        for field, value in conditions.items():
            if value is None:
                where_clauses.append(f"{field} IS NULL")
            elif isinstance(value, (list, tuple)):
                placeholders = ','.join(['$' + str(i + len(params) + 1) for i in range(len(value))])
                where_clauses.append(f"{field} IN ({placeholders})")
                params.extend(value)
            else:
                where_clauses.append(f"{field} = ${len(params) + 1}")
                params.append(value)

        where_sql = " AND ".join(where_clauses)
        return f"WHERE {where_sql}", params


class CacheManager:
    """Multi-level cache manager."""

    def __init__(self):
        self.l1_cache: Dict[str, tuple] = {}  # In-memory cache
        self.l2_cache = None  # Redis cache (to be initialized)
        self.cache_stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "writes": 0
        }

    async def get(self, key: str, strategy: CacheStrategy) -> Optional[Any]:
        """Get value from cache."""
        if not strategy.enabled:
            return None

        # Try L1 cache first
        if strategy.use_l1_cache:
            l1_data = self._get_l1(key)
            if l1_data is not None:
                self.cache_stats["l1_hits"] += 1
                return l1_data

        # Try L2 cache
        if strategy.use_l2_cache:
            l2_data = await self._get_l2(key)
            if l2_data is not None:
                self.cache_stats["l2_hits"] += 1
                # Populate L1 cache
                if strategy.use_l1_cache:
                    self._set_l1(key, l2_data, strategy.ttl)
                return l2_data

        # Cache miss
        if strategy.use_l1_cache:
            self.cache_stats["l1_misses"] += 1
        if strategy.use_l2_cache:
            self.cache_stats["l2_misses"] += 1

        return None

    async def set(self, key: str, value: Any, strategy: CacheStrategy):
        """Set value in cache."""
        if not strategy.enabled:
            return

        self.cache_stats["writes"] += 1

        # Set L1 cache
        if strategy.use_l1_cache:
            self._set_l1(key, value, strategy.ttl)

        # Set L2 cache
        if strategy.use_l2_cache:
            await self._set_l2(key, value, strategy.ttl)

    async def delete(self, key: str, strategy: CacheStrategy):
        """Delete value from cache."""
        # Delete from L1
        if strategy.use_l1_cache and key in self.l1_cache:
            del self.l1_cache[key]

        # Delete from L2
        if strategy.use_l2_cache:
            await self._delete_l2(key)

    async def invalidate_pattern(self, pattern: str, strategy: CacheStrategy):
        """Invalidate all keys matching pattern."""
        # Invalidate L1 cache
        if strategy.use_l1_cache:
            keys_to_delete = [k for k in self.l1_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.l1_cache[key]

        # Invalidate L2 cache
        if strategy.use_l2_cache:
            await self._invalidate_l2_pattern(pattern)

    def _get_l1(self, key: str) -> Optional[Any]:
        """Get from L1 cache."""
        if key in self.l1_cache:
            value, expiry = self.l1_cache[key]
            if expiry > datetime.now():
                return value
            else:
                # Expired, remove from cache
                del self.l1_cache[key]
        return None

    def _set_l1(self, key: str, value: Any, ttl: int):
        """Set in L1 cache."""
        expiry = datetime.now() + timedelta(seconds=ttl)
        self.l1_cache[key] = (value, expiry)

        # Implement simple LRU eviction if cache gets too large
        if len(self.l1_cache) > 1000:
            # Remove oldest entries
            keys = list(self.l1_cache.keys())
            for key in keys[:100]:  # Remove 10% of entries
                del self.l1_cache[key]

    async def _get_l2(self, key: str) -> Optional[Any]:
        """Get from L2 cache (Redis)."""
        if self.l2_cache is None:
            return None

        try:
            data = await self.l2_cache.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"L2 cache get failed: {e}")
        return None

    async def _set_l2(self, key: str, value: Any, ttl: int):
        """Set in L2 cache (Redis)."""
        if self.l2_cache is None:
            return

        try:
            await self.l2_cache.set(key, json.dumps(value), ex=ttl)
        except Exception as e:
            logger.warning(f"L2 cache set failed: {e}")

    async def _delete_l2(self, key: str):
        """Delete from L2 cache (Redis)."""
        if self.l2_cache is None:
            return

        try:
            await self.l2_cache.delete(key)
        except Exception as e:
            logger.warning(f"L2 cache delete failed: {e}")

    async def _invalidate_l2_pattern(self, pattern: str):
        """Invalidate pattern in L2 cache (Redis)."""
        if self.l2_cache is None:
            return

        try:
            keys = await self.l2_cache.keys(f"*{pattern}*")
            if keys:
                await self.l2_cache.delete(*keys)
        except Exception as e:
            logger.warning(f"L2 cache pattern invalidation failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats["l1_hits"] + self.cache_stats["l1_misses"]
        l1_hit_rate = (self.cache_stats["l1_hits"] / total_requests * 100) if total_requests > 0 else 0

        total_requests = self.cache_stats["l2_hits"] + self.cache_stats["l2_misses"]
        l2_hit_rate = (self.cache_stats["l2_hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.cache_stats,
            "l1_hit_rate": l1_hit_rate,
            "l2_hit_rate": l2_hit_rate,
            "l1_cache_size": len(self.l1_cache)
        }


class GenericRepository(Generic[T], ABC):
    """Generic repository with caching and optimization."""

    def __init__(self,
                 table_name: str,
                 model_class: type,
                 cache_strategy: Optional[CacheStrategy] = None,
                 cache_manager: Optional[CacheManager] = None):
        self.table_name = table_name
        self.model_class = model_class
        self.cache_strategy = cache_strategy or CacheStrategy()
        self.cache_manager = cache_manager or CacheManager()
        self.query_optimizer = QueryOptimizer()

    def _generate_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation."""
        key_parts = [self.cache_strategy.prefix, self.table_name, operation]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)

    async def find_by_id(self, id: Any, fields: Optional[List[str]] = None) -> Optional[T]:
        """Find entity by ID with caching."""
        cache_key = self._generate_cache_key("find_by_id", id=str(id))
        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return self.model_class(**cached_result)

        # Build optimized query
        select_fields = self.query_optimizer.optimize_select_fields(fields or ["*"], self.table_name)
        query = f"{select_fields} WHERE id = $1"

        # Execute query
        result = await self._execute_query(query, [id])
        if result:
            entity = self.model_class(**result)
            # Cache the result
            await self.cache_manager.set(cache_key, result, self.cache_strategy)
            return entity

        return None

    async def find_all(self,
                     conditions: Optional[Dict[str, Any]] = None,
                     fields: Optional[List[str]] = None,
                     limit: int = 100,
                     offset: int = 0,
                     order_by: str = "id",
                     direction: str = "ASC") -> List[T]:
        """Find all entities with conditions, pagination, and caching."""
        cache_key = self._generate_cache_key(
            "find_all",
            conditions=str(conditions),
            fields=str(fields),
            limit=limit,
            offset=offset,
            order_by=order_by,
            direction=direction
        )

        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return [self.model_class(**item) for item in cached_result]

        # Build optimized query
        select_fields = self.query_optimizer.optimize_select_fields(fields or ["*"], self.table_name)
        query = select_fields

        # Add WHERE clause
        where_clause, params = self.query_optimizer.build_where_clause(conditions or {})
        query = f"{query} {where_clause}" if where_clause else query

        # Add ordering and pagination
        query = self.query_optimizer.add_ordering(query, order_by, direction)
        query = self.query_optimizer.add_pagination(query, limit, offset)

        # Execute query
        results = await self._execute_query(query, params)

        # Cache the results
        await self.cache_manager.set(cache_key, results, self.cache_strategy)

        return [self.model_class(**item) for item in results]

    async def create(self, entity: T) -> T:
        """Create new entity and invalidate relevant caches."""
        # Extract entity data
        entity_data = self._entity_to_dict(entity)

        # Build INSERT query
        fields = list(entity_data.keys())
        placeholders = [f"${i + 1}" for i in range(len(fields))]
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        # Execute query
        result = await self._execute_query(query, list(entity_data.values()))

        # Invalidate list caches
        await self._invalidate_list_caches()

        return self.model_class(**result)

    async def update(self, id: Any, entity: T) -> Optional[T]:
        """Update entity and invalidate caches."""
        # Extract entity data
        entity_data = self._entity_to_dict(entity)

        # Build UPDATE query
        set_clauses = [f"{field} = ${i + 1}" for i, field in enumerate(entity_data.keys())]
        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE id = ${len(entity_data) + 1}
            RETURNING *
        """

        # Execute query
        params = list(entity_data.values()) + [id]
        result = await self._execute_query(query, params)

        if result:
            # Invalidate specific and list caches
            await self._invalidate_entity_cache(id)
            await self._invalidate_list_caches()

            return self.model_class(**result)

        return None

    async def delete(self, id: Any) -> bool:
        """Delete entity and invalidate caches."""
        query = f"DELETE FROM {self.table_name} WHERE id = $1"

        # Execute query
        result = await self._execute_query(query, [id], return_result=False)

        if result:
            # Invalidate caches
            await self._invalidate_entity_cache(id)
            await self._invalidate_list_caches()

        return result

    async def count(self, conditions: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with conditions and caching."""
        cache_key = self._generate_cache_key("count", conditions=str(conditions))

        cached_result = await self.cache_manager.get(cache_key, self.cache_strategy)
        if cached_result is not None:
            return cached_result

        # Build COUNT query
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"

        # Add WHERE clause
        where_clause, params = self.query_optimizer.build_where_clause(conditions or {})
        query = f"{query} {where_clause}" if where_clause else query

        # Execute query
        result = await self._execute_query(query, params)
        count = result.get("count", 0) if result else 0

        # Cache the result
        await self.cache_manager.set(cache_key, count, self.cache_strategy)

        return count

    async def batch_create(self, entities: List[T]) -> List[T]:
        """Batch create entities with optimized query."""
        if not entities:
            return []

        # Extract entity data
        all_data = [self._entity_to_dict(entity) for entity in entities]
        fields = all_data[0].keys()

        # Build batch INSERT query
        values_placeholders = []
        params = []
        param_index = 1

        for entity_data in all_data:
            entity_placeholders = []
            for field in fields:
                entity_placeholders.append(f"${param_index}")
                params.append(entity_data[field])
                param_index += 1
            values_placeholders.append(f"({', '.join(entity_placeholders)})")

        query = f"""
            INSERT INTO {self.table_name} ({', '.join(fields)})
            VALUES {', '.join(values_placeholders)}
            RETURNING *
        """

        # Execute query
        results = await self._execute_query(query, params, return_many=True)

        # Invalidate list caches
        await self._invalidate_list_caches()

        return [self.model_class(**result) for result in results]

    async def _invalidate_entity_cache(self, id: Any):
        """Invalidate cache for specific entity."""
        cache_key = self._generate_cache_key("find_by_id", id=str(id))
        await self.cache_manager.delete(cache_key, self.cache_strategy)

    async def _invalidate_list_caches(self):
        """Invalidate all list caches for this repository."""
        pattern = self._generate_cache_key("find_all")
        await self.cache_manager.invalidate_pattern(pattern, self.cache_strategy)
        pattern = self._generate_cache_key("count")
        await self.cache_manager.invalidate_pattern(pattern, self.cache_strategy)

    def _entity_to_dict(self, entity: T) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        if hasattr(entity, 'dict'):
            return entity.dict()
        elif hasattr(entity, '__dict__'):
            return {k: v for k, v in entity.__dict__.items() if not k.startswith('_')}
        else:
            raise ValueError(f"Cannot convert {type(entity)} to dictionary")

    @abstractmethod
    async def _execute_query(self, query: str, params: List[Any], return_result: bool = True, return_many: bool = False) -> Any:
        """Execute database query (to be implemented by specific repository)."""
        pass

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for this repository."""
        return self.cache_manager.get_stats()