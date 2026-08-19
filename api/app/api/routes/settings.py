"""OCR 设置路由。

提供：
    - ``GET  /settings/ocr``   读取当前 OCR 配置（API Key 脱敏）
    - ``PUT  /settings/ocr``   更新 OCR 配置（写入 .env）
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, status

from app.api.dependencies import settings_dep
from app.config import Settings, get_settings
from app.models.schemas import (
    APIResponse,
    OcrSettingsResponse,
    OcrSettingsUpdate,
)
from app.utils.logger import get_logger

router = APIRouter(tags=["settings"])
log = get_logger("api.routes.settings")

# .env 文件位置（与 config.py 中的 BASE_DIR 对应）
_ENV_PATH = Path(__file__).resolve().parent.parent.parent.parent / ".env"


def _mask_api_key(key: str) -> str:
    """对 API Key 脱敏：长度 > 4 时显示 ``***`` + 末 4 位，否则显示 ``****``。"""
    if len(key) > 4:
        return "***" + key[-4:]
    return "****"


def _write_env_updates(updates: dict[str, str]) -> None:
    """将更新写回 .env 文件。

    对于每个 key，若文件中已有该行则替换，否则在末尾追加。
    """
    if not _ENV_PATH.exists():
        log.warning(".env 文件不存在: %s", _ENV_PATH)
        return

    content = _ENV_PATH.read_text(encoding="utf-8")

    for key, value in updates.items():
        line = f"{key}={value}"
        pattern = re.compile(rf"^{key}=.*$", flags=re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(line, content)
        else:
            if not content.endswith("\n"):
                content += "\n"
            content += line + "\n"

    _ENV_PATH.write_text(content, encoding="utf-8")
    log.info("已更新 .env 文件: %s", list(updates.keys()))


# ---------------------------------------------------------------------- #
# GET /settings/ocr
# ---------------------------------------------------------------------- #
@router.get(
    "/ocr",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="读取 OCR 设置",
    description="返回当前 OCR 引擎配置，API Key 已脱敏处理。",
)
async def get_ocr_settings(
    settings: Settings = Depends(settings_dep),
) -> APIResponse:
    """读取当前 OCR 配置。

    Returns:
        ``APIResponse`` 包装的 ``OcrSettingsResponse``。
    """
    resp = OcrSettingsResponse(
        engine=settings.ocr_engine.value,
        qwen_api_key=_mask_api_key(settings.qwen_api_key),
        qwen_base_url=settings.qwen_base_url,
        qwen_model=settings.qwen_model,
        qwen_timeout=settings.qwen_timeout,
    )
    return APIResponse(code=0, message="ok", data=resp.model_dump())


# ---------------------------------------------------------------------- #
# PUT /settings/ocr
# ---------------------------------------------------------------------- #
@router.put(
    "/ocr",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="更新 OCR 设置",
    description="部分更新 OCR 配置，同时持久化到 .env 文件。",
)
async def update_ocr_settings(
    body: OcrSettingsUpdate,
    settings: Settings = Depends(settings_dep),
) -> APIResponse:
    """更新 OCR 配置。

    仅更新请求中提供的字段；未提供的字段保持不变。
    更新后的值会同步写入项目根目录的 ``.env`` 文件。
    """
    from app.models.enums import OcrEngine

    env_updates: dict[str, str] = {}

    # engine
    if body.engine is not None:
        try:
            settings.ocr_engine = OcrEngine(body.engine)
        except ValueError:
            valid = [e.value for e in OcrEngine]
            return APIResponse(
                code=400,
                message=f"无效的 OCR 引擎: {body.engine}，有效值: {valid}",
            )
        env_updates["OCR_ENGINE"] = body.engine

    # qwen_api_key
    if body.qwen_api_key is not None:
        settings.qwen_api_key = body.qwen_api_key
        env_updates["QWEN_API_KEY"] = body.qwen_api_key

    # qwen_base_url
    if body.qwen_base_url is not None:
        settings.qwen_base_url = body.qwen_base_url
        env_updates["QWEN_BASE_URL"] = body.qwen_base_url

    # qwen_model
    if body.qwen_model is not None:
        settings.qwen_model = body.qwen_model
        env_updates["QWEN_MODEL"] = body.qwen_model

    # qwen_timeout
    if body.qwen_timeout is not None:
        settings.qwen_timeout = body.qwen_timeout
        env_updates["QWEN_TIMEOUT"] = str(body.qwen_timeout)

    # 持久化到 .env
    if env_updates:
        _write_env_updates(env_updates)

    # 返回更新后的配置
    current = get_settings()
    resp = OcrSettingsResponse(
        engine=current.ocr_engine.value,
        qwen_api_key=_mask_api_key(current.qwen_api_key),
        qwen_base_url=current.qwen_base_url,
        qwen_model=current.qwen_model,
        qwen_timeout=current.qwen_timeout,
    )
    return APIResponse(code=0, message="ok", data=resp.model_dump())
