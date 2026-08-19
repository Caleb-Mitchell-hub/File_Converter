"""统一入口 :class:`Converter`。

设计目标：
    1. 对外只暴露 ``Converter.convert(source, target)`` 一个简单方法。
    2. 内部通过 :class:`Registry` 自动找到匹配的转换器。
    3. 失败抛出 :class:`ConversionError`，绝不静默吞掉异常。
    4. 转换成功后返回实际写入的目标路径。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .base import BaseConverter, ConversionError, ConversionResult
from .logger import get_logger
from .registry import Registry

# 触发 import-time 注册：
#  第一次使用 Converter 时，import 所有具体转换器，把它们加入 Registry。
#  为避免在 base 包里形成循环 import，放在这里 import 是安全的。
#
#  设计要点：不在模块级缓存"已导入"标志。
#  Python 自身的 import 缓存已经保证模块体只执行一次；
#  此处仍然显式实例化并 ``Registry.register``，以同时支持
#  1) import 阶段的 ``Registry.register`` 调用（自动注册路径）
#  2) ``Registry.clear()`` 之后的恢复（手动重新注册）
def _ensure_converters_imported() -> None:
    """确保所有具体转换器已加载到注册表。

    若注册表为空（可能刚被 ``Registry.clear()`` 清空），则重新实例化并注册。
    否则视为已就绪，直接返回。

    顺序很重要：
    - ``QwenOcrConverter`` 在 ``OcrConverter`` **之前**注册，
      因为两者都声明 ``(png, xlsx)`` 等 OCR 路由，
      ``Registry.resolve`` 返回第一个匹配项，必须让云端大模型优先。
    """
    from ..converters import (  # noqa: WPS433 - intentional late import
        ExcelConverter,
        ImageConverter,
        OcrConverter,
        OpenCvOcrConverter,
        PdfConverter,
        QwenOcrConverter,
        WordConverter,
    )

    # 仅在注册表为空时重新注册；这样既避免了无意义的重复注册，
    # 又能在测试或外部清空注册表后自动恢复路由。
    if not Registry.supported_pairs():
        # 顺序：Qwen-VL 云端 > OpenCV 几何检测 > 本地 Tesseract。
        # 三个 converter 共享 (png/jpg/... -> xlsx) 路由，
        # Registry.resolve 返回第一个匹配项，Qwen-VL 优先（OCR 文字识别质量高）。
        ordered = (
            ExcelConverter,
            PdfConverter,
            ImageConverter,
            WordConverter,
            QwenOcrConverter,
            OpenCvOcrConverter,
            OcrConverter,
        )
        for cls in ordered:
            Registry.register(cls())


class Converter:
    """统一转换门面。

    Example::

        from doc_converter import Converter
        Converter.convert("a.xlsx", "a.pdf")
    """

    _log = get_logger("core.Converter")

    # ------------------------------------------------------------------ #
    # 主入口
    # ------------------------------------------------------------------ #
    @classmethod
    def convert(
        cls,
        source: str | Path,
        target: str | Path,
        *,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> Path:
        """把 ``source`` 转换为 ``target``。

        Args:
            source: 源文件路径。
            target: 输出文件路径。
            overwrite: 是否允许覆盖已存在的目标文件。默认 ``False``。
            **kwargs: 透传给具体转换器的扩展参数。

        Returns:
            实际写入的目标路径。

        Raises:
            ConversionError: 不支持的转换、源文件缺失或写入失败。
        """
        _ensure_converters_imported()

        src = Path(source).expanduser()
        dst = Path(target).expanduser()

        src_ext = src.suffix.lower()
        dst_ext = dst.suffix.lower()

        # 自动推断扩展名：调用方只给了目录
        if dst.is_dir() or not dst_ext:
            raise ConversionError(
                f"目标必须是带扩展名的文件路径，不能是目录: {target}"
            )

        # 先做格式校验（即使源文件还不存在），让"格式不支持"错误优先于"文件不存在"
        try:
            Registry.resolve(src_ext, dst_ext)
        except KeyError as exc:
            raise ConversionError(str(exc)) from exc

        # 格式合法后再检查源文件是否存在
        if not src.exists():
            raise ConversionError(f"源文件不存在: {src}")

        if dst.exists() and not overwrite:
            cls._log.warning("目标已存在且未设置 overwrite=True，将跳过: %s", dst)
            return dst

        # 确保父目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)

        # 上面已经提前 resolve 过一次（用于错误信息），这里直接复用结果
        handler = Registry.resolve(src_ext, dst_ext)
        cls._log.info("路由: %s -> %s, 使用 %s", src_ext, dst_ext, handler.name)
        return handler.convert(src, dst, **kwargs)

    # ------------------------------------------------------------------ #
    # 辅助 / 查询
    # ------------------------------------------------------------------ #
    @classmethod
    def supported(cls) -> list[tuple[str, str]]:
        """列出当前已注册的所有支持组合。"""
        _ensure_converters_imported()
        return Registry.supported_pairs()

    @classmethod
    def can_convert(cls, source: str | Path, target: str | Path) -> bool:
        """快速判断某个组合是否被支持（不会触磁盘 IO）。"""
        _ensure_converters_imported()
        src_ext = Path(source).suffix.lower()
        dst_ext = Path(target).suffix.lower()
        try:
            Registry.resolve(src_ext, dst_ext)
            return True
        except KeyError:
            return False

    @classmethod
    def batch(
        cls,
        source_dir: str | Path,
        target_dir: str | Path,
        *,
        overwrite: bool = False,
        continue_on_error: bool = True,
    ) -> list[ConversionResult]:
        """对 ``source_dir`` 下 ``Registry.supported_pairs()`` 中所有支持的文件
        批量转换，输出到 ``target_dir``。

        详见 :class:`doc_converter.core.batch.BatchProcessor`。
        """
        from .batch import BatchProcessor  # 避免循环 import

        return BatchProcessor(
            source_dir=source_dir,
            target_dir=target_dir,
            overwrite=overwrite,
            continue_on_error=continue_on_error,
        ).run()
