"""app.api 包初始化：聚合所有子路由。"""

from fastapi import APIRouter

from app.api.routes import auth, convert, health, settings, tasks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(convert.router, tags=["convert"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])

__all__ = ["api_router"]
