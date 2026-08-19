"""doc_converter
~~~~~~~~~~~~~~~~

企业级文档转换工具 - 统一入口包。

支持以下转换：
    - Excel <-> PDF
    - Excel -> 图片 (PNG / JPG)
    - PDF -> 图片 (PNG / JPG)
    - 图片 -> PDF
    - Word <-> PDF
    - 图片 OCR -> Excel

最简用法：

    >>> from doc_converter import Converter
    >>> Converter.convert("input.xlsx", "output.pdf")
    True

更详细的批量 / 日志 / 高级用法请参考 ``examples`` 目录。
"""

from .core.converter import Converter
from .core.batch import BatchProcessor
from .core.logger import get_logger

__version__ = "1.0.0"
__all__ = ["Converter", "BatchProcessor", "get_logger"]
