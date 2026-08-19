"""服务自描述端点 (``GET /info``)。

供 Serviced-MP 管理平台通过 ``serviced.yaml`` 中的 ``health_url`` 周期性拉取。

设计依据：``docs/superpowers/specs/2026-06-15-file-hz-service-registration-design.md``
第五节（5.1 / 5.2）。

要点：
    - 路径挂在 FastAPI 根路径（不带 ``/api/v1`` 前缀），保持与规范字面要求一致
    - ``include_in_schema=False`` 不让 ``/info`` 出现在 ``/docs`` 的 OpenAPI 文档中
    - **永远返回 HTTP 200**：内部异常被 ``try/except`` 捕获后回退到
      ``{"status": "error", "pid": null, "urls": []}``，让管理平台区分
      "端点不可达" 与 "端点可达但服务异常"
"""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/info", include_in_schema=False)
def get_info() -> dict:
    """服务自描述端点。

    Returns:
        规范第四节规定的 JSON：``status``、``pid``、``urls``。
        任何内部异常都回退为 ``{"status": "error", "pid": null, "urls": []}``，
        同时保持 HTTP 200。
    """
    try:
        return {
            "status": "running",
            "pid": os.getpid(),
            "urls": [
                {"name": "后端根地址", "url": "http://localhost:8000"},
                {"name": "Swagger 文档", "url": "http://localhost:8000/docs"},
                {"name": "REST API", "url": "http://localhost:8000/api/v1"},
                {"name": "前端 Web 界面", "url": "http://localhost:5213"},
            ],
        }
    except Exception:  # pragma: no cover - 防御性兜底
        return {"status": "error", "pid": None, "urls": []}
