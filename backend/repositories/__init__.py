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
from backend.repositories.users import *
from backend.repositories.profiles import *
from backend.repositories.chat_history import *
from backend.repositories.cve_lookups import *
from backend.repositories.security_news import *
from backend.repositories.security_scans import *
from backend.repositories.stats import *

__all__ = [
    'BaseRepository',
    'FallbackRepository',
    'GenericRepository',
    'CacheStrategy',
    'CacheManager',
    'QueryOptimizer',
    'UserRepository'
]
