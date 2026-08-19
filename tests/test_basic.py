"""基础功能测试。

覆盖范围：
    - :class:`doc_converter.Converter` 的查询 / 错误路径
    - 路径工具函数 :func:`ensure_dir` / :func:`unique_output_path` / :func:`split_ext`
    - 平台检测 :func:`detect_platform`
    - :class:`ImageConverter` 的 PNG / JPG / 多图合并
    - :class:`Registry` 的 clear / 重复注册

注意：

- OCR 相关的测试使用 :func:`pytest.importorskip` 与 tesseract 二进制
  探测双重保护，没有环境时自动 skip 而非 fail。
- Excel / Word -> PDF 的端到端测试依赖 LibreOffice 或 MS Office，
  在 CI 上一般会 skip。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from doc_converter import Converter
from doc_converter.core.base import ConversionError
from doc_converter.core.registry import Registry
from doc_converter.utils.paths import ensure_dir, split_ext, unique_output_path
from doc_converter.utils.platform import Platform, detect_platform


# =========================================================================== #
# Converter 查询接口
# =========================================================================== #
def test_converter_supports_pairs() -> None:
    """``Converter.supported()`` 应至少返回 18 个核心转换组合。

    期望至少包含：
        - Excel <-> PDF
        - PDF -> PNG / JPG / XLSX / DOCX
        - 图片 -> PDF / XLSX
        - Word -> PDF
    """
    pairs = Converter.supported()
    assert isinstance(pairs, list), f"supported() 应返回 list，实际: {type(pairs)}"
    assert len(pairs) >= 18, f"支持的组合数量应 >= 18，实际: {len(pairs)}"

    # 把 set 化便于成员检查
    pair_set = {tuple(p) for p in pairs}
    must_have = {
        (".xlsx", ".pdf"),
        (".xls", ".pdf"),
        (".pdf", ".xlsx"),
        (".pdf", ".png"),
        (".pdf", ".jpg"),
        (".pdf", ".docx"),
        (".docx", ".pdf"),
        (".doc", ".pdf"),
        (".png", ".pdf"),
        (".jpg", ".pdf"),
        (".png", ".xlsx"),
    }
    missing = must_have - pair_set
    assert not missing, f"缺少核心支持组合: {missing}"


def test_converter_can_convert() -> None:
    """``Converter.can_convert()`` 对已知组合返回 True，未知返回 False。"""
    # 已知支持的组合
    assert Converter.can_convert("input.xlsx", "output.pdf") is True, (
        "xlsx -> pdf 应支持"
    )
    # 未支持的组合
    assert Converter.can_convert("input.xyz", "output.pdf") is False, (
        "xyz -> pdf 应不支持"
    )
    assert Converter.can_convert("a.md", "a.pdf") is False, (
        "md -> pdf 应不支持（项目未提供该组合）"
    )


def test_converter_source_not_exists(tmp_path: Path) -> None:
    """源文件不存在时抛 :class:`ConversionError`。"""
    missing = tmp_path / "no_such.xlsx"
    with pytest.raises(ConversionError) as exc_info:
        Converter.convert(str(missing), str(tmp_path / "out.pdf"))
    assert "不存在" in str(exc_info.value) or "not exist" in str(exc_info.value).lower(), (
        f"异常消息应提示'源文件不存在'，实际: {exc_info.value}"
    )


def test_converter_target_must_have_extension(tmp_path: Path) -> None:
    """target 是目录或没有扩展名时应抛 :class:`ConversionError`。

    注意：源文件必须存在，否则会被"源文件不存在"先拦截；这里
    复用 conftest 提供的 ``sample_png`` 风格的本地文件作为占位源。
    """
    # 创建一个 .png 源文件（PNG -> PDF 是合法组合，便于触发"扩展名缺失"分支）
    src = tmp_path / "in.png"
    Image.new("RGB", (10, 10), "red").save(src, "PNG")

    # target 是目录
    target_dir = tmp_path / "out_dir"
    target_dir.mkdir()
    with pytest.raises(ConversionError) as exc_info:
        Converter.convert(str(src), str(target_dir))
    assert "扩展名" in str(exc_info.value) or "目录" in str(exc_info.value), (
        f"异常消息应提示'目标必须是带扩展名的文件'，实际: {exc_info.value}"
    )

    # target 没有扩展名
    target_no_ext = tmp_path / "out_noext"
    with pytest.raises(ConversionError):
        Converter.convert(str(src), str(target_no_ext))


def test_converter_unsupported_pair(tmp_path: Path) -> None:
    """不支持的扩展名组合应抛 :class:`ConversionError`。

    源码内部在 :func:`Converter.convert` 中把 :class:`KeyError` 包装为
    :class:`ConversionError`，错误信息形如
    ``"没有注册处理 .md -> .pdf 的转换器"``。
    """
    # 创建一个 .md 源文件（.md 不在 supported_pairs 中）
    src = tmp_path / "in.md"
    src.write_text("# Hello", encoding="utf-8")

    with pytest.raises(ConversionError) as exc_info:
        Converter.convert(str(src), str(tmp_path / "out.pdf"))
    msg = str(exc_info.value)
    # 同时校验错误信息含有关键扩展名 / 关键词，避免误报
    assert (".md" in msg and ".pdf" in msg) or "未注册" in msg or "不支持" in msg, (
        f"异常消息应提示'未注册 .md -> .pdf'，实际: {msg[:200]}"
    )


# =========================================================================== #
# 路径工具
# =========================================================================== #
def test_paths_ensure_dir(tmp_path: Path) -> None:
    """``ensure_dir`` 应能创建嵌套目录。"""
    nested = tmp_path / "a" / "b" / "c"
    assert not nested.exists(), "前置条件：nested 不应存在"
    result = ensure_dir(nested)
    assert result.exists() and result.is_dir(), "ensure_dir 后应为目录"
    assert result == nested, "ensure_dir 应返回传入的 Path"

    # 再次调用应幂等
    result2 = ensure_dir(nested)
    assert result2.exists() and result2 == nested, "ensure_dir 应幂等"


def test_paths_unique_output_path(tmp_path: Path) -> None:
    """``unique_output_path`` 在文件已存在时返回带 ``_1`` / ``_2`` 后缀的新路径。"""
    target = tmp_path / "out.pdf"

    # 不存在时直接返回原路径
    p1 = unique_output_path(target)
    assert p1 == target, f"文件不存在时应返回原路径，实际: {p1}"

    # 创建文件后再调用
    target.write_bytes(b"%PDF-1.4 dummy")
    p2 = unique_output_path(target)
    assert p2 != target, "文件存在时应返回不同路径"
    assert p2.name == "out_1.pdf", f"应追加 _1 后缀，实际: {p2.name}"

    # 再创建 out_1.pdf，应追加 _2
    p2.write_bytes(b"%PDF-1.4 dummy")
    p3 = unique_output_path(target)
    assert p3.name == "out_2.pdf", f"应追加 _2 后缀，实际: {p3.name}"


def test_paths_split_ext(tmp_path: Path) -> None:
    """``split_ext`` 应把 (stem, ext) 拆开，ext 小写含点。"""
    stem, ext = split_ext("report.PDF")
    assert stem == "report", f"stem 应为 'report'，实际: {stem}"
    assert ext == ".pdf", f"ext 应小写且含点，实际: {ext}"

    stem, ext = split_ext("no_extension")
    assert stem == "no_extension", f"无扩展名时 stem 应为原文件名，实际: {stem}"
    assert ext == "", f"无扩展名时 ext 应为空串，实际: {ext}"


# =========================================================================== #
# 平台检测
# =========================================================================== #
def test_platform_detect() -> None:
    """``detect_platform`` 应返回 :class:`Platform` 枚举之一。"""
    p = detect_platform()
    assert isinstance(p, Platform), f"应返回 Platform，实际: {type(p)}"
    assert p in {
        Platform.WINDOWS,
        Platform.LINUX,
        Platform.DARWIN,
        Platform.OTHER,
    }, f"返回了未在枚举中的值: {p}"


# =========================================================================== #
# ImageConverter 端到端
# =========================================================================== #
def test_image_converter_png_to_pdf(
    sample_png: Path, tmp_output_dir: Path
) -> None:
    """PNG -> PDF：用临时 PNG 验证转换产物存在且为非空 PDF。"""
    target = tmp_output_dir / "out.pdf"
    result = Converter.convert(str(sample_png), str(target))

    assert result.exists(), f"PDF 应已生成: {result}"
    assert result.stat().st_size > 0, "PDF 不应为空"
    assert result.suffix.lower() == ".pdf", f"扩展名应为 .pdf，实际: {result.suffix}"


def test_image_converter_jpg_to_pdf(
    sample_jpg: Path, tmp_output_dir: Path
) -> None:
    """JPG -> PDF：用临时 JPG 验证转换产物存在。"""
    target = tmp_output_dir / "out.pdf"
    result = Converter.convert(str(sample_jpg), str(target))

    assert result.exists(), f"PDF 应已生成: {result}"
    assert result.stat().st_size > 0, "PDF 不应为空"


def test_image_converter_convert_many(
    sample_png: Path, sample_jpg: Path, tmp_output_dir: Path
) -> None:
    """多图合并为多页 PDF：调用 :meth:`ImageConverter.convert_many`。"""
    from doc_converter.converters.image_converter import ImageConverter

    target = tmp_output_dir / "merged.pdf"
    converter = ImageConverter()
    result = converter.convert_many([str(sample_png), str(sample_jpg)], str(target))

    assert result.exists(), f"多页 PDF 应已生成: {result}"
    assert result.stat().st_size > 0, "多页 PDF 不应为空"

    # 验证页数 >= 2
    import fitz  # 局部导入，避免模块级硬依赖

    with fitz.open(str(result)) as doc:
        assert doc.page_count >= 2, f"多页 PDF 应 >= 2 页，实际: {doc.page_count}"


# =========================================================================== #
# Registry 行为
# =========================================================================== #
def test_registry_clear() -> None:
    """``Registry.clear()`` 应清空全部路由。

    注意：``Converter._ensure_converters_imported`` 的懒加载机制存在一
    个已知行为——``_IMPORTED`` 标志为 ``True`` 后，再次调用
    :func:`Converter.supported` 不会重新 import 转换器。``clear()`` 后
    必须**显式重新注册**才能恢复，因此本测试在 finally 中调用
    ``importlib.reload`` 重新执行每个转换器模块的顶层 ``Registry.register``。
    """
    # 先记录当前路由数
    before = len(Registry.supported_pairs())
    assert before > 0, "前置条件：注册表应非空"

    Registry.clear()
    try:
        assert Registry.supported_pairs() == [], (
            f"clear() 后路由表应为空，实际: {Registry.supported_pairs()}"
        )
    finally:
        # 重新执行每个转换器模块的顶层代码以触发 ``Registry.register``
        import importlib

        for mod_name in (
            "doc_converter.converters.excel_converter",
            "doc_converter.converters.pdf_converter",
            "doc_converter.converters.image_converter",
            "doc_converter.converters.word_converter",
            "doc_converter.converters.ocr_converter",
        ):
            importlib.import_module(mod_name)
            importlib.reload(importlib.import_module(mod_name))


def test_registry_register_duplicate() -> None:
    """重复注册同名转换器不应报错（按列表追加，可同时存在多个实例）。

    用一个临时 ``(src, dst)`` 组合做隔离，避免影响真实路由。
    """
    from typing import ClassVar, Tuple

    from doc_converter.core.base import BaseConverter

    class _TmpConverter(BaseConverter):
        name: ClassVar[str] = "TmpDupConverter"
        supported_pairs: ClassVar[Tuple[Tuple[str, str], ...]] = (
            (".tmpsrc", ".tmpdst"),
        )

        def convert(self, source, target, **kwargs):  # pragma: no cover - 不调用
            from pathlib import Path as _P

            return _P(target)

    # 首次注册
    Registry.register(_TmpConverter())
    after_first = len(Registry.all_resolved(".tmpsrc", ".tmpdst"))

    # 重复注册不应抛异常
    Registry.register(_TmpConverter())
    after_second = len(Registry.all_resolved(".tmpsrc", ".tmpdst"))

    assert after_first >= 1, "首次注册后应至少 1 个 handler"
    assert after_second == after_first + 1, (
        f"重复注册应追加 handler，从 {after_first} -> {after_second}"
    )

    # 清理：移除所有 _TmpConverter 实例，避免污染其它测试
    for inst in list(Registry.all_resolved(".tmpsrc", ".tmpdst")):
        Registry.unregister(inst)


# =========================================================================== #
# 平台依赖的可选测试（soffice / tesseract / pywin32）
# =========================================================================== #
@pytest.mark.skipif(
    shutil.which("soffice") is None and shutil.which("libreoffice") is None,
    reason="需要本机安装 LibreOffice (soffice) 才能跑 Excel/Word -> PDF 端到端测试",
)
def test_excel_to_pdf_smoke(tmp_path: Path) -> None:
    """Excel -> PDF 端到端冒烟测试：需要本机 LibreOffice。

    用 openpyxl 生成一个最简单的 xlsx，再调 ``Converter.convert`` 转 PDF。
    """
    from openpyxl import Workbook

    src = tmp_path / "tiny.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["hello", "world"])
    ws.append([1, 2])
    wb.save(str(src))

    target = tmp_path / "tiny.pdf"
    result = Converter.convert(str(src), str(target))

    assert result.exists(), "PDF 应已生成"
    assert result.stat().st_size > 0, "PDF 不应为空"


def test_ocr_converter_imports() -> None:
    """OCR 转换器：pytesseract / tesseract 二进制任一缺失时 skip。"""
    pytesseract = pytest.importorskip("pytesseract")
    try:
        version = pytesseract.get_tesseract_version()
    except Exception as exc:
        pytest.skip(f"tesseract binary not installed: {exc}")

    # 至少能拿到版本号
    assert version is not None
