"""图片 -> PDF 转换器。

支持的输入格式: ``.png`` / ``.jpg`` / ``.jpeg`` / ``.bmp`` / ``.tiff`` / ``.webp``
输出格式: ``.pdf``

主要能力:
    - 单张图片转换为单页 PDF。
    - 多张图片按顺序合并为多页 PDF（通过 :meth:`ImageConverter.convert_many`）。

实现策略:
    - 使用 Pillow (PIL) 加载图片，统一转换为 ``RGB`` 模式（PDF 不支持 alpha 通道）。
    - 多图合并借助 Pillow ``Image.save(..., save_all=True, append_images=rest)``。
    - 写入 PDF 时设置 ``resolution=dpi`` 元数据（默认 300 DPI，适合打印）。
    - 通过 :class:`doc_converter.core.registry.Registry` 在模块导入时自动注册。
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Iterable, List, Tuple

from PIL import Image, UnidentifiedImageError

from ..core.base import BaseConverter, ConversionError, PathLike
from ..core.logger import get_logger
from ..core.registry import Registry
from ..utils.paths import ensure_dir, unique_output_path


class ImageConverter(BaseConverter):
    """图片到 PDF 的转换器。

    Examples:
        单文件::

            converter = ImageConverter()
            converter.convert("input.png", "output.pdf")

        多文件合并::

            converter.convert_many(
                ["page1.png", "page2.png"],
                "merged.pdf",
            )
    """

    name: ClassVar[str] = "ImageConverter"
    supported_pairs: ClassVar[Tuple[Tuple[str, str], ...]] = (
        (".png", ".pdf"),
        (".jpg", ".pdf"),
        (".jpeg", ".pdf"),
        (".bmp", ".pdf"),
        (".tiff", ".pdf"),
        (".webp", ".pdf"),
    )

    _log = get_logger("converters.image")

    def __init__(self, *, dpi: int = 300, **kwargs: object) -> None:
        """初始化图片转换器。

        Args:
            dpi: 写入 PDF 时使用的 DPI 元数据。默认 300。
            **kwargs: 预留扩展参数（当前未使用）。
        """
        if dpi <= 0:
            raise ValueError(f"dpi 必须为正整数，收到: {dpi}")
        self.dpi: int = int(dpi)

    # ------------------------------------------------------------------ #
    # 公开 API
    # ------------------------------------------------------------------ #
    def convert(
        self,
        source: PathLike,
        target: PathLike,
        **kwargs: object,
    ) -> Path:
        """将单张图片转换为 PDF。

        Args:
            source: 源图片路径。
            target: 输出 PDF 路径。
            **kwargs: 支持 ``dpi``、``overwrite`` 覆盖默认设置。

        Returns:
            实际写入的 PDF 路径。

        Raises:
            ConversionError: 源文件不存在、格式不支持或写入失败。
        """
        src, dst = self._resolve_paths(source, target)
        self._check_pair_supported(self.supported_pairs, src.suffix, dst.suffix)

        dpi = self._coerce_dpi(kwargs.pop("dpi", self.dpi))
        overwrite = bool(kwargs.pop("overwrite", False))

        ensure_dir(dst.parent)
        final_dst = dst if overwrite else unique_output_path(dst)

        try:
            image = self._open_as_rgb(src)
        except (FileNotFoundError, UnidentifiedImageError) as exc:
            raise ConversionError(f"无法读取图片: {src} ({exc})") from exc

        try:
            image.save(final_dst, "PDF", resolution=dpi)
        except OSError as exc:
            raise ConversionError(f"写入 PDF 失败: {final_dst} ({exc})") from exc
        finally:
            image.close()

        self._log.info("图片转 PDF 完成: %s -> %s (dpi=%d)", src, final_dst, dpi)
        return final_dst

    def convert_many(
        self,
        sources: Iterable[PathLike],
        target: PathLike,
        **kwargs: object,
    ) -> Path:
        """将多张图片合并为多页 PDF（按入参顺序）。

        Args:
            sources: 图片路径列表。
            target: 输出 PDF 路径。
            **kwargs: 支持 ``dpi``、``overwrite`` 覆盖默认设置。

        Returns:
            实际写入的 PDF 路径。

        Raises:
            ConversionError: 列表为空、任何一张图片无法读取或写入失败。
        """
        src_list: List[Path] = []
        for item in sources:
            p = Path(item).expanduser()
            if not p.exists():
                raise ConversionError(f"源文件不存在: {p}")
            src_list.append(p)

        if not src_list:
            raise ConversionError("convert_many 至少需要一张图片")

        dst = Path(target).expanduser()
        if not dst.suffix:
            raise ConversionError(f"目标文件必须包含扩展名 .pdf: {dst}")
        self._check_pair_supported(self.supported_pairs, src_list[0].suffix, dst.suffix)

        dpi = self._coerce_dpi(kwargs.pop("dpi", self.dpi))
        overwrite = bool(kwargs.pop("overwrite", False))

        ensure_dir(dst.parent)
        final_dst = dst if overwrite else unique_output_path(dst)

        images: List[Image.Image] = []
        opened_paths: List[Path] = []
        try:
            for src in src_list:
                try:
                    images.append(self._open_as_rgb(src))
                    opened_paths.append(src)
                except (FileNotFoundError, UnidentifiedImageError) as exc:
                    raise ConversionError(
                        f"无法读取图片: {src} ({exc})"
                    ) from exc

            if not images:
                raise ConversionError("没有可写入 PDF 的有效图片")

            first, *rest = images
            first.save(
                final_dst,
                "PDF",
                resolution=dpi,
                save_all=True,
                append_images=rest,
            )
        except OSError as exc:
            raise ConversionError(f"写入 PDF 失败: {final_dst} ({exc})") from exc
        finally:
            for img in images:
                try:
                    img.close()
                except Exception:  # noqa: BLE001 - 关闭时不影响主流程
                    pass

        self._log.info(
            "多图合并 PDF 完成: %d 页 -> %s (dpi=%d)",
            len(images),
            final_dst,
            dpi,
        )
        return final_dst

    # ------------------------------------------------------------------ #
    # 内部辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def _open_as_rgb(src: Path) -> Image.Image:
        """打开图片并确保为 ``RGB`` 模式（PDF 不支持 alpha）。"""
        img = Image.open(src)
        # 对包含 alpha 通道、调色板或灰度的图，统一转为 RGB
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img

    @staticmethod
    def _coerce_dpi(value: object) -> int:
        """校验并归一化 dpi 参数。"""
        try:
            dpi = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ConversionError(f"dpi 必须是整数，收到: {value!r}") from exc
        if dpi <= 0:
            raise ConversionError(f"dpi 必须为正整数，收到: {dpi}")
        return dpi


# ---------------------------------------------------------------------------
# 模块加载时自动注册到全局路由。
# ---------------------------------------------------------------------------
Registry.register(ImageConverter())
