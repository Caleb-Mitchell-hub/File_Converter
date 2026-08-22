
"""用户服务：基于 SQLite 的用户 CRUD 与认证查询。

提供：
- 创建用户（密码加盐哈希存储）
- 按用户名 / id 查询
- 用户名密码校验（authenticate）
- 预置默认管理员（首次启动时）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.db import get_connection
from app.security import hash_password, verify_password


@dataclass
class User:
    """用户记录（内存表示，对应 users 表一行）。"""

    id: int
    username: str
    password_hash: str
    nickname: str
    role: str
    created_at: datetime

    def to_public(self) -> dict:
        """对外暴露的安全字段（不含密码哈希）。"""
        return {
            "id": str(self.id),
            "username": self.username,
            "nickname": self.nickname,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }


def _row_to_user(row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        nickname=row["nickname"],
        role=row["role"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def get_user_by_username(username: str) -> Optional[User]:
    conn = get_connection(get_settings().db_path)
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: int) -> Optional[User]:
    conn = get_connection(get_settings().db_path)
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def create_user(
    username: str,
    password: str,
    nickname: str = "",
    role: str = "user",
) -> User:
    """创建用户。用户名重复会抛 sqlite3.IntegrityError（由调用方处理）。"""
    conn = get_connection(get_settings().db_path)
    password_hash = hash_password(password)
    created_at = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, nickname, role, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, nickname or username, role, created_at),
    )
    conn.commit()
    user = get_user_by_id(cur.lastrowid)
    if user is None:  # pragma: no cover - 理论不可达
        raise RuntimeError("用户创建后查询失败")
    return user


def authenticate(username: str, password: str) -> Optional[User]:
    """校验用户名 + 密码，成功返回 User，失败返回 None。"""
    user = get_user_by_username(username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def ensure_default_admin() -> None:
    """预置默认管理员（不存在时创建）。配置见 .env 的 DEFAULT_ADMIN_*。"""
    settings = get_settings()
    if get_user_by_username(settings.default_admin_username) is None:
        create_user(
            username=settings.default_admin_username,
            password=settings.default_admin_password,
            nickname="管理员",
            role="admin",
        )
