"""doc_converter.utils
~~~~~~~~~~~~~~~~~~~~~

通用工具：路径处理、平台检测。"""

from .paths import ensure_dir, unique_output_path, split_ext
from .platform import Platform, detect_platform, has_office, has_libreoffice

__all__ = [
    "ensure_dir",
    "unique_output_path",
    "split_ext",
    "Platform",
    "detect_platform",
    "has_office",
    "has_libreoffice",
]
