"""跨平台辅助：检测 OS、判断本地 Office / LibreOffice 是否可用。"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class Platform(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    DARWIN = "darwin"
    OTHER = "other"


def detect_platform() -> Platform:
    """根据 ``sys.platform`` 推断当前平台。"""
    p = sys.platform
    if p.startswith("win"):
        return Platform.WINDOWS
    if p.startswith("linux"):
        return Platform.LINUX
    if p.startswith("darwin"):
        return Platform.DARWIN
    return Platform.OTHER


@dataclass(frozen=True)
class OfficeStatus:
    has_office: bool
    has_libreoffice: bool
    soffice_path: Optional[str]
    office_path: Optional[str]

    def preferred_engine(self) -> str:
        """根据可用性返回推荐引擎名称。"""
        if self.has_office:
            return "ms-office"
        if self.has_libreoffice:
            return "libreoffice"
        return "none"

    def install_hint(self) -> str:
        """给用户的可读安装指引。"""
        if self.has_office:
            return ""
        if self.has_libreoffice:
            return ""
        if sys.platform.startswith("win"):
            return (
                "未检测到 Microsoft Office 也不到 LibreOffice。"
                "请二选一安装：\n"
                "  1) Microsoft Office (Excel) - 推荐保真度最高\n"
                "  2) LibreOffice - 免费。安装后确保 'soffice.exe' 在 PATH 中。\n"
                "     快速安装：winget install TheDocumentFoundation.LibreOffice"
            )
        if sys.platform == "darwin":
            return (
                "请安装 LibreOffice：brew install --cask libreoffice\n"
                "或从 https://www.libreoffice.org/ 下载 .dmg"
            )
        return (
            "请安装 LibreOffice：apt install libreoffice (Debian/Ubuntu) "
            "或 yum install libreoffice (RHEL/CentOS)"
        )


def _office_executables() -> list[str]:
    """Windows + macOS 上的 Microsoft Office 可执行文件名。"""
    return [
        "soffice.exe",  # LibreOffice（误命名兼容）
        "winword.exe",
        "excel.exe",
        "powerpnt.exe",
    ]


def _windows_office_search_paths() -> list[Path]:
    """Windows 上 Microsoft Office 的常见安装位置。

    返回所有可能存在的根目录；调用方需要再拼上最终 exe 名字。
    """
    candidates: list[Path] = []
    # 1) Program Files
    for root in (r"C:\Program Files", r"C:\Program Files (x86)"):
        if not Path(root).exists():
            continue
        # Microsoft Office 2016+ 统一入口
        candidates.extend(Path(root).glob("Microsoft Office/root/Office*"))
        # Click-to-Run
        candidates.extend(Path(root).glob("Microsoft Office*/*"))
        # 旧版
        candidates.extend(Path(root).glob("Microsoft Office/Office*"))
        candidates.extend(Path(root).glob("Office*"))
        # Office 365 子目录
        candidates.extend(Path(root).glob("Microsoft 365/root/Office*"))
    return [p for p in candidates if p.is_dir()]


def _find_office_executable() -> Optional[str]:
    """在 Windows 上扫描常见路径寻找 Office 可执行文件。"""
    if not sys.platform.startswith("win"):
        return None

    # 先用 shutil.which（最快）
    for exe in _office_executables():
        path = shutil.which(exe)
        if path:
            return path

    # 再扫描常见安装目录
    for base in _windows_office_search_paths():
        for exe in ("EXCEL.EXE", "excel.exe", "WINWORD.EXE", "winword.exe"):
            cand = base / exe
            if cand.exists():
                return str(cand)
    return None


def has_office() -> bool:
    """粗略判断本机是否安装了 Microsoft Office（Windows + macOS 有效）。"""
    if _find_office_executable():
        return True
    # macOS 上检查 /Applications 下的 Microsoft Excel.app / Word.app
    if sys.platform == "darwin":
        apps = Path("/Applications")
        for name in ("Microsoft Excel.app", "Microsoft Word.app"):
            if (apps / name).exists():
                return True
    return False


def has_libreoffice() -> bool:
    """判断本机是否安装了 LibreOffice（任何平台）。"""
    if shutil.which("soffice") is not None:
        return True
    if shutil.which("libreoffice") is not None:
        return True
    # Windows 上回退到常见安装目录
    if sys.platform.startswith("win"):
        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for c in candidates:
            if Path(c).exists():
                return True
    return False


def _find_soffice() -> Optional[str]:
    """跨平台查找 soffice/libreoffice 可执行文件完整路径。"""
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    if sys.platform.startswith("win"):
        for c in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if Path(c).exists():
                return str(Path(c))
    return None


def office_status() -> OfficeStatus:
    return OfficeStatus(
        has_office=has_office(),
        has_libreoffice=has_libreoffice(),
        soffice_path=_find_soffice(),
        office_path=_find_office_executable(),
    )
