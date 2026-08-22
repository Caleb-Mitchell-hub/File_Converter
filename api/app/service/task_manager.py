
"""任务管理器（SQLite 持久化）。

设计：
- 内存维护 _tasks dict 保证读写速度；每次变更同步持久化到 SQLite
  （INSERT OR REPLACE），重启后通过 load_all() 恢复。
- 每个任务归属一个 user_id，查询/下载/删除接口按用户隔离。
- 状态机：PENDING -> RUNNING -> (SUCCESS | PARTIAL_SUCCESS | FAILED)
- 过期清理基于 TTL，同时删除内存与数据库记录。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from app.db import get_connection
from app.models.enums import ConversionType, TaskStatus
from app.models.schemas import FileResult, TaskInfo


class TaskRecord:
    """单条任务记录（线程安全，异步安全）。"""

    __slots__ = (
        "task_id", "user_id", "status", "conversion_type", "progress",
        "total_files", "processed_files",
        "created_at", "updated_at", "finished_at",
        "error_message", "output_files", "file_results", "extra",
        "_lock",
    )

    def __init__(
        self,
        task_id: str,
        conversion_type: ConversionType,
        total_files: int = 1,
        user_id: Optional[int] = None,
    ) -> None:
        now = datetime.utcnow()
        self.task_id = task_id
        self.user_id: Optional[int] = user_id
        self.status: TaskStatus = TaskStatus.PENDING
        self.conversion_type = conversion_type
        self.progress: float = 0.0
        self.total_files = total_files
        self.processed_files = 0
        self.created_at = now
        self.updated_at = now
        self.finished_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.output_files: List[str] = []
        self.file_results: List[FileResult] = []
        self.extra: dict = {}
        self._lock = threading.Lock()

    def to_info(self, download_url: Optional[str] = None) -> TaskInfo:
        return TaskInfo(
            task_id=self.task_id,
            status=self.status,
            conversion_type=self.conversion_type,
            progress=self.progress,
            total_files=self.total_files,
            processed_files=self.processed_files,
            created_at=self.created_at,
            updated_at=self.updated_at,
            finished_at=self.finished_at,
            error_message=self.error_message,
            output_files=list(self.output_files),
            download_url=download_url,
            extra=dict(self.extra),
        )


class TaskManager:
    """任务管理器（线程安全 + SQLite 持久化）。"""

    def __init__(self, ttl_hours: int = 24, db_path: Optional[Path] = None) -> None:
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._ttl = timedelta(hours=ttl_hours)
        self._db_path: Optional[Path] = db_path

    # ------------------------------------------------------------------ #
    # 持久化
    # ------------------------------------------------------------------ #
    def _persist(self, record: TaskRecord) -> None:
        """把单条任务写入 SQLite（INSERT OR REPLACE）。"""
        if self._db_path is None:
            return
        conn = get_connection(self._db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO tasks (
                task_id, user_id, status, conversion_type, progress,
                total_files, processed_files, created_at, updated_at,
                finished_at, error_message, output_files, file_results, extra
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.task_id,
                record.user_id,
                record.status.value,
                record.conversion_type.value,
                record.progress,
                record.total_files,
                record.processed_files,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                record.finished_at.isoformat() if record.finished_at else None,
                record.error_message,
                json.dumps(record.output_files, ensure_ascii=False),
                json.dumps(
                    [f.model_dump() for f in record.file_results],
                    ensure_ascii=False,
                ),
                json.dumps(record.extra, ensure_ascii=False),
            ),
        )
        conn.commit()

    def load_all(self) -> int:
        """从数据库恢复全部任务到内存。返回恢复数量。"""
        if self._db_path is None:
            return 0
        conn = get_connection(self._db_path)
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        with self._lock:
            self._tasks.clear()
            for row in rows:
                record = TaskRecord(
                    task_id=row["task_id"],
                    conversion_type=ConversionType(row["conversion_type"]),
                    total_files=row["total_files"],
                    user_id=row["user_id"],
                )
                record.status = TaskStatus(row["status"])
                record.progress = row["progress"]
                record.processed_files = row["processed_files"]
                record.created_at = datetime.fromisoformat(row["created_at"])
                record.updated_at = datetime.fromisoformat(row["updated_at"])
                record.finished_at = (
                    datetime.fromisoformat(row["finished_at"])
                    if row["finished_at"] else None
                )
                record.error_message = row["error_message"]
                record.output_files = json.loads(row["output_files"])
                record.file_results = [
                    FileResult(**f) for f in json.loads(row["file_results"])
                ]
                record.extra = json.loads(row["extra"])
                self._tasks[record.task_id] = record
        return len(rows)

    # ------------------------------------------------------------------ #
    # 创建
    # ------------------------------------------------------------------ #
    def create(
        self,
        task_id: str,
        conversion_type: ConversionType,
        total_files: int = 1,
        user_id: Optional[int] = None,
    ) -> TaskRecord:
        """创建并注册一个任务（立即持久化）。"""
        record = TaskRecord(task_id, conversion_type, total_files, user_id)
        with self._lock:
            self._tasks[task_id] = record
        self._persist(record)
        return record

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_all(
        self, limit: int = 100, user_id: Optional[int] = None
    ) -> List[TaskRecord]:
        """按创建时间倒序返回任务。

        Args:
            user_id: 指定时只返回该用户的任务（数据隔离）。
        """
        with self._lock:
            records = [
                r for r in self._tasks.values()
                if user_id is None or r.user_id == user_id
            ]
            records.sort(key=lambda r: r.created_at, reverse=True)
            return records[:limit]

    # ------------------------------------------------------------------ #
    # 状态更新（线程安全 + 持久化）
    # ------------------------------------------------------------------ #
    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        error_message: Optional[str] = None,
    ) -> None:
        record = self.get(task_id)
        if not record:
            return
        with record._lock:
            record.status = status
            record.updated_at = datetime.utcnow()
            if error_message is not None:
                record.error_message = error_message
            if status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.PARTIAL_SUCCESS):
                record.finished_at = datetime.utcnow()
                record.progress = 100.0
        self._persist(record)

    def update_progress(
        self,
        task_id: str,
        processed: int,
        total: Optional[int] = None,
    ) -> None:
        record = self.get(task_id)
        if not record:
            return
        with record._lock:
            record.processed_files = processed
            if total is not None:
                record.total_files = total
            if record.total_files > 0:
                record.progress = round(processed / record.total_files * 100, 2)
            record.updated_at = datetime.utcnow()
        self._persist(record)

    def append_output(self, task_id: str, filename: str) -> None:
        record = self.get(task_id)
        if not record:
            return
        with record._lock:
            if filename not in record.output_files:
                record.output_files.append(filename)
            record.updated_at = datetime.utcnow()
        self._persist(record)

    def append_file_result(self, task_id: str, result: FileResult) -> None:
        record = self.get(task_id)
        if not record:
            return
        with record._lock:
            record.file_results.append(result)
            record.updated_at = datetime.utcnow()
        self._persist(record)

    def set_extra(self, task_id: str, key: str, value) -> None:
        record = self.get(task_id)
        if not record:
            return
        with record._lock:
            record.extra[key] = value
            record.updated_at = datetime.utcnow()
        self._persist(record)

    # ------------------------------------------------------------------ #
    # 清理 / 删除
    # ------------------------------------------------------------------ #
    def cleanup_expired(self) -> int:
        """清理超过 TTL 的已完成任务。返回清理数量。"""
        now = datetime.utcnow()
        expired_ids: List[str] = []
        with self._lock:
            for tid, record in self._tasks.items():
                if record.finished_at and (now - record.finished_at) > self._ttl:
                    expired_ids.append(tid)
            for tid in expired_ids:
                del self._tasks[tid]
        if expired_ids and self._db_path is not None:
            conn = get_connection(self._db_path)
            conn.executemany(
                "DELETE FROM tasks WHERE task_id = ?",
                [(tid,) for tid in expired_ids],
            )
            conn.commit()
        return len(expired_ids)

    def delete(self, task_id: str) -> bool:
        with self._lock:
            removed = self._tasks.pop(task_id, None) is not None
        if removed and self._db_path is not None:
            conn = get_connection(self._db_path)
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
        return removed

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()
        if self._db_path is not None:
            conn = get_connection(self._db_path)
            conn.execute("DELETE FROM tasks")
            conn.commit()

    def __len__(self) -> int:
        with self._lock:
            return len(self._tasks)
