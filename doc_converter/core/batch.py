"""批量处理。

使用方式::

    from doc_converter.core.batch import BatchProcessor

    results = BatchProcessor(
        source_dir="input/",
        target_dir="output/",
        overwrite=False,
    ).run()

    for r in results:
        print(r.source, "->", r.target, r.success, r.message)

特性：
    - 自动创建目标目录，绝不覆盖源文件。
    - 单个文件失败不会中断整个批处理（``continue_on_error=True``）。
    - 结束时打印汇总报告。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from .base import ConversionError, ConversionResult
from .converter import Converter
from .logger import get_logger


@dataclass
class BatchResult:
    """整批处理的结果汇总。"""

    total: int = 0
    success: int = 0
    failed: int = 0
    results: List[ConversionResult] = field(default_factory=list)

    def __iter__(self):  # type: ignore[override]
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    def summary(self) -> str:
        return (
            f"批量转换完成: 总数={self.total}, 成功={self.success}, "
            f"失败={self.failed}"
        )


class BatchProcessor:
    """目录级别的批量处理器。

    仅会处理 :class:`Converter.supported()` 中出现的扩展名组合；
    其它文件会被跳过并记录日志。
    """

    _log = get_logger("core.BatchProcessor")

    def __init__(
        self,
        source_dir: str | Path,
        target_dir: str | Path,
        *,
        overwrite: bool = False,
        continue_on_error: bool = True,
        recursive: bool = True,
    ) -> None:
        self.source_dir = Path(source_dir).expanduser().resolve()
        self.target_dir = Path(target_dir).expanduser().resolve()
        self.overwrite = overwrite
        self.continue_on_error = continue_on_error
        self.recursive = recursive

    # ------------------------------------------------------------------ #
    # 主入口
    # ------------------------------------------------------------------ #
    def run(self) -> List[ConversionResult]:
        """执行批处理并返回 ``list[ConversionResult]``。"""
        if not self.source_dir.exists() or not self.source_dir.is_dir():
            raise ConversionError(
                f"源目录不存在或不是目录: {self.source_dir}"
            )

        self.target_dir.mkdir(parents=True, exist_ok=True)

        # 把"所有支持的源扩展名"收集起来，便于按扩展名过滤
        src_exts = {src for src, _ in Converter.supported()}

        files = self._iter_files(src_exts)
        self._log.info(
            "批量处理开始: source=%s, target=%s, 待处理=%d",
            self.source_dir, self.target_dir, len(files),
        )

        results: List[ConversionResult] = []
        for src_path, dst_path in files:
            results.append(self._convert_one(src_path, dst_path))

        # 汇总
        success = sum(1 for r in results if r.success)
        failed = len(results) - success
        self._log.info(
            "批量处理完成: 总数=%d, 成功=%d, 失败=%d", len(results), success, failed
        )
        return results

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #
    def _iter_files(self, src_exts: Iterable[str]) -> Iterable[tuple[Path, Path]]:
        pattern = self.source_dir.rglob("*") if self.recursive else self.source_dir.glob("*")
        for src_path in pattern:
            if not src_path.is_file():
                continue
            if src_path.suffix.lower() not in src_exts:
                continue
            # 保持相对路径结构输出
            rel = src_path.relative_to(self.source_dir)
            dst_path = self.target_dir / rel
            # 目标扩展名沿用源扩展名（本批处理按"格式归一"为目录→目录的复制式处理，
            # 真正的格式转换仍由调用方在 ``Converter.convert`` 中指定）。
            # 这里默认按第一个支持的目的扩展名做转换，便于"PDF目录转图片目录"等场景。
            dst_ext = self._infer_dst_ext(src_path.suffix.lower())
            if dst_ext is None:
                # 没有任何已注册的目的格式，回退为同名复制
                self._log.debug("无目标格式，跳过: %s", src_path)
                continue
            dst_path = dst_path.with_suffix(dst_ext)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            yield src_path, dst_path

    def _infer_dst_ext(self, src_ext: str) -> str | None:
        """根据已注册的组合挑一个默认目的扩展名。"""
        for s, d in Converter.supported():
            if s == src_ext:
                return d
        return None

    def _convert_one(self, src: Path, dst: Path) -> ConversionResult:
        try:
            actual = Converter.convert(src, dst, overwrite=self.overwrite)
        except ConversionError as exc:
            self._log.error("转换失败: %s -> %s, 原因: %s", src, dst, exc)
            if not self.continue_on_error:
                raise
            return ConversionResult(source=src, target=dst, success=False, message=str(exc))
        except Exception as exc:  # 兜底保护
            self._log.exception("未预期异常: %s -> %s", src, dst)
            if not self.continue_on_error:
                raise
            return ConversionResult(
                source=src, target=dst, success=False,
                message=f"未预期异常: {exc!r}",
            )
        return ConversionResult(source=src, target=actual, success=True, message="ok")
