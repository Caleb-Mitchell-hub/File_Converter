"""抽象基类与异常类型。

所有具体转换器都必须继承 :class:`BaseConverter` 并实现 :meth:`convert`。
``supported_pairs`` 用来声明本转换器能够处理的 (src_ext, dst_ext) 组合，
便于 ``Registry`` 自动路由。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Iterable, Tuple

PathLike = str | Path


class ConversionError(Exception):
    """转换过程中出现的任何可恢复错误。"""


@dataclass(frozen=True)
class ConversionResult:
    """单次转换的结果对象。

    Attributes:
        source: 源文件路径。
        target: 输出文件路径（实际写入位置）。
        success: 是否成功。
        message: 人类可读的状态描述。
    """

    source: Path
    target: Path
    success: bool
    message: str = ""

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return self.success


class BaseConverter(ABC):
    """所有具体转换器的抽象基类。

    子类必须实现 :meth:`convert`。每个子类应通过类属性
    ``supported_pairs`` 声明自己支持的扩展名组合，例如：

        supported_pairs: ClassVar[Tuple[Tuple[str, str], ...]] = (
            (".xlsx", ".pdf"),
            (".xls",  ".pdf"),
        )
    """

    #: 当前转换器名称（用于日志和注册）。
    name: ClassVar[str] = "BaseConverter"

    #: 支持的 (src_ext, dst_ext) 组合，扩展名统一小写、含点。
    supported_pairs: ClassVar[Tuple[Tuple[str, str], ...]] = ()

    @abstractmethod
    def convert(self, source: PathLike, target: PathLike) -> Path:
        """执行转换。

        Args:
            source: 源文件路径。
            target: 输出文件路径。

        Returns:
            实际写入的目标路径。

        Raises:
            ConversionError: 转换失败时抛出。
        """

    # ------------------------------------------------------------------ #
    # 辅助方法
    # ------------------------------------------------------------------ #
    def supports(self, src_ext: str, dst_ext: str) -> bool:
        """判断当前转换器是否支持给定的扩展名组合。"""
        src_ext = src_ext.lower()
        dst_ext = dst_ext.lower()
        return (src_ext, dst_ext) in {tuple(p) for p in self.supported_pairs}

    @staticmethod
    def _resolve_paths(source: PathLike, target: PathLike) -> Tuple[Path, Path]:
        """统一把 ``str``/``Path`` 转成绝对 ``Path`` 对象。"""
        src = Path(source).expanduser().resolve()
        dst = Path(target).expanduser()
        if not src.exists():
            raise ConversionError(f"源文件不存在: {src}")
        return src, dst

    @staticmethod
    def _check_pair_supported(
        pairs: Iterable[Tuple[str, str]], src_ext: str, dst_ext: str
    ) -> None:
        """断言给定的扩展名组合在 ``pairs`` 中，否则抛出 ``ConversionError``。"""
        norm = {(s.lower(), d.lower()) for s, d in pairs}
        if (src_ext.lower(), dst_ext.lower()) not in norm:
            raise ConversionError(
                f"不支持的转换: {src_ext} -> {dst_ext}。"
                f"已支持: {sorted(norm)}"
            )
