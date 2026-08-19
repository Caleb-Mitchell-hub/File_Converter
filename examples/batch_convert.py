"""批量目录转换示例。

本示例演示 :func:`Converter.batch` 的标准用法：

- 把 ``input/`` 下所有受支持的文件转换到 ``output/``。
- 单个文件失败不会中断整批（``continue_on_error=True``）。
- 结束时打印总数 / 成功 / 失败 汇总。

运行前：

1. 准备好 ``input/`` 目录并放入测试文件（xlsx / pdf / docx / png ...）。
2. 准备好 ``output/`` 目录（或让程序自动创建）。

注意事项：

- ``Converter.batch`` 会按"已注册组合中匹配源扩展名的目的扩展名"自动选
  第一个匹配（参见 ``BatchProcessor._infer_dst_ext``）；如果同一源扩展名
  对应多种目的格式（例如 ``.xlsx`` 可转 ``.pdf``、``.png``、``.jpg``），
  当前实现会**默认选字典序第一个**。如需指定目标格式，请改用
  :func:`Converter.convert` 自行遍历。
"""

from __future__ import annotations

from pathlib import Path

from doc_converter import Converter


def main() -> None:
    """演示批量转换并打印汇总报告。"""

    input_dir = Path("input")
    output_dir = Path("output")

    if not input_dir.exists():
        print(f"提示：{input_dir} 不存在，请先创建并放入测试文件后重试。")
        return

    # ------------------------------------------------------------------ #
    # 批量处理：递归扫描 input/ 下所有受支持的文件，转到 output/。
    # ------------------------------------------------------------------ #
    results = Converter.batch(
        source_dir=input_dir,
        target_dir=output_dir,
        overwrite=False,           # 目标已存在时不覆盖，自动追加 _1 / _2 后缀
        continue_on_error=True,    # 单个文件失败不影响其他
    )

    # ------------------------------------------------------------------ #
    # 汇总统计
    # ------------------------------------------------------------------ #
    total = len(results)
    success = sum(1 for r in results if r.success)
    failed = total - success

    print("=" * 60)
    print(f"批量转换完成: 总数={total}, 成功={success}, 失败={failed}")
    print("=" * 60)

    # 列出失败的文件
    if failed:
        print("\n失败文件：")
        for r in results:
            if not r.success:
                print(f"  - {r.source} -> {r.target} ({r.message})")
    else:
        print("\n全部成功！")


if __name__ == "__main__":
    main()
