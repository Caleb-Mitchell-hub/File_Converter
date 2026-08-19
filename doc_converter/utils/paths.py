"""路径相关的工具。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在；若不存在则创建。返回 ``Path``。"""
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def unique_output_path(path: str | Path) -> Path:
    """如果目标文件已存在，附加一个 ``_1``、``_2`` 后缀以避免覆盖。

    Example::

        >>> unique_output_path("out.pdf")
        PosixPath('out.pdf')           # 不存在
        >>> unique_output_path("out.pdf")  # 已存在
        PosixPath('out_1.pdf')
    """
    p = Path(path).expanduser()
    if not p.exists():
        return p
    stem, suffix, parent = p.stem, p.suffix, p.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1
        if i > 9999:  # 防止死循环
            return parent / f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"


def split_ext(path: str | Path) -> tuple[str, str]:
    """分解扩展名与剩余部分。

    Returns:
        (stem, ext) 其中 ext 始终以 ``.`` 开头且为小写。
    """
    p = Path(path)
    return p.stem, p.suffix.lower()


def safe_filename(name: str, replacement: str = "_") -> str:
    """去掉文件名中的非法字符。"""
    illegal = '<>:"/\\|?*'
    for ch in illegal:
        name = name.replace(ch, replacement)
    return name.strip().rstrip(".") or "untitled"
