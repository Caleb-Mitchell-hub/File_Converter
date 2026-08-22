"""任务查询与文件下载路由。

提供：
    - ``GET    /api/v1/tasks``                     任务列表
    - ``GET    /api/v1/tasks/{task_id}``           查询单个任务
    - ``GET    /api/v1/tasks/{task_id}/download``           批量：下载 zip
    - ``GET    /api/v1/tasks/{task_id}/download/{filename}`` 单文件：下载指定文件
    - ``DELETE /api/v1/tasks/{task_id}``           删除任务（含输出 / 上传文件）

**安全**：所有文件操作前必须用 ``Path.resolve()`` 校验父目录，
防止 ``..`` 路径穿越落到 settings.output_dir 之外。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse

from app.api.dependencies import get_current_user, settings_dep, task_manager_dep
from app.service.user_service import User
from app.config import Settings
from app.models.enums import TaskStatus
from app.models.schemas import (
    APIResponse,
    FileResult,
    TaskInfo,
    TaskListResponse,
)
from app.service.task_manager import TaskManager
from app.utils.file_utils import safe_delete
from app.utils.logger import get_logger

router = APIRouter()
log = get_logger("api.routes.tasks")


# ---------------------------------------------------------------------- #
# 工具：安全解析 + 路径穿越校验
# ---------------------------------------------------------------------- #
def _safe_resolve(base_dir: Path, *parts: str) -> Path:
    """把 parts 拼到 base_dir 之下，resolve 后校验仍在 base_dir 之内。

    Raises:
        HTTPException 400: 路径穿越。
    """
    base_resolved = base_dir.resolve()
    target = (base_dir.joinpath(*parts)).resolve()
    try:
        # Python 3.9+ : is_relative_to
        target.relative_to(base_resolved)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"非法路径: {target}",
        ) from exc
    return target


def _build_download_url(task_id: str, record, settings: Settings) -> Optional[str]:
    """根据任务状态和类型决定 download_url。"""
    if record.status not in (TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS):
        return None

    is_batch = bool(record.extra.get("is_batch"))
    if is_batch:
        # 批量：指向 zip 或多文件列表入口
        return f"/api/v1/tasks/{task_id}/download"
    else:
        # 单文件：拿 output_files[0]
        if record.output_files:
            return f"/api/v1/tasks/{task_id}/download/{record.output_files[0]}"
        return None


# ---------------------------------------------------------------------- #
# 任务列表
# ---------------------------------------------------------------------- #
@router.get(
    "/tasks",
    response_model=APIResponse,
    summary="任务列表",
    description="按创建时间倒序返回最近的任务记录。",
)
async def list_tasks(
    limit: int = Query(50, ge=1, le=500, description="返回的最大条数"),
    tm: TaskManager = Depends(task_manager_dep),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """列出当前用户的最近任务（数据隔离）。"""
    from app.config import get_settings  # 局部导入，避免循环

    settings = get_settings()
    records = tm.list_all(limit=limit, user_id=user.id)
    tasks = [
        r.to_info(download_url=_build_download_url(r.task_id, r, settings))
        for r in records
    ]

    resp = TaskListResponse(total=len(tasks), tasks=tasks)
    return APIResponse(code=0, message="ok", data=resp.model_dump())


# ---------------------------------------------------------------------- #
# 单个任务详情
# ---------------------------------------------------------------------- #
@router.get(
    "/tasks/{task_id}",
    response_model=APIResponse,
    summary="查询单个任务",
)
async def get_task(
    task_id: str,
    tm: TaskManager = Depends(task_manager_dep),
    settings: Settings = Depends(settings_dep),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """查询任务详情。

    404: 任务不存在或已被清理。
    """
    record = tm.get(task_id)
    if not record or record.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在或已过期: {task_id}",
        )

    info: TaskInfo = record.to_info(download_url=_build_download_url(task_id, record, settings))
    return APIResponse(code=0, message="ok", data=info.model_dump())


# ---------------------------------------------------------------------- #
# 下载：批量（zip） / 单文件（指定 filename）
# ---------------------------------------------------------------------- #
@router.get(
    "/tasks/{task_id}/download",
    summary="下载批量任务产物（zip）",
    description="任务为批量且 zip_output=True 时返回 zip 包。",
)
async def download_batch(
    task_id: str,
    tm: TaskManager = Depends(task_manager_dep),
    settings: Settings = Depends(settings_dep),
    user: User = Depends(get_current_user),
):
    """下载批量转换结果。

    优先从 extra.zip_path 取（__run_batch_task 写入）；
    若不存在则尝试在 output_dir 下匹配 ``{task_id}*.zip``。
    """
    record = tm.get(task_id)
    if not record or record.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}",
        )
    if record.status not in (TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务尚未完成: status={record.status.value}",
        )

    # 优先用 extra.zip_path
    zip_path_str: Optional[str] = record.extra.get("zip_path")
    zip_path: Optional[Path] = None
    if zip_path_str:
        candidate = Path(zip_path_str)
        # 防穿越
        try:
            zip_path = _safe_resolve(settings.output_dir / str(user.id), candidate.name)
        except HTTPException:
            zip_path = None
        if zip_path is None or not zip_path.exists():
            # 退而求其次：直接信任记录里的路径（但仍要校验父目录）
            parent = candidate.resolve().parent
            try:
                parent.relative_to((settings.output_dir / str(user.id)).resolve())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="zip 路径不在 output_dir 之内",
                )
            zip_path = candidate if candidate.exists() else None

    if zip_path is None or not zip_path.exists():
        # 兜底：在 output_dir 下找任何与 task 相关的 zip
        output_dir = (settings.output_dir / str(user.id)).resolve()
        for cand in output_dir.rglob("*.zip"):
            if task_id[:8] in cand.name:
                zip_path = cand
                break

    if zip_path is None or not zip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到打包文件",
        )

    log.info("下载批量结果: %s -> %s", task_id, zip_path.name)
    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip",
    )


@router.get(
    "/tasks/{task_id}/download/{filename}",
    summary="下载单文件任务产物",
    description="任务为单文件时，下载指定文件名的产物。",
)
async def download_single(
    task_id: str,
    filename: str,
    tm: TaskManager = Depends(task_manager_dep),
    settings: Settings = Depends(settings_dep),
    user: User = Depends(get_current_user),
):
    """下载单文件转换产物。"""
    record = tm.get(task_id)
    if not record or record.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}",
        )
    if record.status not in (TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务尚未完成: status={record.status.value}",
        )

    # 防路径穿越（用户专属输出目录）
    target = _safe_resolve(settings.output_dir / str(user.id), filename)
    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件不存在: {filename}",
        )

    # 额外校验：filename 必须在该任务的 output_files 内（防止猜到其他文件）
    if record.output_files and filename not in record.output_files:
        log.warning(
            "下载文件名不匹配 task=%s: 请求=%s, 实际=%s",
            task_id,
            filename,
            record.output_files,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该文件不属于此任务",
        )

    log.info("下载文件: %s/%s", task_id, filename)
    # 推断 media_type
    media_type = _guess_media_type(filename)
    return FileResponse(
        path=str(target),
        filename=filename,
        media_type=media_type,
    )


def _guess_media_type(filename: str) -> str:
    """根据扩展名猜测 media_type。"""
    ext = Path(filename).suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".zip": "application/zip",
    }.get(ext, "application/octet-stream")


# ---------------------------------------------------------------------- #
# 删除任务
# ---------------------------------------------------------------------- #
@router.delete(
    "/tasks/{task_id}",
    response_model=APIResponse,
    summary="删除任务",
    description="清理任务记录、输出文件、上传文件（如可定位）。",
)
async def delete_task(
    task_id: str,
    tm: TaskManager = Depends(task_manager_dep),
    settings: Settings = Depends(settings_dep),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """删除任务。

    行为：
        - 删除 TaskManager 中的记录
        - 删除 output_dir 下属于该任务的产物（按 output_files 名字精确匹配）
        - 尝试删除 upload_dir 下的源文件（按 record.extra.source_path 列表）
    """
    record = tm.get(task_id)
    if not record or record.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}",
        )

    cleaned_outputs: list[str] = []
    cleaned_uploads: list[str] = []

    # 1. 清理输出文件（用户专属输出目录）
    output_dir = (settings.output_dir / str(user.id)).resolve()
    for fname in record.output_files:
        try:
            target = _safe_resolve(output_dir, fname)
        except HTTPException:
            continue
        if target.exists() and target.is_file():
            safe_delete(target)
            cleaned_outputs.append(fname)
        elif target.exists() and target.is_dir():
            # 可能是批量子目录
            safe_delete(target)
            cleaned_outputs.append(fname)

    # 2. 清理源文件（单文件 / 批量都能用，用户专属上传目录）
    upload_dir = (settings.upload_dir / str(user.id)).resolve()
    source_paths = record.extra.get("source_paths") or []
    if not source_paths and record.extra.get("source_path"):
        source_paths = [record.extra["source_path"]]
    for sp in source_paths:
        p = Path(sp)
        try:
            target = _safe_resolve(upload_dir, p.name)
        except HTTPException:
            continue
        if target.exists():
            safe_delete(target)
            cleaned_uploads.append(p.name)

    # 3. 删除记录
    tm.delete(task_id)

    log.info(
        "删除任务 %s: outputs=%s, uploads=%s",
        task_id,
        cleaned_outputs,
        cleaned_uploads,
    )
    return APIResponse(
        code=0,
        message="ok",
        data={
            "task_id": task_id,
            "cleaned_outputs": cleaned_outputs,
            "cleaned_uploads": cleaned_uploads,
        },
    )
