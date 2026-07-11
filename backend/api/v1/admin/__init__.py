"""
Admin API Router for CyberSec Assistant

Aggregates all admin endpoint routers from individual modules.
"""
from fastapi import APIRouter

from .user_management import router as user_management_router
from .crawler_control import router as crawler_control_router
from .news_moderation import router as news_moderation_router
from .system_monitoring import router as system_monitoring_router
from .rag_operations import router as rag_operations_router
from .nlu_training import router as nlu_training_router

# Create main admin router
router = APIRouter()

# Include all sub-routers with their respective prefixes
router.include_router(user_management_router, tags=["admin", "users"])
router.include_router(crawler_control_router, tags=["admin", "crawler"])
router.include_router(news_moderation_router, tags=["admin", "news"])
router.include_router(system_monitoring_router, tags=["admin", "system"])
router.include_router(rag_operations_router, tags=["admin", "rag"])
router.include_router(nlu_training_router, tags=["admin", "nlu"])

__all__ = ['router']