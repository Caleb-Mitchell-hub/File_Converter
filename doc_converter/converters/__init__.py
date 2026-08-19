"""doc_converter.converters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

所有具体转换器实现。

- :class:`ExcelConverter`     Excel <-> PDF, Excel -> 图片
- :class:`PdfConverter`        PDF -> 图片, PDF -> Excel
- :class:`ImageConverter`      图片 -> PDF
- :class:`WordConverter`       Word <-> PDF
- :class:`OcrConverter`        图片 OCR -> Excel (本地 Tesseract)
- :class:`QwenOcrConverter`    图片 OCR -> Excel (云端 Qwen-VL，支持合并单元格)

每个转换器会在被 import 时自动通过模块底部的 ``Registry.register`` 注册到全局路由。

注意：``QwenOcrConverter`` 与 ``OcrConverter`` 共享 ``(png/jpg/... -> xlsx)``
路由，import 顺序决定了 ``Registry.resolve`` 命中谁 ——
**QwenOcrConverter 必须早于 OcrConverter**，让云端模型优先。
"""

from .excel_converter import ExcelConverter
from .pdf_converter import PdfConverter
from .image_converter import ImageConverter
from .word_converter import WordConverter
from .qwen_ocr_converter import QwenOcrConverter     # 优先：云端大模型（OCR 准）
from .opencv_ocr_converter import OpenCvOcrConverter  # 次选：本地几何（合并准，OCR 弱）
from .ocr_converter import OcrConverter              # 最后：本地 Tesseract

__all__ = [
    "ExcelConverter",
    "PdfConverter",
    "ImageConverter",
    "WordConverter",
    "OcrConverter",
    "QwenOcrConverter",
    "OpenCvOcrConverter",
]
