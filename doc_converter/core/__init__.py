"""doc_converter.core
~~~~~~~~~~~~~~~~~~~

核心框架模块：抽象基类、注册器、门面、批量处理、日志、路径与平台工具。

对外暴露的稳定 API：
    - :class:`BaseConverter`
    - :class:`Converter`  （统一入口门面）
    - :class:`BatchProcessor`
    - :func:`get_logger`
"""

from .base import BaseConverter, ConversionError
from .converter import Converter
from .registry import Registry
from .batch import BatchProcessor, BatchResult
from .logger import get_logger

__all__ = [
    "BaseConverter",
    "ConversionError",
    "Converter",
    "Registry",
    "BatchProcessor",
    "BatchResult",
    "get_logger",
]
