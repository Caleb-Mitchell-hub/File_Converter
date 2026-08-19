"""OCR 专项示例：批量识别扫描件并输出到 Excel。

本示例展示两种 OCR 用法：

1. 通过 :func:`Converter.convert` 一行代码完成单图 OCR。
2. 直接实例化 :class:`OcrConverter` 自定义 ``lang`` / ``min_confidence``
   等参数。

依赖：

- Python 包：``pip install pytesseract openpyxl``
- 系统二进制：``tesseract`` + 中文/英文语言包
  - Windows：https://github.com/UB-Mannheim/tesseract/wiki
  - macOS：``brew install tesseract tesseract-lang``
  - Linux：``sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng``

实现要点：

- 默认语言：``chi_sim+eng``（简体中文 + 英文）。
- 默认 ``min_confidence = 50``：丢弃置信度低于 50 的词，避免把噪点写入 Excel。
- 多图合并请用 ``OcrConverter.convert_many([...], "out.xlsx")``，
  每个图片会作为单独 sheet。
"""

from __future__ import annotations

from pathlib import Path

from doc_converter import Converter
from doc_converter.converters.ocr_converter import OcrConverter


def main() -> None:
    """演示两种调用方式。"""

    # ------------------------------------------------------------------ #
    # 方式 1：使用统一入口（最简）
    # ------------------------------------------------------------------ #
    # 等价于：OcrConverter(lang="chi_sim+eng", min_confidence=50).convert(...)
    Converter.convert("scan.png", "scan.xlsx")

    # ------------------------------------------------------------------ #
    # 方式 2：手动实例化以自定义参数
    # ------------------------------------------------------------------ #
    # - lang: 可改为 "eng" / "chi_tra" / "chi_sim+eng+jpn" 等
    # - min_confidence: 越低召回越多但噪点越多；越高越干净但可能漏字
    ocr = OcrConverter(
        lang="chi_sim+eng",
        min_confidence=60,
    )
    ocr.convert("scan.png", "scan_custom.xlsx")

    # ------------------------------------------------------------------ #
    # 方式 3（可选）：多图合并为同一 xlsx，每个图片一个 sheet
    # ------------------------------------------------------------------ #
    # 取消下方注释即可使用：
    #
    # ocr.convert_many(
    #     ["scan_page_1.png", "scan_page_2.png", "scan_page_3.png"],
    #     "scan_all.xlsx",
    # )

    print("OCR 转换完成，结果已写入 scan.xlsx / scan_custom.xlsx")


if __name__ == "__main__":
    main()
