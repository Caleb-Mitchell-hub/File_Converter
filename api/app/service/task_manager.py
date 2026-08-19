"""任务管理器。

内存中维护所有任务的状态。生产环境可替换为 Redis / 数据库实现。
提供：
    - 创建任务
    - 更新进度
    - 标记完成 / 失败
    - 查询单个 / 全部
    - 过期清理（基于 TTL）
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.models.enums import ConversionType, TaskStatus
from app.models.schemas import FileResult, TaskInfo


class TaskRecord:
    """单条任务记录（线程安全，异步安全）。"""

    __slots__ = (
        "task_id", "status", "conversion_type", "progress",
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
    ) -> None:
        now = datetime.utcnow()
        self.task_id = task_id
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
        self._lock = asyncio.Lock()

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
    """任务管理器（线程 + 协程安全）。

    设计要点：
        - 用 ``threading.Lock`` 保护 ``_tasks`` dict 的并发读写
        - 内部状态变更走 ``async with record._lock``，避免单任务内并发更新丢失
        - 提供 ``cleanup_expired`` 定期清理过期任务
    """

    def __init__(self, ttl_hours: int = 24) -> None:
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._ttl = timedelta(hours=ttl_hours)

    # ------------------------------------------------------------------ #
    # 创建
    # ------------------------------------------------------------------ #
    def create(
        self,
        task_id: str,
        conversion_type: ConversionType,
        total_files: int = 1,
    ) -> TaskRecord:
        """创建并注册一个任务。"""
        record = TaskRecord(task_id, conversion_type, total_files)
        with self._lock:
            self._tasks[task_id] = record
        return record

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #
    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_all(self, limit: int = 100) -> List[TaskRecord]:
        with self._lock:
            records = sorted(
                self._tasks.values(),
                key=lambda r: r.created_at,
                reverse=True,
            )
            return records[:limit]

    # ------------------------------------------------------------------ #
    # 状态更新（线程安全）
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
        record.status = status
        record.updated_at = datetime.utcnow()
        if error_message is not None:
            record.error_message = error_message
        if status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.PARTIAL_SUCCESS):
            record.finished_at = datetime.utcnow()
            record.progress = 100.0

    def update_progress(
        self,
        task_id: str,
        processed: int,
        total: Optional[int] = None,
    ) -> None:
        record = self.get(task_id)
        if not record:
            return
        record.processed_files = processed
        if total is not None:
            record.total_files = total
        if record.total_files > 0:
            record.progress = round(processed / record.total_files * 100, 2)
        record.updated_at = datetime.utcnow()

    def append_output(self, task_id: str, filename: str) -> None:
        record = self.get(task_id)
        if not record:
            return
        if filename not in record.output_files:
            record.output_files.append(filename)
        record.updated_at = datetime.utcnow()

    def append_file_result(self, task_id: str, result: FileResult) -> None:
        record = self.get(task_id)
        if not record:
            return
        record.file_results.append(result)
        record.updated_at = datetime.utcnow()

    def set_extra(self, task_id: str, key: str, value) -> None:
        record = self.get(task_id)
        if not record:
            return
        record.extra[key] = value
        record.updated_at = datetime.utcnow()

    # ------------------------------------------------------------------ #
    # 清理
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
        return len(expired_ids)

    def delete(self, task_id: str) -> bool:
        with self._lock:
            return self._tasks.pop(task_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._tasks)
