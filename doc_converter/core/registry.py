"""全局转换器注册表。

使用示例::

    from doc_converter.core.registry import Registry
    from doc_converter.converters.excel_converter import ExcelConverter

    Registry.register(ExcelConverter())
    handler = Registry.resolve(".xlsx", ".pdf")

线程安全：通过 ``threading.Lock`` 保护 ``_registry`` 字典。
"""

from __future__ import annotations

import threading
from typing import Dict, List, Tuple

from .base import BaseConverter


class Registry:
    """单例风格的注册表（实际通过类方法访问）。

    内部数据结构::

        _registry: Dict[Tuple[str, str], List[BaseConverter]]
            key   = (源扩展名, 目标扩展名)  小写、含点
            value = 可处理该组合的转换器列表（按注册顺序）
    """

    _registry: Dict[Tuple[str, str], List[BaseConverter]] = {}
    _lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # 注册 / 注销
    # ------------------------------------------------------------------ #
    @classmethod
    def register(cls, converter: BaseConverter) -> None:
        """注册一个转换器实例。

        会把该转换器声明的 ``supported_pairs`` 中的每一对都加入路由表。
        """
        if not isinstance(converter, BaseConverter):
            raise TypeError("只能注册 BaseConverter 的子类实例")

        with cls._lock:
            for pair in converter.supported_pairs:
                src, dst = pair[0].lower(), pair[1].lower()
                cls._registry.setdefault((src, dst), []).append(converter)

    @classmethod
    def unregister(cls, converter: BaseConverter) -> None:
        """从路由表中移除某个转换器实例。"""
        with cls._lock:
            for key, handlers in list(cls._registry.items()):
                cls._registry[key] = [h for h in handlers if h is not converter]
                if not cls._registry[key]:
                    del cls._registry[key]

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    @classmethod
    def resolve(cls, src_ext: str, dst_ext: str) -> BaseConverter:
        """根据扩展名返回第一个匹配的转换器。

        Raises:
            KeyError: 没有任何注册器支持该组合。
        """
        with cls._lock:
            handlers = cls._registry.get((src_ext.lower(), dst_ext.lower()))
            if not handlers:
                raise KeyError(
                    f"没有注册处理 {src_ext} -> {dst_ext} 的转换器。"
                    f"已注册: {sorted(cls._registry.keys())}"
                )
            return handlers[0]

    @classmethod
    def all_resolved(cls, src_ext: str, dst_ext: str) -> List[BaseConverter]:
        """返回所有能处理该组合的转换器（按注册顺序）。"""
        with cls._lock:
            return list(cls._registry.get((src_ext.lower(), dst_ext.lower()), []))

    @classmethod
    def supported_pairs(cls) -> List[Tuple[str, str]]:
        """列出已注册的全部 (src, dst) 组合。"""
        with cls._lock:
            return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:  # pragma: no cover - 测试用
        """清空注册表，主要用于单元测试。"""
        with cls._lock:
            cls._registry.clear()
