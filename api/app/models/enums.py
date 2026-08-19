"""枚举类型定义。"""

from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    """转换任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"  # 批量转换时部分成功


class OcrEngine(str, Enum):
    """OCR 引擎选择。

    - ``opencv_hybrid``: OpenCV 几何检测 + Qwen-VL 云端 OCR（默认），适合带边框表格
    - ``qwen_vl``: 纯 Qwen-VL 云端 OCR，适合无线表格
    - ``tesseract``: 纯本地 Tesseract OCR，无需网络
    """

    OPENCV_HYBRID = "opencv_hybrid"
    QWEN_VL = "qwen_vl"
    TESSERACT = "tesseract"


class ConversionType(str, Enum):
    """支持的转换类型。

    每种类型对应一对 (源扩展名, 目标扩展名)。
    用户通过此枚举指定转换方向，避免歧义。
    """

    # Excel 系列
    XLSX_TO_PDF = "xlsx_to_pdf"
    XLSX_TO_PNG = "xlsx_to_png"
    XLSX_TO_JPG = "xlsx_to_jpg"
    PDF_TO_XLSX = "pdf_to_xlsx"

    # Word 系列
    DOCX_TO_PDF = "docx_to_pdf"
    PDF_TO_DOCX = "pdf_to_docx"

    # PDF/图片
    PDF_TO_PNG = "pdf_to_png"
    PDF_TO_JPG = "pdf_to_jpg"

    # 图片系列
    PNG_TO_PDF = "png_to_pdf"
    JPG_TO_PDF = "jpg_to_pdf"
    JPEG_TO_PDF = "jpeg_to_pdf"

    # OCR
    PNG_TO_XLSX = "png_to_xlsx"  # OCR
    JPG_TO_XLSX = "jpg_to_xlsx"  # OCR

    @property
    def source_ext(self) -> str:
        return self.value.split("_to_")[0].replace("_xlsx", "")

    @property
    def target_ext(self) -> str:
        return "." + self.value.split("_to_")[1]

    @property
    def source_ext_dot(self) -> str:
        return "." + self.source_ext
