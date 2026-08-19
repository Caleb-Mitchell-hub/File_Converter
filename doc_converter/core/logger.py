"""统一的日志工具。

默认行为：
    - 日志级别 INFO
    - 输出到 stderr
    - 格式: ``[时间] [级别] [logger] 消息``

使用::

    from doc_converter.core.logger import get_logger
    log = get_logger(__name__)
    log.info("处理 %s", path)
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

_DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
_DEFAULT_LEVEL = logging.INFO

_configured = False


def _configure_root() -> None:
    """惰性配置根 logger。多次调用是安全的。"""
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    root = logging.getLogger("doc_converter")
    root.addHandler(handler)
    root.setLevel(_DEFAULT_LEVEL)
    root.propagate = False
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取一个属于 ``doc_converter`` 命名空间的 logger。

    Args:
        name: 子模块名，例如 ``"doc_converter.converters.excel"``。
            若为空字符串或 ``None``，则返回包级 logger。
    """
    _configure_root()
    if not name:
        return logging.getLogger("doc_converter")
    if not name.startswith("doc_converter"):
        name = f"doc_converter.{name}"
    return logging.getLogger(name)


def set_level(level: int) -> None:  # pragma: no cover - 简单 setter
    """修改全局日志级别，便于用户在批处理时调整详细度。"""
    _configure_root()
    logging.getLogger("doc_converter").setLevel(level)
