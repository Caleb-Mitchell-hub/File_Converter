"""依赖注入工具。"""

from __future__ import annotations

from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.security import decode_access_token
from app.service import ConversionService, TaskManager
from app.service.user_service import User, get_user_by_id
from app.state import get_conversion_service, get_task_manager

# Bearer token 解析器（auto_error=False：缺失时返回 None，由我们统一抛 401）
_bearer_scheme = HTTPBearer(auto_error=False)


def settings_dep() -> Settings:
    return get_settings()


def task_manager_dep() -> TaskManager:
    return get_task_manager()


def conversion_service_dep() -> ConversionService:
    try:
        return get_conversion_service()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    """FastAPI 依赖：解析 Bearer token 并返回当前用户。

    任何失败（缺失 / 无效 / 过期 / 用户不存在）统一抛 401，
    避免向前端泄露"用户名是否存在"等探测信息。
    """
    settings = get_settings()
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录",
        )
    payload = decode_access_token(credentials.credentials, settings.jwt_secret)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效或已过期，请重新登录",
        )
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效",
        ) from None
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在，请重新登录",
        )
    return user


async def validate_upload(
    file: UploadFile,
    *,
    allowed_extensions: list[str] | None = None,
    max_size_mb: int | None = None,
) -> UploadFile:
    """FastAPI 依赖：校验上传文件。"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名为空",
        )

    if allowed_extensions:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in {e.lower() for e in allowed_extensions}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {ext}，允许: {allowed_extensions}",
            )

    if max_size_mb is not None:
        # 注意：UploadFile.size 不是所有后端都暴露；
        # 这里用 spool_max_size 由 Starlette 在流式读取时强制。
        # 此处仅作占位提示。
        pass

    return file
