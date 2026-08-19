"""全局运行时状态。

把 TaskManager / ConversionService 单例从 main.py 抽到独立模块，
避免 ``app.main`` 和 ``app.api.dependencies`` 之间的循环导入。
"""

from __future__ import annotations

from typing import Optional

from app.service import ConversionService, TaskManager

_task_manager: Optional[TaskManager] = None
_conversion_service: Optional[ConversionService] = None


def set_task_manager(tm: TaskManager) -> None:
    global _task_manager
    _task_manager = tm


def set_conversion_service(cs: ConversionService) -> None:
    global _conversion_service
    _conversion_service = cs


def get_task_manager() -> TaskManager:
    if _task_manager is None:
        raise RuntimeError("TaskManager 尚未初始化（lifespan 未启动）")
    return _task_manager


def get_conversion_service() -> ConversionService:
    if _conversion_service is None:
        raise RuntimeError("ConversionService 尚未初始化或初始化失败")
    return _conversion_service
