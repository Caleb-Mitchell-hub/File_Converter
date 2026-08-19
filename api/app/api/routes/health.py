"""健康检查路由。

提供一个轻量级的 ``/api/v1/health`` 端点，用于：
    - 探活 (liveness / readiness)
    - 检查 doc_converter 引擎是否就绪
    - 返回当前支持的转换对数量

约定：只要进程在跑、doc_converter 加载成功，就返回 200 + ``status=ok``。
任何子资源（磁盘、上传目录等）异常都通过日志暴露，接口本身保持轻量。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, status

from app.api.dependencies import conversion_service_dep, settings_dep
from app.config import Settings
from app.models.schemas import APIResponse, HealthResponse
from app.service.conversion_service import ConversionService

router = APIRouter()


@router.get(
    "/health",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="健康检查",
    description="返回服务基本信息和当前已注册的转换对数量。",
)
async def health_check(
    settings: Settings = Depends(settings_dep),
    converter: ConversionService = Depends(conversion_service_dep),
) -> APIResponse:
    """健康检查端点。

    Returns:
        ``APIResponse`` 包装的 ``HealthResponse``。``data`` 字段为 HealthResponse 的 dict。
    """
    # 动态获取当前 doc_converter 支持的转换对数量
    try:
        supported_pairs = len(converter._supported_pairs)  # noqa: SLF001
    except Exception:  # pragma: no cover
        supported_pairs = 0

    health = HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        converters=5,  # 硬编码：xlsx/pdf/docx/image/ocr 共 5 个转换器模块
        supported_pairs=supported_pairs,
        timestamp=datetime.utcnow(),
    )
    return APIResponse(code=0, message="ok", data=health.model_dump())
