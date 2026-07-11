"""
Repository Layer - Data Access Pattern

This layer provides a clean abstraction over database operations,
eliminating CRUD code duplication and ensuring consistent data access.
"""

from backend.repositories.base_repository import BaseRepository, FallbackRepository
from backend.repositories.generic_repository import (
    GenericRepository,
    CacheStrategy,
    CacheManager,
    QueryOptimizer
)
from backend.repositories.user_repository import UserRepository

__all__ = [
    'BaseRepository',
    'FallbackRepository',
    'GenericRepository',
    'CacheStrategy',
    'CacheManager',
    'QueryOptimizer',
    'UserRepository'
]