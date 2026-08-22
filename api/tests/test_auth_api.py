
"""认证 + 数据隔离 + 任务持久化 集成测试。

覆盖：
- 未登录访问受保护接口返回 401
- 注册（含重复注册 409、弱密码 400）
- 登录 / /auth/me
- 用户 A 与用户 B 的任务相互不可见（列表过滤、详情 404、下载 404）
- 任务持久化：重建 TaskManager 后 load_all 恢复
"""

from __future__ import annotations

import io
import shutil
import sys
import uuid
from pathlib import Path

_API_DIR = Path(__file__).resolve().parent.parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.service.task_manager import TaskManager


#: 可写临时目录根（沙箱内系统 Temp 不可写，改到工作区 logs 下）
_TMP_ROOT = Path(__file__).resolve().parent.parent.parent / "logs" / "test-tmp"


@pytest.fixture()
def client(monkeypatch):
    """每个测试使用独立临时数据库 / 上传 / 输出目录。"""
    _TMP_ROOT.mkdir(parents=True, exist_ok=True)
    # 注意：不能使用 tempfile.mkdtemp —— DSH 沙箱会拦截其创建的目录
    base = _TMP_ROOT / f"auth_{uuid.uuid4().hex[:10]}"
    base.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    monkeypatch.setattr(settings, "db_path", base / "test.db")
    monkeypatch.setattr(settings, "upload_dir", base / "uploads")
    monkeypatch.setattr(settings, "output_dir", base / "outputs")
    with TestClient(app) as c:
        yield c
    shutil.rmtree(base, ignore_errors=True)


def _register(client, username: str, password: str, nickname: str = "") -> None:
    body = {"username": username, "password": password}
    if nickname:
        body["nickname"] = nickname
    resp = client.post("/api/v1/auth/register", json=body)
    assert resp.status_code == 200, resp.text


def _login(client, username: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["access_token"]
    assert token, "登录应返回 access_token"
    return {"Authorization": "Bearer " + token}


def _tiny_png() -> bytes:
    from PIL import Image
    import io as _io

    buf = _io.BytesIO()
    Image.new("RGB", (50, 50), "red").save(buf, format="PNG")
    return buf.getvalue()


# =========================================================================== #
# 认证
# =========================================================================== #
def test_unauthorized_returns_401(client) -> None:
    """未登录访问任务接口应返回 401。"""
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 401, resp.text
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


def test_register_login_me_flow(client) -> None:
    """注册 -> 登录 -> /auth/me 全流程。"""
    _register(client, "alice", "alice123", "Alice")
    headers = _login(client, "alice", "alice123")

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    data = me.json()["data"]
    assert data["username"] == "alice"
    assert data["nickname"] == "Alice"
    assert data["role"] == "user"
    assert "password" not in data, "响应不得包含密码字段"


def test_register_duplicate_409(client) -> None:
    _register(client, "alice", "alice123")
    resp = client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "xxx123"}
    )
    assert resp.status_code == 409, resp.text


def test_register_weak_password_400(client) -> None:
    resp = client.post(
        "/api/v1/auth/register", json={"username": "bob", "password": "123"}
    )
    assert resp.status_code == 400, resp.text


def test_login_wrong_password_401(client) -> None:
    _register(client, "alice", "alice123")
    resp = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "wrong"}
    )
    assert resp.status_code == 401, resp.text


def test_default_admin_seeded(client) -> None:
    """首次启动应预置默认管理员，且密码正确。"""
    headers = _login(client, "admin", "admin123")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["data"]["role"] == "admin"


# =========================================================================== #
# 数据隔离
# =========================================================================== #
def test_task_isolation_between_users(client) -> None:
    """用户 A 创建的任务，用户 B 列表/详情/下载均不可见。"""
    _register(client, "alice", "alice123")
    _register(client, "bob", "bob12345")
    alice_h = _login(client, "alice", "alice123")
    bob_h = _login(client, "bob", "bob12345")

    # alice 转换一个小 PNG -> PDF
    resp = client.post(
        "/api/v1/convert",
        files={"file": ("tiny.png", _tiny_png(), "image/png")},
        data={"conversion_type": "png_to_pdf"},
        headers=alice_h,
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["data"]["task_id"]
    download_url = resp.json()["data"]["download_url"]

    # alice 能在列表看到
    alice_list = client.get("/api/v1/tasks", headers=alice_h).json()["data"]
    assert any(t["task_id"] == task_id for t in alice_list["tasks"])

    # bob 列表看不到
    bob_list = client.get("/api/v1/tasks", headers=bob_h).json()["data"]
    assert all(t["task_id"] != task_id for t in bob_list["tasks"])

    # bob 详情 404（不泄露存在性）
    resp = client.get(f"/api/v1/tasks/{task_id}", headers=bob_h)
    assert resp.status_code == 404, resp.text

    # bob 下载 404
    resp = client.get(download_url, headers=bob_h)
    assert resp.status_code == 404, resp.text

    # alice 自己可以下载
    resp = client.get(download_url, headers=alice_h)
    assert resp.status_code == 200, resp.text


# =========================================================================== #
# 持久化
# =========================================================================== #
def test_task_persistence_after_restart(client) -> None:
    """任务写入 SQLite 后，新建 TaskManager.load_all 可恢复。"""
    _register(client, "alice", "alice123")
    alice_h = _login(client, "alice", "alice123")

    resp = client.post(
        "/api/v1/convert",
        files={"file": ("tiny.png", _tiny_png(), "image/png")},
        data={"conversion_type": "png_to_pdf"},
        headers=alice_h,
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["data"]["task_id"]

    # 模拟重启：全新的 TaskManager 从同一个数据库文件恢复
    settings = get_settings()
    tm = TaskManager(ttl_hours=24, db_path=settings.db_path)
    restored = tm.load_all()
    assert restored >= 1, "数据库应至少恢复 1 个任务"
    record = tm.get(task_id)
    assert record is not None, f"任务 {task_id} 应能从数据库恢复"
    assert record.user_id is not None, "恢复的任务应带 user_id"
    assert record.status.value == "success", (
        f"任务状态应为 success，实际: {record.status.value}"
    )


def test_user_persistence_after_restart(client) -> None:
    """用户写入 SQLite 后，再次查询仍然存在（重启不丢）。"""
    _register(client, "carol", "carol123")
    # 新的查询路径（模拟重启后首次登录）
    from app.service.user_service import get_user_by_username

    user = get_user_by_username("carol")
    assert user is not None, "重启后用户应仍存在"
    assert user.role == "user"
