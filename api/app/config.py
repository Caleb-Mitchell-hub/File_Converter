"""应用配置。

使用 pydantic-settings 从环境变量 / .env 文件加载配置。
所有路径、上传大小限制、日志级别等都集中在此。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.enums import OcrEngine


# 项目根目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """全局配置。"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- 服务 ----
    app_name: str = "Document Conversion API"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- 路径 ----
    upload_dir: Path = Field(default=BASE_DIR / "uploads")
    output_dir: Path = Field(default=BASE_DIR / "outputs")
    log_dir: Path = Field(default=BASE_DIR / "logs")

    # ---- 上传限制 ----
    max_upload_size_mb: int = 100
    max_batch_files: int = 50
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [
            ".xlsx", ".xls", ".pdf", ".docx", ".doc",
            ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp",
        ]
    )

    # ---- 日志 ----
    log_level: str = "INFO"
    log_to_file: bool = True
    log_to_console: bool = True
    log_retention_days: int = 30

    # ---- 任务管理 ----
    task_result_ttl_hours: int = 24
    enable_async_processing: bool = True

    # ---- CORS ----
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # ---- 转换引擎 ----
    default_dpi: int = 300
    default_jpg_quality: int = 95

    # ---- OCR 引擎 ----
    ocr_engine: OcrEngine = OcrEngine.OPENCV_HYBRID

    # ---- OCR 大模型（Qwen-VL）----
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-vl-plus"
    qwen_timeout: int = 60

    def ensure_directories(self) -> None:
        """启动时确保所有目录存在。"""
        for d in (self.upload_dir, self.output_dir, self.log_dir):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局单例配置。"""
    s = Settings()
    s.ensure_directories()
    return s
