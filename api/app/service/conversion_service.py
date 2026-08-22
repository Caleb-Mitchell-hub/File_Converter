"""业务层：包装 doc_converter，提供异步转换能力。

所有 doc_converter 调用都通过 ``asyncio.to_thread`` 放到线程池执行，
避免阻塞 FastAPI 事件循环。
"""

from __future__ import annotations

import asyncio
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from app.config import get_settings
from app.models.enums import ConversionType, OcrEngine, TaskStatus
from app.models.schemas import FileResult
from app.utils.file_utils import (
    ensure_dir,
    generate_task_id,
    is_extension_allowed,
    safe_delete,
    safe_filename,
    secure_unique_name,
)
from app.utils.logger import get_logger

# doc_converter 需要仓库根目录在 sys.path 中（懒加载时注入）
import sys as _sys
from pathlib import Path as _Path
_root = _Path(__file__).resolve().parents[3]
if str(_root) not in _sys.path:
    _sys.path.insert(0, str(_root))

from doc_converter.core.base import ConversionError  # type: ignore[import-not-found]

# 延迟导入避免启动开销
_converter_module = None


def _get_converter():
    """懒加载 doc_converter 包（sys.path 已在模块顶层注入仓库根目录）。"""
    global _converter_module
    if _converter_module is None:
        from doc_converter import Converter
        _converter_module = Converter
    return _converter_module


class ConversionService:
    """转换服务：单文件 + 批量。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.log = get_logger("service.ConversionService")
        # 触发 doc_converter 加载（注册所有路由）
        try:
            self._converter_cls = _get_converter()
            self._supported_pairs = self._converter_cls.supported()
            self.log.info(
                "doc_converter 已加载，支持 %d 个转换组合", len(self._supported_pairs)
            )
        except Exception as exc:
            self.log.exception("加载 doc_converter 失败: %s", exc)
            raise

    # ------------------------------------------------------------------ #
    # 单文件
    # ------------------------------------------------------------------ #
    async def convert_single(
        self,
        source_path: Path,
        conversion_type: ConversionType,
        target_filename: Optional[str] = None,
        dpi: Optional[int] = None,
        jpg_quality: Optional[int] = None,
        overwrite: bool = False,
        on_progress: Optional[Callable[[int, int], None]] = None,
        output_dir: Optional[Path] = None,
    ) -> Tuple[Path, FileResult]:
        """转换单个文件。

        Args:
            source_path: 已保存到本地的源文件。
            conversion_type: 转换类型。
            target_filename: 自定义输出文件名（可选）。
            dpi / jpg_quality: 透传渲染参数。
            overwrite: 覆盖开关。
            on_progress: 进度回调 ``(processed, total)``，本接口中 ``total==1``。
                **二级进度**（如 PDF → DOCX 的页级进度）通过
                ``on_page_progress(processed, total)`` 单独发出。

        Returns:
            ``(output_path, FileResult)``
        """
        log = self.log
        log.info("开始单文件转换: %s -> %s", source_path, conversion_type)

        # 校验扩展名
        if not is_extension_allowed(source_path.name, [conversion_type.source_ext_dot]):
            msg = (
                f"源文件扩展名 {source_path.suffix} 与转换类型 "
                f"{conversion_type} 要求的 {conversion_type.source_ext_dot} 不匹配"
            )
            log.error(msg)
            result = FileResult(
                source_filename=source_path.name,
                success=False,
                message=msg,
            )
            raise ConversionValidationError(msg, result)

        # 构造目标路径（支持用户隔离目录）
        target_dir = ensure_dir(output_dir or self.settings.output_dir)
        if target_filename:
            out_name = safe_filename(target_filename)
        else:
            out_name = (
                source_path.stem
                + "_"
                + generate_task_id()[:6]
                + conversion_type.target_ext
            )
        target_path = target_dir / out_name

        # 文件级进度起始
        if on_progress:
            try:
                on_progress(0, 1)
            except Exception:  # noqa: BLE001
                log.warning("on_progress 回调异常 (file start)", exc_info=True)

        # 实际转换（线程池执行）
        try:
            actual = await asyncio.to_thread(
                self._do_convert,
                source_path,
                target_path,
                conversion_type,
                dpi,
                jpg_quality,
                overwrite,
                on_progress,
            )
        except Exception as exc:
            log.exception("转换失败: %s", source_path.name)
            result = FileResult(
                source_filename=source_path.name,
                success=False,
                message=str(exc),
            )
            # 失败也要把进度推到 100%，避免前端卡住
            if on_progress:
                try:
                    on_progress(1, 1)
                except Exception:  # noqa: BLE001
                    pass
            raise ConversionExecutionError(str(exc), result) from exc

        if on_progress:
            try:
                on_progress(1, 1)
            except Exception:  # noqa: BLE001
                log.warning("on_progress 回调异常 (file done)", exc_info=True)

        log.info("转换成功: %s -> %s", source_path.name, actual.name)
        return actual, FileResult(
            source_filename=source_path.name,
            output_filename=actual.name,
            success=True,
            message="ok",
        )

    def _do_convert(
        self,
        source: Path,
        target: Path,
        ctype: ConversionType,
        dpi: Optional[int],
        jpg_quality: Optional[int],
        overwrite: bool,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        kwargs: dict = {"overwrite": overwrite}
        if dpi is not None and ctype in (
            ConversionType.XLSX_TO_PNG,
            ConversionType.XLSX_TO_JPG,
            ConversionType.PDF_TO_PNG,
            ConversionType.PDF_TO_JPG,
        ):
            kwargs["dpi"] = dpi
        if jpg_quality is not None and ctype in (
            ConversionType.XLSX_TO_JPG,
            ConversionType.PDF_TO_JPG,
        ):
            kwargs["jpg_quality"] = jpg_quality

        # 对 OCR 类任务（图片 → xlsx），按配置的 OCR 引擎分发
        if ctype in (ConversionType.PNG_TO_XLSX, ConversionType.JPG_TO_XLSX):
            kwargs.pop("on_progress", None)  # OCR 转换器不使用进度回调
            engine = self.settings.ocr_engine
            converter = _resolve_ocr_converter(engine)
            try:
                return converter.convert(source, target, **kwargs)
            except ConversionError as exc:
                self.log.warning(
                    "OCR 引擎 %s 失败，回退到 Tesseract: %s", engine.value, exc
                )
                from doc_converter.converters.ocr_converter import OcrConverter
                return OcrConverter().convert(source, target, **kwargs)

        # on_progress 仅 PDF -> DOCX 真正消费；其它转换器拿到 None 不会崩。
        kwargs["on_progress"] = on_progress
        return self._converter_cls.convert(source, target, **kwargs)

    # ------------------------------------------------------------------ #
    # 批量
    # ------------------------------------------------------------------ #
    async def convert_batch(
        self,
        source_paths: List[Path],
        conversion_type: ConversionType,
        target_subdir: Optional[str] = None,
        dpi: Optional[int] = None,
        jpg_quality: Optional[int] = None,
        overwrite: bool = False,
        zip_output: bool = True,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_page_progress: Optional[Callable[[str, int, int], None]] = None,
        output_dir: Optional[Path] = None,
    ) -> Tuple[List[FileResult], Optional[Path]]:
        """批量转换。

        Args:
            on_progress: 文件级回调 ``(processed_files, total_files)``。
            on_page_progress: 页级回调 ``(source_filename, current_page, total_pages)``。
                当前仅 PDF → DOCX 真正发出；其它 converter 不会触发。

        Returns:
            ``(file_results, zip_path)``
            - ``file_results``: 每个文件的处理结果
            - ``zip_path``: 打包后的 zip 路径（zip_output=True 时）
        """
        log = self.log
        total = len(source_paths)
        log.info("开始批量转换: %d 个文件, 类型=%s", total, conversion_type)

        if total == 0:
            return [], None

        # 准备输出目录（支持用户隔离目录）
        root_dir = output_dir or self.settings.output_dir
        sub = safe_filename(target_subdir) if target_subdir else f"batch_{generate_task_id()[:8]}"
        out_dir = ensure_dir(root_dir / sub)

        results: List[FileResult] = []
        for idx, src in enumerate(source_paths, start=1):
            # 当前文件切换：清零页级进度，让前端知道我们在处理哪个文件
            if on_page_progress:
                try:
                    on_page_progress(src.name, 0, 0)
                except Exception:  # noqa: BLE001
                    log.warning("on_page_progress 回调异常", exc_info=True)

            # 把页级回调包裹成 ``(processed, total) -> None``，传给 _do_convert
            page_cb = on_page_progress

            def _page_proxy(filename: str, processed: int, total_pages: int) -> None:
                if page_cb is None:
                    return
                try:
                    page_cb(filename, processed, total_pages)
                except Exception:  # noqa: BLE001
                    log.warning("on_page_progress 回调异常", exc_info=True)

            def _on_page(processed: int, total_pages: int) -> None:
                _page_proxy(src.name, processed, total_pages)

            try:
                out_name = src.stem + "_" + generate_task_id()[:6] + conversion_type.target_ext
                out_path = out_dir / out_name

                actual = await asyncio.to_thread(
                    self._do_convert,
                    src,
                    out_path,
                    conversion_type,
                    dpi,
                    jpg_quality,
                    overwrite,
                    _on_page if on_page_progress else None,
                )
                results.append(
                    FileResult(
                        source_filename=src.name,
                        output_filename=actual.name,
                        success=True,
                        message="ok",
                    )
                )
            except Exception as exc:
                log.exception("批量任务中单文件失败: %s", src.name)
                results.append(
                    FileResult(
                        source_filename=src.name,
                        success=False,
                        message=str(exc),
                    )
                )
            if on_progress:
                try:
                    on_progress(idx, total)
                except Exception:  # noqa: BLE001
                    log.warning("on_progress 回调异常", exc_info=True)

        # 打包
        zip_path: Optional[Path] = None
        if zip_output and any(r.success for r in results):
            zip_path = out_dir.parent / f"{sub}.zip"
            await asyncio.to_thread(self._zip_outputs, out_dir, zip_path)
            log.info("批量结果已打包: %s", zip_path)

        return results, zip_path

    @staticmethod
    def _zip_outputs(folder: Path, zip_path: Path) -> None:
        """把 folder 内所有文件打包到 zip_path。"""
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in folder.iterdir():
                if f.is_file():
                    zf.write(f, arcname=f.name)


# ---------------------------------------------------------------------- #
# OCR 引擎解析
# ---------------------------------------------------------------------- #
def _resolve_ocr_converter(engine: OcrEngine):
    """按 OCR 引擎枚举返回对应的转换器实例。"""
    if engine == OcrEngine.OPENCV_HYBRID:
        from doc_converter.converters.opencv_ocr_converter import OpenCvOcrConverter
        return OpenCvOcrConverter()
    if engine == OcrEngine.QWEN_VL:
        from doc_converter.converters.qwen_ocr_converter import QwenOcrConverter
        return QwenOcrConverter()
    if engine == OcrEngine.TESSERACT:
        from doc_converter.converters.ocr_converter import OcrConverter
        return OcrConverter()
    raise ConversionError(f"未知 OCR 引擎: {engine}")


# ---------------------------------------------------------------------- #
# 自定义业务异常
# ---------------------------------------------------------------------- #
class ConversionValidationError(Exception):
    """参数校验错误（扩展名不匹配等）。"""

    def __init__(self, message: str, result: FileResult) -> None:
        super().__init__(message)
        self.result = result


class ConversionExecutionError(Exception):
    """转换执行错误（引擎层失败）。"""

    def __init__(self, message: str, result: FileResult) -> None:
        super().__init__(message)
        self.result = result
