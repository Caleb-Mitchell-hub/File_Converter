
"""SQLite 数据库访问层。

设计：
- 使用标准库 sqlite3，WAL 模式提升并发读写性能。
- 连接通过 threading.local 按线程缓存（sqlite3 连接非线程安全）。
- 写操作立即 commit；任务/用户量级小，无需连接池。
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nickname      TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id          TEXT PRIMARY KEY,
    user_id          INTEGER NOT NULL,
    status           TEXT NOT NULL,
    conversion_type  TEXT NOT NULL,
    progress         REAL NOT NULL DEFAULT 0,
    total_files      INTEGER NOT NULL DEFAULT 1,
    processed_files  INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    finished_at      TEXT,
    error_message    TEXT,
    output_files     TEXT NOT NULL DEFAULT '[]',
    file_results     TEXT NOT NULL DEFAULT '[]',
    extra            TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, created_at);
"""

_local = threading.local()


def get_connection(db_path: Path) -> sqlite3.Connection:
    """获取当前线程的 SQLite 连接（首次使用时创建并缓存）。

    缓存按 db_path 隔离：当数据库路径变化（如测试切换临时库）时
    自动重建连接，避免误用指向旧文件的连接。
    """
    db_path = Path(db_path)
    conn: sqlite3.Connection | None = getattr(_local, "conn", None)
    conn_path: str | None = getattr(_local, "conn_path", None)
    if conn is not None and conn_path == str(db_path):
        return conn
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _local.conn = conn
    _local.conn_path = str(db_path)
    return conn


def init_db(db_path: Path) -> None:
    """建表（幂等）。应用启动时调用一次。"""
    conn = get_connection(db_path)
    conn.executescript(_SCHEMA)
    conn.commit()
