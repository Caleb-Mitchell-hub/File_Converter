"""文件相关工具函数。"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path
from typing import Optional

# Windows / macOS / Linux 共用的非法文件名字符
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(name: str, replacement: str = "_") -> str:
    """去除文件名中的非法字符。"""
    cleaned = _ILLEGAL_CHARS.sub(replacement, name).strip().rstrip(".")
    return cleaned or "untitled"


def generate_task_id() -> str:
    """生成短任务 ID。"""
    return uuid.uuid4().hex[:16]


def secure_unique_name(original_filename: str, prefix: str = "") -> str:
    """根据原始文件名生成一个安全的唯一文件名。

    Args:
        original_filename: 用户上传的原始文件名。
        prefix: 可选前缀（如任务 ID）。

    Returns:
        ``{prefix}_{uuid8}_{safe_stem}{ext}``
    """
    p = Path(original_filename)
    stem = safe_filename(p.stem)
    suffix = p.suffix.lower()
    short = uuid.uuid4().hex[:8]
    name = f"{prefix}_{short}_{stem}{suffix}" if prefix else f"{short}_{stem}{suffix}"
    return name


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在。"""
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_extension_allowed(filename: str, allowed: list[str]) -> bool:
    """判断文件扩展名是否在白名单中。"""
    return Path(filename).suffix.lower() in {e.lower() for e in allowed}


def safe_delete(path: str | Path, missing_ok: bool = True) -> None:
    """安全删除文件或目录。"""
    p = Path(path)
    if not p.exists():
        if missing_ok:
            return
        raise FileNotFoundError(f"路径不存在: {p}")
    if p.is_file():
        p.unlink()
    elif p.is_dir():
        shutil.rmtree(p)


def get_file_size_mb(path: str | Path) -> float:
    """获取文件大小（MB）。"""
    return Path(path).stat().st_size / (1024 * 1024)


def human_readable_size(size_bytes: int) -> str:
    """把字节数转成人类可读字符串。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
