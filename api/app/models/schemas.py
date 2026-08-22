"""Pydantic 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .enums import ConversionType, TaskStatus


# ---------------------------------------------------------------------- #
# 通用响应
# ---------------------------------------------------------------------- #
class APIResponse(BaseModel):
    """统一响应外壳。"""

    code: int = 0
    message: str = "ok"
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """统一错误响应。"""

    code: int
    message: str
    detail: Optional[str] = None
    task_id: Optional[str] = None


# ---------------------------------------------------------------------- #
# 转换请求
# ---------------------------------------------------------------------- #
class ConversionRequest(BaseModel):
    """单文件转换的元数据（文件本体通过 multipart 上传）。"""

    conversion_type: ConversionType = Field(
        ..., description="转换类型枚举"
    )
    target_filename: Optional[str] = Field(
        None, description="可选的自定义输出文件名（含扩展名）"
    )
    dpi: Optional[int] = Field(None, ge=72, le=2400, description="图片渲染 DPI")
    jpg_quality: Optional[int] = Field(None, ge=1, le=100, description="JPG 质量")
    overwrite: bool = Field(False, description="是否覆盖已存在的目标文件")


class BatchConversionRequest(BaseModel):
    """批量转换请求（通过 multipart 上传多个文件 + 一个 conversion_type）。"""

    conversion_type: ConversionType = Field(..., description="批量转换类型")
    target_subdir: Optional[str] = Field(None, description="输出子目录名")
    dpi: Optional[int] = Field(None, ge=72, le=2400)
    jpg_quality: Optional[int] = Field(None, ge=1, le=100)
    overwrite: bool = False
    zip_output: bool = Field(True, description="批量结果是否打包为 ZIP 下载")


# ---------------------------------------------------------------------- #
# 任务 / 结果
# ---------------------------------------------------------------------- #
class TaskInfo(BaseModel):
    """任务信息。"""

    task_id: str = Field(..., description="任务唯一 ID")
    status: TaskStatus = Field(..., description="任务状态")
    conversion_type: ConversionType = Field(..., description="转换类型")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="进度百分比")
    total_files: int = Field(1, ge=1, description="总文件数")
    processed_files: int = Field(0, ge=0, description="已处理文件数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    finished_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    output_files: List[str] = Field(
        default_factory=list, description="输出文件名列表"
    )
    download_url: Optional[str] = Field(
        None, description="下载 URL（任务完成后填充）"
    )
    extra: dict = Field(default_factory=dict, description="扩展元数据")


class FileResult(BaseModel):
    """批量任务中单个文件的处理结果。"""

    source_filename: str
    output_filename: Optional[str] = None
    success: bool
    message: str = ""


class TaskListResponse(BaseModel):
    """任务列表响应。"""

    total: int
    tasks: List[TaskInfo]


# ---------------------------------------------------------------------- #
# 健康检查
# ---------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = "ok"
    app: str
    version: str
    converters: int
    supported_pairs: int
    timestamp: datetime


# ---------------------------------------------------------------------- #
# OCR 设置
# ---------------------------------------------------------------------- #
class OcrSettingsResponse(BaseModel):
    """OCR 设置响应（API Key 脱敏）。"""

    engine: str
    qwen_api_key: str
    qwen_base_url: str
    qwen_model: str
    qwen_timeout: int


class OcrSettingsUpdate(BaseModel):
    """OCR 设置更新请求（所有字段可选）。"""

    engine: Optional[str] = None
    qwen_api_key: Optional[str] = None
    qwen_base_url: Optional[str] = None
    qwen_model: Optional[str] = None
    qwen_timeout: Optional[int] = None

# ---------------------------------------------------------------------- #
# 认证 / 用户
# ---------------------------------------------------------------------- #
class UserInfo(BaseModel):
    """对外暴露的用户信息（不含密码哈希）。"""

    id: str
    username: str
    nickname: str
    role: str
    created_at: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求。"""

    username: str
    password: str
    nickname: Optional[str] = None


class LoginResponse(BaseModel):
    """登录响应：JWT + 用户信息。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo

