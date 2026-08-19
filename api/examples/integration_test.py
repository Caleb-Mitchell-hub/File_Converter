"""集成测试。

本脚本同时支持两种运行方式：

1. **pytest 风格**::

       pytest examples/integration_test.py -v

2. **直接命令行执行**::

       python examples/integration_test.py

测试用例会先 ping ``/api/v1/health`` 探测服务，若后端未启动则整体跳过并提示。
所有临时产物由 pytest 的 ``tmp_path`` fixture 提供，结束后自动清理。

前置条件::

    cd api && uvicorn app.main:app

可调环境变量：
    - ``DOC_CONVERTER_BASE_URL``：覆盖默认 :data:`BASE_URL`。
    - ``DOC_CONVERTER_TIMEOUT``：覆盖默认 :data:`TIMEOUT`（秒）。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# 把 examples 目录加入 sys.path，确保 ``from api_client import ...`` 可用
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import requests
from PIL import Image

from api_client import APIError, DocConverterClient


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BASE_URL: str = os.environ.get("DOC_CONVERTER_BASE_URL", "http://localhost:8000")
TIMEOUT: int = int(os.environ.get("DOC_CONVERTER_TIMEOUT", "60"))


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _is_api_up() -> bool:
    """快速探测后端是否在线。

    Returns:
        ``/api/v1/health`` 返回 200 时为 ``True``。
    """
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        return resp.status_code == 200
    except Exception:  # noqa: BLE001 - 探测过程吞掉所有连接错误
        return False


# 整个模块在没有 API 时整体跳过
pytestmark = pytest.mark.skipif(
    not _is_api_up(),
    reason=f"API not running at {BASE_URL}",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_png(tmp_path) -> Path:
    """生成一张 200x200 的红色 PNG，存到临时目录。"""
    p: Path = tmp_path / "test.png"
    Image.new("RGB", (200, 200), "red").save(p)
    return p


@pytest.fixture
def client():
    """提供一个 :class:`DocConverterClient` 实例，测试结束自动关闭。"""
    c = DocConverterClient(base_url=BASE_URL, timeout=TIMEOUT)
    try:
        yield c
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------


def test_health(client: DocConverterClient) -> None:
    """健康检查端点应返回 ``status=ok`` 且 ``supported_pairs > 0``。"""
    info = client.health()
    assert info["status"] == "ok", f"unexpected status: {info}"
    assert int(info.get("supported_pairs", 0)) > 0, "supported_pairs 应大于 0"


def test_single_convert(
    client: DocConverterClient, sample_png: Path, tmp_path: Path
) -> None:
    """单文件转换 PNG -> PDF：响应标记成功，下载文件存在且非空。"""
    out: Path = tmp_path / "out.pdf"
    result = client.convert_single(
        file_path=sample_png,
        conversion_type="png_to_pdf",
        save_to=out,
    )
    assert out.exists(), f"输出文件不存在: {out}"
    assert out.stat().st_size > 0, f"输出文件为空: {out}"
    # 兼容 ``success`` 字段或 ``status == "success"``
    assert result.get("success") is True or result.get("status") == "success", (
        f"转换未标记成功: {result}"
    )


def test_batch_convert(client: DocConverterClient, tmp_path: Path) -> None:
    """批量转换 3 张 PNG -> 1 个 PDF ZIP：任务成功且 ZIP 非空。"""
    files: list = []
    for i, color in enumerate(["red", "blue", "green"]):
        p: Path = tmp_path / f"img_{i}.png"
        Image.new("RGB", (100, 100), color).save(p)
        files.append(p)

    task_id: str = client.convert_batch(
        file_paths=files,
        conversion_type="png_to_pdf",
        zip_output=True,
    )
    assert task_id, "task_id 不应为空"

    final = client.wait_for_task(task_id, timeout=60)
    assert final["status"] in ("success", "partial_success"), (
        f"批量任务未成功: {final}"
    )

    zip_path: Path = tmp_path / "result.zip"
    client.download(task_id, save_to=zip_path)
    assert zip_path.exists(), f"ZIP 不存在: {zip_path}"
    assert zip_path.stat().st_size > 0, f"ZIP 为空: {zip_path}"


def test_task_not_found(client: DocConverterClient) -> None:
    """查询不存在的任务应抛 :class:`APIError` 且状态码为 404。"""
    with pytest.raises(APIError) as exc_info:
        client.get_task("nonexistent_task_id_xyz")
    assert exc_info.value.status_code == 404, (
        f"期望 404，实际 {exc_info.value.status_code}"
    )


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def _main() -> int:
    """直接执行时的入口：探测 API 后调用 pytest。

    Returns:
        进程退出码（与 pytest 退出码一致）。
    """
    print("=" * 60)
    print("集成测试（需要先启动 uvicorn）")
    print(f"BASE_URL = {BASE_URL}")
    print(f"TIMEOUT  = {TIMEOUT}s")
    print("=" * 60)

    if not _is_api_up():
        print(f"\n[FAIL] API 未运行在 {BASE_URL}")
        print("请先启动: cd api && uvicorn app.main:app --reload")
        return 1

    print(f"\n[ OK ] API 在线，开始跑测试...")
    return subprocess.call(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"]
    )


if __name__ == "__main__":
    sys.exit(_main())
