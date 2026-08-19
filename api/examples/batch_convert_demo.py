"""批量转换演示：生成多张测试图，转换为 PDF，打包下载。

演示内容：

1. 在 :data:`OUTPUT_DIR` 下生成 5 张不同颜色的测试 PNG。
2. 调用 :meth:`DocConverterClient.convert_batch` 提交批量任务。
3. 通过 :meth:`wait_for_task` + 进度回调实时展示进度。
4. 下载 ZIP 形式的批量结果。

运行前请确保后端已启动::

    cd api && uvicorn app.main:app

执行::

    python examples/batch_convert_demo.py
"""

from __future__ import annotations

import time
from pathlib import Path

from PIL import Image

from api_client import DocConverterClient

# 输出目录：脚本所在目录的 ``out/`` 子目录
OUTPUT_DIR = Path(__file__).resolve().parent / "out"
OUTPUT_DIR.mkdir(exist_ok=True)

# 测试图片颜色与数量
COLORS = ["red", "blue", "green", "yellow", "purple"]

# 批量结果 ZIP 文件名
ZIP_NAME = "batch_result.zip"


def _build_samples() -> list:
    """在 :data:`OUTPUT_DIR` 下生成 5 张 300x200 的纯色 PNG。

    Returns:
        生成的 PNG 路径列表。
    """
    samples: list = []
    for i, color in enumerate(COLORS):
        p = OUTPUT_DIR / f"sample_{i}.png"
        Image.new("RGB", (300, 200), color).save(p)
        samples.append(p)
    return samples


def _cleanup(samples: list, zip_path: Path) -> None:
    """清理本次演示生成的所有临时文件。"""
    for p in samples:
        p.unlink(missing_ok=True)
    zip_path.unlink(missing_ok=True)


def main() -> int:
    """脚本入口。

    Returns:
        进程退出码，0 表示成功。
    """
    samples = _build_samples()
    zip_path = OUTPUT_DIR / ZIP_NAME
    started = time.monotonic()

    with DocConverterClient(base_url="http://localhost:8000") as client:
        # 1. 健康检查（失败提前退出，避免无效轮询）
        try:
            health = client.health()
        except Exception as exc:  # noqa: BLE001
            print(f"[X] 健康检查失败: {exc}")
            _cleanup(samples, zip_path)
            return 1
        print(
            f"[1/4] 服务状态: {health.get('status')}, "
            f"支持 {health.get('supported_pairs', 0)} 个转换"
        )

        # 2. 提交批量任务
        print(f"[2/4] 提交批量任务，{len(samples)} 个文件...")
        try:
            task_id = client.convert_batch(
                file_paths=samples,
                conversion_type="png_to_pdf",
                zip_output=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[X] 提交批量任务失败: {exc}")
            _cleanup(samples, zip_path)
            return 2
        print(f"      task_id = {task_id}")

        # 3. 轮询直到完成
        def on_progress(info) -> None:
            """进度回调：打印百分比 / 状态 / 已处理数。"""
            progress = info.get("progress", 0.0)
            status = info.get("status", "?")
            processed = info.get("processed_files", 0)
            total = info.get("total_files", len(samples))
            print(f"      [{progress:5.1f}%] {status} ({processed}/{total})")

        try:
            final = client.wait_for_task(
                task_id, poll_interval=1.0, on_progress=on_progress
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[X] 等待任务失败: {exc}")
            _cleanup(samples, zip_path)
            return 3

        print(f"[3/4] 任务完成: {final.get('status')}")

        # 4. 下载 ZIP 结果
        status = final.get("status")
        if status in ("success", "partial_success"):
            try:
                zip_path = client.download(task_id, save_to=zip_path)
            except Exception as exc:  # noqa: BLE001
                print(f"[X] 下载失败: {exc}")
                _cleanup(samples, zip_path)
                return 4
            print(
                f"[4/4] 已下载: {zip_path} ({zip_path.stat().st_size} bytes)"
            )
        else:
            print(f"[!] 任务未成功结束（status={status}），跳过下载")

    elapsed = time.monotonic() - started
    print(f"\n总耗时: {elapsed:.1f}s")

    # 清理
    _cleanup(samples, zip_path)
    print("[cleanup] 已清理演示文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
