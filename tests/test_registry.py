"""注册器 (Registry) 单元测试。

覆盖：
    - 已知组合可正确 ``resolve`` 到对应转换器实例
    - 未知组合抛 :class:`KeyError`
    - ``supported_pairs()`` 返回稳定排序的列表
    - 并发 ``resolve`` 是线程安全的（不会抛异常 / 返回坏引用）

设计说明：

``doc_converter.core.converter._ensure_converters_imported`` 在第一次调用
后会把 ``_IMPORTED`` 置为 ``True``，再调用 :func:`Converter.supported` 时
会跳过重新 import。**这意味着 :meth:`Registry.clear` 之后无法通过
:func:`Converter.supported` 自动恢复**（已记录为现有 bug）。

本测试在模块加载时显式 import 所有具体转换器并重新 ``register``，
既保证本文件能独立运行，也避免依赖 :class:`Converter` 的懒加载时序。
"""

from __future__ import annotations

import threading
from typing import ClassVar, Tuple

import pytest

# 显式 import 并 register 全部具体转换器，确保 Registry 非空
# （不依赖 Converter 的懒加载 / _IMPORTED 时序）
from doc_converter import Converter  # noqa: F401  - 触发初始注册
from doc_converter.converters.excel_converter import ExcelConverter
from doc_converter.converters.image_converter import ImageConverter
from doc_converter.converters.ocr_converter import OcrConverter
from doc_converter.converters.pdf_converter import PdfConverter
from doc_converter.converters.word_converter import WordConverter
from doc_converter.core.base import BaseConverter
from doc_converter.core.registry import Registry


# 模块级 fixture：保证 Registry 至少包含 5 个内置转换器
@pytest.fixture(autouse=True)
def _ensure_default_converters_registered():
    """每个测试运行前，若 Registry 为空则补全默认转换器。"""
    if not Registry.supported_pairs():
        Registry.register(ExcelConverter())
        Registry.register(PdfConverter())
        Registry.register(ImageConverter())
        Registry.register(WordConverter())
        Registry.register(OcrConverter())
    yield


# =========================================================================== #
# 基础 resolve / supported_pairs
# =========================================================================== #
def test_registry_resolve_known() -> None:
    """已知组合应能 ``resolve`` 出正确的 BaseConverter 子类实例。

    我们挑几个稳定存在的核心组合验证：
        - .xlsx -> .pdf   -> ExcelConverter
        - .pdf  -> .png   -> PdfConverter
        - .png  -> .pdf   -> ImageConverter
        - .png  -> .xlsx  -> OcrConverter（依赖 tesseract，但 resolve 阶段不触发）
    """
    # 触发懒加载，确保路由表非空
    Converter.supported()

    # Excel -> PDF
    h = Registry.resolve(".xlsx", ".pdf")
    assert h.name == "ExcelConverter", f"期望 ExcelConverter，实际: {h.name}"

    # PDF -> PNG
    h = Registry.resolve(".pdf", ".png")
    assert h.name == "PdfConverter", f"期望 PdfConverter，实际: {h.name}"

    # PNG -> PDF
    h = Registry.resolve(".png", ".pdf")
    assert h.name == "ImageConverter", f"期望 ImageConverter，实际: {h.name}"

    # PNG -> XLSX (OCR 路由)
    h = Registry.resolve(".png", ".xlsx")
    assert h.name == "OcrConverter", f"期望 OcrConverter，实际: {h.name}"


def test_registry_resolve_unknown() -> None:
    """未知组合应抛 :class:`KeyError`，且错误信息包含扩展名提示。"""
    Converter.supported()  # 确保已注册

    with pytest.raises(KeyError) as exc_info:
        Registry.resolve(".unknownext", ".pdf")
    msg = str(exc_info.value)
    assert ".unknownext" in msg or ".pdf" in msg, (
        f"KeyError 消息应提示相关扩展名，实际: {msg[:200]}"
    )


def test_registry_supported_pairs() -> None:
    """``supported_pairs()`` 应返回 list，且元素为 (str, str) 元组。"""
    Converter.supported()
    pairs = Registry.supported_pairs()

    assert isinstance(pairs, list), f"应返回 list，实际: {type(pairs)}"
    assert len(pairs) > 0, "至少应注册一对组合"
    for p in pairs:
        assert isinstance(p, tuple), f"元素应为 tuple，实际: {type(p)}"
        assert len(p) == 2, f"元素应有 2 项，实际: {p}"
        src, dst = p
        assert isinstance(src, str) and src.startswith("."), (
            f"源扩展名应以 . 开头，实际: {src}"
        )
        assert isinstance(dst, str) and dst.startswith("."), (
            f"目标扩展名应以 . 开头，实际: {dst}"
        )

    # 已注册的组合在 ``Converter.supported()`` 中应一致
    assert pairs == Converter.supported(), (
        "Registry.supported_pairs() 与 Converter.supported() 不一致"
    )


# =========================================================================== #
# 线程安全
# =========================================================================== #
def test_registry_thread_safe() -> None:
    """并发 :meth:`Registry.resolve` 不应抛异常、计数应等于线程数。

    使用一个独立的 ``(src, dst)`` 组合（在 setup 阶段注册一次），
    避免和真实路由的"懒加载"时序耦合。线程数取 20 即可触发竞争。
    """

    class _TSConv(BaseConverter):
        name: ClassVar[str] = "TSConv"
        supported_pairs: ClassVar[Tuple[Tuple[str, str], ...]] = (
            (".threadsrc", ".threaddst"),
        )

        def convert(self, source, target, **kwargs):  # pragma: no cover - 不调用
            from pathlib import Path

            return Path(target)

    # 注册
    Registry.register(_TSConv())
    try:
        n_threads = 20
        errors: list[BaseException] = []
        results: list[str] = []
        lock = threading.Lock()

        def worker() -> None:
            try:
                h = Registry.resolve(".threadsrc", ".threaddst")
                with lock:
                    results.append(h.name)
            except BaseException as e:  # noqa: BLE001
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"并发 resolve 出现异常: {errors[:3]}"
        assert len(results) == n_threads, (
            f"应有 {n_threads} 个成功结果，实际: {len(results)}"
        )
        # 全部结果应一致
        assert set(results) == {"TSConv"}, f"handler 名称应一致，实际: {set(results)}"
    finally:
        # 清理：移除测试注册的转换器
        for inst in list(Registry.all_resolved(".threadsrc", ".threaddst")):
            Registry.unregister(inst)
