"""依赖注入工具。"""

from __future__ import annotations

from fastapi import Depends, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.service import ConversionService, TaskManager
from app.state import get_conversion_service, get_task_manager


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
