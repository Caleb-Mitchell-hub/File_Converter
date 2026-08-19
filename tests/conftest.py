"""pytest 共享 fixture。

为单元测试提供临时输入 / 输出目录与常用样本文件（PNG / JPG / PDF）。
所有 fixture 都基于 pytest 内置的 :func:`tmp_path` 工厂，确保测试结束后
自动清理。

使用：

    def test_xxx(sample_png, tmp_output_dir):
        out = tmp_output_dir / "x.pdf"
        ...
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import pytest
from PIL import Image


# --------------------------------------------------------------------------- #
# 目录 fixture
# --------------------------------------------------------------------------- #
@pytest.fixture
def tmp_input_dir(tmp_path: Path) -> Path:
    """返回一个临时输入目录（自动创建）。"""
    p = tmp_path / "input"
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """返回一个临时输出目录（自动创建）。"""
    p = tmp_path / "output"
    p.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------------------- #
# 样本文件 fixture
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    """生成一个 200x200 红色 PNG。"""
    img = Image.new("RGB", (200, 200), "red")
    p = tmp_path / "sample.png"
    img.save(p, format="PNG")
    return p


@pytest.fixture
def sample_jpg(tmp_path: Path) -> Path:
    """生成一个 200x200 蓝色 JPG。"""
    img = Image.new("RGB", (200, 200), "blue")
    p = tmp_path / "sample.jpg"
    img.save(p, format="JPEG")
    return p


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """用 PyMuPDF 生成一个简单的 2 页 PDF，每页写有 "Page N / Hello World"。

    注意：不要把 ``doc.close()`` 放在 ``return`` 之前——PyMuPDF 在 close 后
    仍会保留文件本身，但若先 close 后再 return，pytest 不会出错；这里保留
    显式 close 以提示调用方及时释放资源。
    """
    p = tmp_path / "sample.pdf"
    doc = fitz.open()
    try:
        for i in range(2):
            page = doc.new_page(width=595, height=842)  # A4 尺寸（点）
            page.insert_text((50, 50), f"Page {i + 1}\nHello World")
        doc.save(str(p))
    finally:
        doc.close()
    return p
