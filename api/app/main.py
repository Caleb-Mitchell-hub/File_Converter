"""FastAPI 主入口。

启动流程：
    1. 加载配置 + 配置日志
    2. 构造 FastAPI app，挂载中间件 + 异常处理器
    3. 注册路由
    4. 启动 lifespan：初始化 TaskManager / ConversionService，启动后台清理协程
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api import api_router
from app.api.routes.info import router as info_router
from app.config import get_settings
from app.models.schemas import ErrorResponse
from app.service import TaskManager
from app.service.conversion_service import ConversionService
from app.state import (
    set_conversion_service,
    set_task_manager,
)
from app.utils.logger import configure_logging, get_logger

# 模块级单例（在 lifespan 中初始化）
_task_manager: TaskManager | None = None
_conversion_service: ConversionService | None = None
_cleanup_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用启动 / 关闭钩子。"""
    global _task_manager, _conversion_service, _cleanup_task

    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        log_dir=settings.log_dir,
        log_to_console=settings.log_to_console,
        log_to_file=settings.log_to_file,
        retention_days=settings.log_retention_days,
    )
    log = get_logger("app.lifespan")
    log.info("=" * 60)
    log.info("启动 %s v%s", settings.app_name, settings.app_version)
    log.info("上传目录: %s", settings.upload_dir)
    log.info("输出目录: %s", settings.output_dir)
    log.info("日志目录: %s", settings.log_dir)
    log.info("=" * 60)

    # 初始化单例
    _task_manager = TaskManager(ttl_hours=settings.task_result_ttl_hours)
    set_task_manager(_task_manager)
    try:
        _conversion_service = ConversionService()
        set_conversion_service(_conversion_service)
    except Exception as exc:
        log.exception("ConversionService 初始化失败: %s", exc)
        # 不阻塞启动，但转换接口将不可用
        _conversion_service = None

    # 启动过期清理后台任务（每 1 小时跑一次）
    async def _cleanup_loop() -> None:
        while True:
            try:
                await asyncio.sleep(3600)
                if _task_manager:
                    n = _task_manager.cleanup_expired()
                    if n:
                        log.info("清理过期任务: %d 个", n)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pragma: no cover
                log.exception("清理任务异常: %s", exc)

    _cleanup_task = asyncio.create_task(_cleanup_loop())

    try:
        yield
    finally:
        log.info("关闭应用...")
        if _cleanup_task:
            _cleanup_task.cancel()
            try:
                await _cleanup_task
            except asyncio.CancelledError:
                pass
        log.info("应用关闭完成")


def create_app() -> FastAPI:
    """工厂函数：创建 FastAPI 应用实例。"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "企业级文档转换 REST API。\n\n"
            "支持：\n"
            "- Excel ↔ PDF\n"
            "- Excel → 图片\n"
            "- PDF → 图片\n"
            "- 图片 → PDF\n"
            "- Word ↔ PDF\n"
            "- 图片 OCR → Excel\n\n"
            "**异步处理**：单文件返回 task_id 后台执行，"
            "通过 `/api/v1/tasks/{task_id}` 查询进度与下载。"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        log = get_logger("app.http")
        log.warning("HTTP %d on %s: %s", exc.status_code, request.url.path, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.status_code,
                message=str(exc.detail),
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        log = get_logger("app.validation")
        log.warning("校验失败 on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                code=422,
                message="请求参数校验失败",
                detail=str(exc.errors()),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log = get_logger("app.error")
        log.exception("未捕获异常 on %s: %s", request.url.path, exc)
        # 关键：把异常文本也带回给前端，方便用户看到真实失败原因。
        # 仅裁剪到 1000 字符防止响应体膨胀或泄漏堆栈敏感信息。
        settings = get_settings()
        raw = str(exc) or exc.__class__.__name__
        detail = raw[:1000] if raw else None
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code=500,
                # 把真实原因放在 message，前端优先用这个而不是固定文案
                message=detail or "服务器内部错误",
                detail=detail,
            ).model_dump(),
        )

    # 注册路由
    app.include_router(api_router, prefix="/api/v1")
    # /info 挂在根路径（不带 /api/v1 前缀），符合 Serviced-MP 规范第四节
    app.include_router(info_router)

    return app


# uvicorn 入口
app = create_app()  # OCR 引擎配置功能已就绪


if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
