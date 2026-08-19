"""单文件转换示例。

本示例展示 ``Converter.convert()`` 的 6 个最常见用法，覆盖：

- Excel -> PDF
- Excel -> PNG（高清 300 DPI）
- PDF -> PNG（多页自动拆分）
- 图片 -> PDF
- Word -> PDF
- 图片 OCR -> Excel

运行前请确保：

1. 已安装基础依赖：``pip install -r requirements.txt``
2. 已准备好 ``samples/`` 目录，并放入对应的测试文件。
3. 若运行 Excel/Word -> PDF 场景，需要本机存在 LibreOffice
   （或 Windows + Microsoft Office + ``pip install pywin32 docx2pdf``）。
4. 若运行 OCR 场景，需要系统安装 Tesseract 二进制及中文/英文语言包，
   并 ``pip install pytesseract``。

可调用的所有支持组合可用 ``Converter.supported()`` 查询。
"""

from __future__ import annotations

import logging
from pathlib import Path

from doc_converter import Converter
from doc_converter.core.logger import set_level

# ---------------------------------------------------------------------------
# 调高日志详细度（DEBUG / INFO / WARNING / ERROR）
# ---------------------------------------------------------------------------
# 默认 INFO；改为 DEBUG 可以看到每个转换器的"路由"与"引擎选择"细节。
set_level(logging.INFO)

# ---------------------------------------------------------------------------
# 准备输出目录
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """依次演示 6 个常见转换场景。"""

    # ----------------------------------------------------------------- #
    # 1) Excel -> PDF
    # 引擎选择：Windows + 装了 MS Office -> pywin32（保真度最高）；
    #           其它平台 / 无 Office    -> LibreOffice headless。
    # ----------------------------------------------------------------- #
    Converter.convert("samples/report.xlsx", OUTPUT_DIR / "report.pdf")

    # ----------------------------------------------------------------- #
    # 2) Excel -> PNG（高清 300 DPI）
    # 实际链路：Excel -> 中间 PDF（LibreOffice / pywin32）-> PNG（PyMuPDF）。
    # 多页时只导出第一页；如需全页，改用 PDF -> PNG。
    # ----------------------------------------------------------------- #
    Converter.convert("samples/chart.xlsx", OUTPUT_DIR / "chart.png")

    # ----------------------------------------------------------------- #
    # 3) PDF -> PNG（多页自动拆分为 page_001.png / page_002.png ...）
    # 注意：传入的 target 是"输出目录 + 基础名"，实际产物为同名带 _page_NNN 后缀。
    # ----------------------------------------------------------------- #
    Converter.convert("samples/manual.pdf", OUTPUT_DIR / "manual_page.png")

    # ----------------------------------------------------------------- #
    # 4) 图片 -> PDF
    # 支持 png / jpg / jpeg / bmp / tiff / webp。
    # 多张图片合并为多页 PDF 请使用 ``ImageConverter.convert_many()``。
    # ----------------------------------------------------------------- #
    Converter.convert("samples/photo.png", OUTPUT_DIR / "photo.pdf")

    # ----------------------------------------------------------------- #
    # 5) Word -> PDF
    # 引擎：Windows + MS Word -> docx2pdf/pywin32；其它 -> LibreOffice。
    # ----------------------------------------------------------------- #
    Converter.convert("samples/document.docx", OUTPUT_DIR / "document.pdf")

    # ----------------------------------------------------------------- #
    # 6) 图片 OCR -> Excel
    # 依赖：tesseract 二进制 + pytesseract；默认语言 chi_sim+eng。
    # 词级 OCR 结果按 block/par/line 还原为"行 x 列"写入 Excel。
    # ----------------------------------------------------------------- #
    Converter.convert("samples/scan.png", OUTPUT_DIR / "scan.xlsx")

    # 全部完成
    print(f"完成：6 个示例已写入 {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
