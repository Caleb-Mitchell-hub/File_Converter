"""单文件转换演示。

演示 DocConverter 客户端的最小完整流程：

1. 调用 :meth:`health` 检查服务。
2. 使用 :meth:`convert_single` 将 PNG 转换为 PDF。
3. 自动下载到本地并校验产物。

运行前请确保后端已启动::

    cd api && uvicorn app.main:app

执行::

    python examples/single_convert_demo.py
"""

from __future__ import annotations

from pathlib import Path

from api_client import DocConverterClient

# 生成一张 200x200 的纯色测试图，存到当前工作目录
from PIL import Image

# 文档输出目录：脚本所在目录的 ``out/`` 子目录，避免污染仓库根
OUTPUT_DIR = Path(__file__).resolve().parent / "out"
OUTPUT_DIR.mkdir(exist_ok=True)

# 输入与输出文件名
SAMPLE_NAME = "demo_sample.png"
OUTPUT_NAME = "output.pdf"

sample = OUTPUT_DIR / SAMPLE_NAME
output_pdf = OUTPUT_DIR / OUTPUT_NAME


def main() -> int:
    """脚本入口。

    Returns:
        进程退出码，0 表示成功。
    """
    # 1. 准备测试文件
    Image.new("RGB", (200, 200), "red").save(sample)
    print(f"[1/4] 已生成测试文件: {sample}")

    with DocConverterClient() as client:
        # 2. 健康检查
        try:
            health = client.health()
        except Exception as exc:  # noqa: BLE001 - 演示脚本简单处理
            print(f"[X] 健康检查失败: {exc}")
            return 1
        print(
            f"[2/4] 服务状态: {health.get('status')}, "
            f"支持 {health.get('supported_pairs', 0)} 个转换"
        )

        # 3. 单文件转换：图片 -> PDF，并自动下载
        try:
            result = client.convert_single(
                file_path=sample,
                conversion_type="png_to_pdf",
                save_to=output_pdf,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[X] 转换失败: {exc}")
            return 2

        print(
            f"[3/4] 转换成功: {result.get('output_filename', output_pdf.name)} "
            f"({result.get('file_size', output_pdf.stat().st_size)} bytes)"
        )

    # 4. 校验产物
    if not output_pdf.exists() or output_pdf.stat().st_size == 0:
        print(f"[X] 产物 {output_pdf} 不存在或为空")
        return 3
    print(f"[4/4] 产物 OK: {output_pdf} ({output_pdf.stat().st_size} bytes)")

    # 清理演示产物
    sample.unlink(missing_ok=True)
    output_pdf.unlink(missing_ok=True)
    print("[cleanup] 已清理演示文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
