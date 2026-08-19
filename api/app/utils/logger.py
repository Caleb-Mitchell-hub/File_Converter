"""统一日志配置。

支持：
    - 控制台输出（彩色，按级别）
    - 文件输出（按天滚动，保留 N 天）
    - uvicorn / fastapi / doc_converter 等子 logger 透传

使用::

    from app.utils.logger import get_logger
    log = get_logger(__name__)
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    retention_days: int = 30,
) -> None:
    """配置全局日志。

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）。
        log_dir: 日志文件目录，为 None 则不写文件。
        log_to_console: 是否输出到 stderr。
        log_to_file: 是否写文件。
        retention_days: 日志保留天数。
    """
    global _CONFIGURED
    if _CONFIGURED:
        # 重复调用时只更新级别
        logging.getLogger().setLevel(level)
        return

    root = logging.getLogger()
    root.setLevel(level.upper())
    # 清理已有 handler（避免重复输出）
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    if log_to_console:
        ch = logging.StreamHandler(stream=sys.stderr)
        ch.setFormatter(formatter)
        ch.setLevel(level.upper())
        root.addHandler(ch)

    if log_to_file and log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = TimedRotatingFileHandler(
            filename=str(log_dir / "app.log"),
            when="midnight",
            interval=1,
            backupCount=retention_days,
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        fh.setLevel(level.upper())
        root.addHandler(fh)

        # 单独写错误日志
        efh = TimedRotatingFileHandler(
            filename=str(log_dir / "error.log"),
            when="midnight",
            interval=1,
            backupCount=retention_days,
            encoding="utf-8",
        )
        efh.setFormatter(formatter)
        efh.setLevel(logging.ERROR)
        root.addHandler(efh)

    # 抑制过吵的第三方库日志
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取 logger，自动归属到 ``app`` 命名空间。"""
    if not name:
        return logging.getLogger("app")
    if not name.startswith("app"):
        name = f"app.{name}"
    return logging.getLogger(name)
