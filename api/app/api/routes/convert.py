"""转换接口路由。

暴露两个核心端点：
    - ``POST /api/v1/convert``      单文件转换（同步返回结果）
    - ``POST /api/v1/convert/batch`` 批量转换（异步后台执行，立即返回 task_id）

单文件 vs 批量的设计差异：
    - 单文件：体量小、耗时相对可控，**同步**执行并直接返回文件结果。
      但仍用 task 包装，方便前端用统一的"任务"模型处理。
    - 批量：文件数 / 单文件大小都可能很大，**真正异步**执行：
      1. 立刻保存所有上传文件
      2. 创建 task 记录
      3. 用 ``asyncio.create_task`` 启动后台协程
      4. 立刻返回 task_id，客户端轮询 ``/api/v1/tasks/{task_id}``
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.api.dependencies import (
    conversion_service_dep,
    get_current_user,
    settings_dep,
    task_manager_dep,
)
from app.service.user_service import User
from app.config import Settings
from app.models.enums import ConversionType, TaskStatus
from app.models.schemas import APIResponse, FileResult
from app.service.conversion_service import (
    ConversionExecutionError,
    ConversionService,
    ConversionValidationError,
)
from app.service.task_manager import TaskManager
from app.utils.file_utils import (
    ensure_dir,
    generate_task_id,
    get_file_size_mb,
    human_readable_size,
    is_extension_allowed,
    safe_delete,
    safe_filename,
    secure_unique_name,
)
from app.utils.logger import get_logger

router = APIRouter()
log = get_logger("api.routes.convert")


# ---------------------------------------------------------------------- #
# 工具：统一的成功 / 错误响应工厂
# ---------------------------------------------------------------------- #
def _ok(data: Optional[dict] = None, message: str = "ok") -> dict:
    """构造统一成功响应。"""
    return {"code": 0, "message": message, "data": data or {}}


# ---------------------------------------------------------------------- #
# 工具：保存上传文件
# ---------------------------------------------------------------------- #
async def _save_upload(
    upload: UploadFile,
    dest_dir: Path,
    max_size_bytes: int,
) -> Path:
    """把 UploadFile 流式保存到 dest_dir。

    边读边累计大小，超过 ``max_size_bytes`` 立即中止并抛 413。
    返回最终落盘的绝对路径。
    """
    ensure_dir(dest_dir)
    saved_name = secure_unique_name(upload.filename or "unnamed")
    dest_path = dest_dir / saved_name

    bytes_written = 0
    try:
        with dest_path.open("wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_size_bytes:
                    out.close()
                    safe_delete(dest_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"文件过大: {human_readable_size(bytes_written)} > "
                            f"{human_readable_size(max_size_bytes)}"
                        ),
                    )
                out.write(chunk)
    finally:
        await upload.close()

    return dest_path


# ---------------------------------------------------------------------- #
# 单文件转换
# ---------------------------------------------------------------------- #
@router.post(
    "/convert",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="单文件转换（同步）",
    description=(
        "上传单个文件并立即转换，返回结果 + task 包装。\n\n"
        "**适用场景**：文件较小、可接受秒级等待。\n"
        "**返回字段**：`download_url` 可用于下载产物。"
    ),
)
async def convert_single(
    file: UploadFile = File(..., description="待转换的源文件"),
    conversion_type: ConversionType = Form(..., description="转换类型枚举"),
    target_filename: Optional[str] = Form(None, description="可选自定义输出文件名"),
    dpi: Optional[int] = Form(None, ge=72, le=2400, description="图片渲染 DPI"),
    jpg_quality: Optional[int] = Form(None, ge=1, le=100, description="JPG 质量"),
    overwrite: bool = Form(False, description="是否覆盖已存在的目标文件"),
    settings: Settings = Depends(settings_dep),
    tm: TaskManager = Depends(task_manager_dep),
    converter: ConversionService = Depends(conversion_service_dep),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """单文件转换端点（同步）。

    流程：
        1. 校验扩展名 + 大小
        2. 落地到 upload_dir
        3. 创建 task 记录（status=pending）
        4. 同步调用 conversion_service.convert_single
        5. 成功 → 写 task 状态 = success；返回 download_url
           失败 → 写 task 状态 = failed；抛 HTTPException 500
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名为空",
        )

    # 1. 扩展名校验（既要全局白名单，也要匹配 conversion_type 期望）
    if not is_extension_allowed(file.filename, settings.allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {Path(file.filename).suffix}",
        )
    if not is_extension_allowed(file.filename, [conversion_type.source_ext_dot]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"源文件扩展名与转换类型不匹配: "
                f"文件={Path(file.filename).suffix}, 期望={conversion_type.source_ext_dot}"
            ),
        )

    # 2. 保存文件
    try:
        saved_path = await _save_upload(
            file,
            dest_dir=settings.upload_dir,
            max_size_bytes=settings.max_upload_size_bytes,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("保存上传文件失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存上传文件失败: {exc}",
        ) from exc

    saved_size = saved_path.stat().st_size
    log.info(
        "单文件转换: task 接收 filename=%s, type=%s, size=%.2fMB",
        saved_path.name,
        conversion_type.value,
        get_file_size_mb(saved_path),
    )

    # 3. 创建 task 记录
    task_id = generate_task_id()
    record = tm.create(task_id, conversion_type, total_files=1, user_id=user.id)
    record.extra.update(
        {
            "source_filename": saved_path.name,
            "source_path": str(saved_path),
            "is_batch": False,
        }
    )
    tm.update_status(task_id, TaskStatus.RUNNING)

    # 4. 同步执行转换（带进度回调 → 写回 task_record.progress / extra）
    def _on_file_progress(processed: int, total: int) -> None:
        tm.update_progress(task_id, processed, total)

    def _on_page_progress(processed: int, total: int) -> None:
        """页级进度：写入 ``task.extra.current_page / total_page``，
        用于前端展示「解析第 N/M 页」。
        单文件路径里 processed == 当前页号；total == 总页数。"""
        tm.set_extra(task_id, "current_page", processed)
        tm.set_extra(task_id, "total_pages", total)
        # 文件级百分比也跟着刷新，方便前端显示底部条
        if total > 0:
            tm.update_progress(task_id, processed, total)

    try:
        output_path, file_result = await converter.convert_single(
            source_path=saved_path,
            conversion_type=conversion_type,
            target_filename=target_filename,
            dpi=dpi,
            jpg_quality=jpg_quality,
            overwrite=overwrite,
            on_progress=_on_page_progress,
            output_dir=settings.output_dir / str(user.id),
        )
    except (ConversionValidationError, ConversionExecutionError) as exc:
        log.error("转换失败: %s - %s", saved_path.name, exc)
        tm.update_status(task_id, TaskStatus.FAILED, error_message=str(exc))
        # 失败时清理上传文件，避免占盘
        safe_delete(saved_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        log.exception("转换未预期异常: %s", exc)
        tm.update_status(task_id, TaskStatus.FAILED, error_message=str(exc))
        safe_delete(saved_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"转换失败: {exc}",
        ) from exc

    # 5. 写 task 状态
    tm.append_output(task_id, output_path.name)
    tm.append_file_result(task_id, file_result)
    tm.set_extra(task_id, "output_path", str(output_path))
    tm.set_extra(task_id, "output_size", output_path.stat().st_size)
    tm.update_status(task_id, TaskStatus.SUCCESS)

    # 6. 组装响应
    data = {
        "task_id": task_id,
        "status": TaskStatus.SUCCESS.value,
        "source_filename": saved_path.name,
        "output_filename": output_path.name,
        "download_url": f"/api/v1/tasks/{task_id}/download/{output_path.name}",
        "file_size": output_path.stat().st_size,
        "file_size_human": human_readable_size(output_path.stat().st_size),
    }
    return APIResponse(code=0, message="ok", data=data)


# ---------------------------------------------------------------------- #
# 单文件后台执行（异步端点，复用批量任务的 _run_batch_task 模型）
# ---------------------------------------------------------------------- #
async def _run_single_task(
    task_id: str,
    saved_path: Path,
    conversion_type: ConversionType,
    target_filename: Optional[str],
    dpi: Optional[int],
    jpg_quality: Optional[int],
    overwrite: bool,
    tm: TaskManager,
    converter: ConversionService,
    output_dir: Optional[Path] = None,
) -> None:
    """单文件异步路径：与批量行为完全一致；状态机从 PENDING 切到 RUNNING。"""
    try:

        def _on_page_progress(processed: int, total: int) -> None:
            tm.set_extra(task_id, "current_page", processed)
            tm.set_extra(task_id, "total_pages", total)
            if total > 0:
                tm.update_progress(task_id, processed, total)

        tm.update_status(task_id, TaskStatus.RUNNING)

        output_path, file_result = await converter.convert_single(
            source_path=saved_path,
            conversion_type=conversion_type,
            target_filename=target_filename,
            dpi=dpi,
            jpg_quality=jpg_quality,
            overwrite=overwrite,
            on_progress=_on_page_progress,
            output_dir=output_dir,
        )

        tm.append_output(task_id, output_path.name)
        tm.append_file_result(task_id, file_result)
        tm.set_extra(task_id, "output_path", str(output_path))
        tm.set_extra(task_id, "output_size", output_path.stat().st_size)
        tm.update_status(task_id, TaskStatus.SUCCESS)
        log.info("异步单文件完成: %s -> %s", task_id, output_path.name)
    except Exception as exc:
        log.exception("异步单文件失败: %s - %s", task_id, exc)
        try:
            tm.update_status(task_id, TaskStatus.FAILED, error_message=str(exc))
        except Exception:  # pragma: no cover
            pass


@router.post(
    "/convert/async",
    response_model=APIResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="单文件转换（异步，立即返回 task_id）",
    description=(
        "上传单个文件并**立即**返回 task_id，后台执行转换。\n\n"
        "**适用场景**：PDF → DOCX 等需要秒级以上的转换；前端可基于 task_id "
        "轮询 `/api/v1/tasks/{task_id}` 实时显示进度（含 PDF 页级进度）。\n\n"
        "**进度字段**：`progress` 表示文件级进度；对于 PDF→DOCX，"
        "``extra.current_page / extra.total_pages`` 显示已解析到第几页 / 总页数。"
    ),
)
async def convert_single_async(
    file: UploadFile = File(..., description="待转换的源文件"),
    conversion_type: ConversionType = Form(..., description="转换类型枚举"),
    target_filename: Optional[str] = Form(None),
    dpi: Optional[int] = Form(None, ge=72, le=2400),
    jpg_quality: Optional[int] = Form(None, ge=1, le=100),
    overwrite: bool = Form(False),
    settings: Settings = Depends(settings_dep),
    tm: TaskManager = Depends(task_manager_dep),
    converter: ConversionService = Depends(conversion_service_dep),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """单文件异步端点：先创建 PENDING task，立刻返回 task_id。"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名为空",
        )
    if not is_extension_allowed(file.filename, settings.allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {Path(file.filename).suffix}",
        )
    if not is_extension_allowed(file.filename, [conversion_type.source_ext_dot]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"源文件扩展名与转换类型不匹配: "
                f"文件={Path(file.filename).suffix}, 期望={conversion_type.source_ext_dot}"
            ),
        )

    # 保存文件
    try:
        saved_path = await _save_upload(
            file,
            dest_dir=settings.upload_dir,
            max_size_bytes=settings.max_upload_size_bytes,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("异步单文件保存失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存上传文件失败: {exc}",
        ) from exc

    # 创建 task（PENDING），把任务丢到后台协程
    task_id = generate_task_id()
    record = tm.create(task_id, conversion_type, total_files=1, user_id=user.id)
    record.extra.update(
        {
            "source_filename": saved_path.name,
            "source_path": str(saved_path),
            "is_batch": False,
            "is_single_async": True,
            "total_pages": None,
            "current_page": 0,
        }
    )

    asyncio.create_task(
        _run_single_task(
            task_id=task_id,
            saved_path=saved_path,
            conversion_type=conversion_type,
            target_filename=target_filename,
            dpi=dpi,
            jpg_quality=jpg_quality,
            overwrite=overwrite,
            tm=tm,
            converter=converter,
            output_dir=settings.output_dir / str(user.id),
        )
    )

    log.info(
        "异步单文件任务已入队: %s, file=%s, type=%s",
        task_id,
        saved_path.name,
        conversion_type.value,
    )

    data = {
        "task_id": task_id,
        "status": TaskStatus.PENDING.value,
        "total_files": 1,
        "message": "已接收任务，请轮询进度",
        "query_url": f"/api/v1/tasks/{task_id}",
    }
    return APIResponse(code=0, message="accepted", data=data)


# ---------------------------------------------------------------------- #
# 后台批量任务执行函数
# ---------------------------------------------------------------------- #
async def _run_batch_task(
    task_id: str,
    file_paths: List[Path],
    conversion_type: ConversionType,
    target_subdir: Optional[str],
    dpi: Optional[int],
    jpg_quality: Optional[int],
    overwrite: bool,
    zip_output: bool,
    tm: TaskManager,
    converter: ConversionService,
    output_dir: Optional[Path] = None,
) -> None:
    """真正执行批量转换的后台协程。

    状态机：
        PENDING -> RUNNING -> (SUCCESS | PARTIAL_SUCCESS | FAILED)
    """
    try:
        tm.update_status(task_id, TaskStatus.RUNNING)

        def _on_progress(processed: int, total: int) -> None:
            tm.update_progress(task_id, processed, total)

        def _on_page_progress(filename: str, processed: int, total: int) -> None:
            """批量任务内「当前文件 + 页号」二级进度。

            写入 ``task.extra`` 供前端展示，例如::

                current_file:  "interview.pdf"
                current_page:  45
                total_pages:   269
            """
            tm.set_extra(task_id, "current_file", filename)
            tm.set_extra(task_id, "current_page", processed)
            tm.set_extra(task_id, "total_pages", total)

        results, zip_path = await converter.convert_batch(
            source_paths=file_paths,
            conversion_type=conversion_type,
            target_subdir=target_subdir,
            dpi=dpi,
            jpg_quality=jpg_quality,
            overwrite=overwrite,
            zip_output=zip_output,
            on_progress=_on_progress,
            on_page_progress=_on_page_progress,
            output_dir=output_dir,
        )

        # 把每个文件的结果写入 task
        for r in results:
            tm.append_file_result(task_id, r)
            if r.success and r.output_filename:
                tm.append_output(task_id, r.output_filename)

        if zip_path is not None:
            tm.append_output(task_id, zip_path.name)
            tm.set_extra(task_id, "zip_path", str(zip_path))
            tm.set_extra(task_id, "zip_size", zip_path.stat().st_size)

        # 决定终态
        n_ok = sum(1 for r in results if r.success)
        n_fail = len(results) - n_ok
        if n_ok == 0:
            # 全部失败：把所有失败原因汇总到 error_message
            first_reason = (
                next((r.message for r in results if not r.success), "") or "未知错误"
            )
            tm.update_status(
                task_id,
                TaskStatus.FAILED,
                error_message=(
                    f"所有 {len(results)} 个文件转换失败。"
                    f"首个原因：{first_reason}"[:1000]
                ),
            )
        elif n_ok < len(results):
            # 部分成功：把失败原因汇总展示
            fail_reasons = [
                f"{r.source_filename}: {r.message}"
                for r in results
                if not r.success
            ]
            summary = (
                f"{n_ok}/{len(results)} 个文件成功，{n_fail} 个失败。"
                f"失败原因：\n" + "\n".join(f"  - {x}" for x in fail_reasons[:10])
            )[:1000]
            tm.update_status(
                task_id,
                TaskStatus.PARTIAL_SUCCESS,
                error_message=summary,
            )
        else:
            tm.update_status(task_id, TaskStatus.SUCCESS)

        log.info(
            "批量任务完成: %s, 成功=%d/%d",
            task_id,
            n_ok,
            len(results),
        )
    except Exception as exc:
        log.exception("批量任务异常: %s - %s", task_id, exc)
        try:
            tm.update_status(task_id, TaskStatus.FAILED, error_message=str(exc))
        except Exception:  # pragma: no cover
            pass


# ---------------------------------------------------------------------- #
# 批量转换
# ---------------------------------------------------------------------- #
@router.post(
    "/convert/batch",
    response_model=APIResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="批量文件转换（异步）",
    description=(
        "上传多个文件并异步转换，立即返回 task_id。\n\n"
        "**适用场景**：文件多 / 大，需要后台处理。\n"
        "**后续**：用 task_id 轮询 `/api/v1/tasks/{task_id}` 获取进度与下载链接。"
    ),
)
async def convert_batch(
    files: List[UploadFile] = File(..., description="待转换的文件列表（multipart 字段名=files）"),
    conversion_type: ConversionType = Form(..., description="转换类型枚举"),
    target_subdir: Optional[str] = Form(None, description="可选输出子目录名"),
    dpi: Optional[int] = Form(None, ge=72, le=2400),
    jpg_quality: Optional[int] = Form(None, ge=1, le=100),
    overwrite: bool = Form(False),
    zip_output: bool = Form(True, description="是否把结果打包为 zip"),
    settings: Settings = Depends(settings_dep),
    tm: TaskManager = Depends(task_manager_dep),
    converter: ConversionService = Depends(conversion_service_dep),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """批量转换端点（异步）。

    流程：
        1. 校验文件数 ≤ max_batch_files
        2. 校验每个文件扩展名
        3. 全部保存到 upload_dir
        4. 创建 task（PENDING）
        5. asyncio.create_task 启动后台协程
        6. 立刻返回 task_id
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供文件",
        )

    if len(files) > settings.max_batch_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"批量文件数超过限制: {len(files)} > {settings.max_batch_files}"
            ),
        )

    # 扩展名校验（先全部过一遍再保存）
    for f in files:
        if not f.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空",
            )
        if not is_extension_allowed(f.filename, settings.allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {f.filename}",
            )
        if not is_extension_allowed(f.filename, [conversion_type.source_ext_dot]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"源文件扩展名不匹配: {f.filename} -> {conversion_type.source_ext_dot}"
                ),
            )

    # 保存所有文件
    saved_paths: List[Path] = []
    try:
        for f in files:
            p = await _save_upload(
                f,
                dest_dir=settings.upload_dir / str(user.id),
                max_size_bytes=settings.max_upload_size_bytes,
            )
            saved_paths.append(p)
    except HTTPException:
        # 部分保存失败时清理已保存的
        for p in saved_paths:
            safe_delete(p)
        raise
    except Exception as exc:
        log.exception("批量保存文件失败: %s", exc)
        for p in saved_paths:
            safe_delete(p)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存文件失败: {exc}",
        ) from exc

    # 创建 task
    task_id = generate_task_id()
    record = tm.create(task_id, conversion_type, total_files=len(saved_paths), user_id=user.id)
    record.extra.update(
        {
            "source_filenames": [p.name for p in saved_paths],
            "source_paths": [str(p) for p in saved_paths],
            "is_batch": True,
        }
    )
    # 状态保持 PENDING（_run_batch_task 会切到 RUNNING）

    # 启动后台任务
    asyncio.create_task(
        _run_batch_task(
            task_id=task_id,
            file_paths=saved_paths,
            conversion_type=conversion_type,
            target_subdir=target_subdir,
            dpi=dpi,
            jpg_quality=jpg_quality,
            overwrite=overwrite,
            zip_output=zip_output,
            tm=tm,
            converter=converter,
            output_dir=settings.output_dir / str(user.id),
        )
    )

    log.info(
        "批量任务已入队: %s, files=%d, type=%s",
        task_id,
        len(saved_paths),
        conversion_type.value,
    )

    data = {
        "task_id": task_id,
        "status": TaskStatus.PENDING.value,
        "total_files": len(saved_paths),
        "message": "已接收任务，请轮询进度",
        "query_url": f"/api/v1/tasks/{task_id}",
    }
    return APIResponse(code=0, message="accepted", data=data)
