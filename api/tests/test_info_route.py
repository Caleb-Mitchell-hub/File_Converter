"""``GET /info`` 端点单元测试。

设计依据：``docs/superpowers/specs/2026-06-15-file-hz-service-registration-design.md``
第五节（5.1 / 5.2 / 5.3）。

覆盖：
    - 状态码 200
    - 响应是合法 JSON
    - 字段齐全：``status``（字符串）、``pid``（整数 > 0）、``urls``（数组，len >= 4）
    - 每个 ``urls`` 元素都包含 ``name`` 和 ``url`` 字段
    - ``/info`` 不出现在 OpenAPI 文档中（``include_in_schema=False``）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 让 ``from app.main import app`` 可工作：把 ``api/`` 加进 sys.path
_API_DIR = Path(__file__).resolve().parent.parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


client = TestClient(app)


def test_info_returns_http_200() -> None:
    """``GET /info`` 必须始终返回 200。"""
    resp = client.get("/info")
    assert resp.status_code == 200, (
        f"/info 应返回 200，实际: {resp.status_code}, body: {resp.text}"
    )


def test_info_response_is_json() -> None:
    """响应体是合法 JSON。"""
    resp = client.get("/info")
    assert resp.headers["content-type"].startswith("application/json"), (
        f"content-type 应为 JSON，实际: {resp.headers.get('content-type')}"
    )
    body = resp.json()
    assert isinstance(body, dict), f"顶层应为 dict，实际: {type(body)}"


def test_info_status_field() -> None:
    """``status`` 字段存在且为字符串。"""
    body = client.get("/info").json()
    assert "status" in body, f"缺少 status 字段，实际 keys: {list(body.keys())}"
    assert isinstance(body["status"], str), (
        f"status 应为 str，实际: {type(body['status'])}"
    )
    assert body["status"] == "running", (
        f"status 应固定为 'running'，实际: {body['status']}"
    )


def test_info_pid_field_is_positive_int() -> None:
    """``pid`` 字段是大于 0 的整数，且等于当前进程 pid。"""
    body = client.get("/info").json()
    assert "pid" in body, f"缺少 pid 字段，实际 keys: {list(body.keys())}"
    pid = body["pid"]
    # bool 是 int 的子类，这里排除掉
    assert isinstance(pid, int) and not isinstance(pid, bool), (
        f"pid 应为 int，实际: {type(pid)}"
    )
    assert pid > 0, f"pid 应 > 0，实际: {pid}"
    assert pid == os.getpid(), (
        f"pid 应等于当前进程 pid ({os.getpid()})，实际: {pid}"
    )


def test_info_urls_array_has_at_least_four_entries() -> None:
    """``urls`` 是数组，且至少 4 项。"""
    body = client.get("/info").json()
    assert "urls" in body, f"缺少 urls 字段，实际 keys: {list(body.keys())}"
    urls = body["urls"]
    assert isinstance(urls, list), f"urls 应为 list，实际: {type(urls)}"
    assert len(urls) >= 4, f"urls 应至少 4 项，实际: {len(urls)}"


def test_info_urls_entries_have_name_and_url() -> None:
    """每条 url 元素都包含 ``name``（非空字符串）和 ``url``（非空字符串）。"""
    urls = client.get("/info").json()["urls"]
    for i, entry in enumerate(urls):
        assert isinstance(entry, dict), f"第 {i} 项应为 dict，实际: {type(entry)}"
        assert "name" in entry, f"第 {i} 项缺少 name 字段: {entry}"
        assert "url" in entry, f"第 {i} 项缺少 url 字段: {entry}"
        assert isinstance(entry["name"], str) and entry["name"], (
            f"第 {i} 项 name 应为非空字符串，实际: {entry['name']!r}"
        )
        assert isinstance(entry["url"], str) and entry["url"], (
            f"第 {i} 项 url 应为非空字符串，实际: {entry['url']!r}"
        )


def test_info_excluded_from_openapi_schema() -> None:
    """``/info`` 不应出现在 OpenAPI 文档中（``include_in_schema=False``）。

    避免污染 ``/docs``，并防止与规范要求的 4 项 urls 重复出现在自动文档里。
    """
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/info" not in paths, (
        f"/info 不应在 OpenAPI paths 中，实际 paths: {list(paths.keys())}"
    )
