"""Central API router registration."""

from fastapi import APIRouter

from backend.api import auth_routes, chat, chatbot, cve, news, profiles, reports, stats
from backend.api import proxy, system
from backend.api.v1 import admin


api_router = APIRouter()
api_router.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
api_router.include_router(chat.router, prefix="/api/chat", tags=["chat"])
api_router.include_router(news.router, prefix="/api/news", tags=["news"])
api_router.include_router(stats.router, prefix="/api/stats", tags=["stats"])
api_router.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])
api_router.include_router(cve.router, prefix="/api/cve", tags=["cve"])
api_router.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/api/admin", tags=["admin"])
api_router.include_router(reports.router, prefix="/api/reports", tags=["reports"])
api_router.include_router(proxy.router, prefix="/api/proxy", tags=["proxy"])
api_router.include_router(system.router)
