# Document Conversion REST API

> 企业级文档转换 REST API 服务 —— FastAPI 包装 [doc_converter](../doc_converter) 引擎

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ 特性

- 🚀 **FastAPI + 异步**：原生 async/await，批量任务真后台执行
- 📦 **统一接口**：`POST /api/v1/convert` 一行上传即转换
- 🔄 **23 种转换组合**：Excel/Word/PDF/图片/OCR 全覆盖
- 🆔 **任务追踪**：返回 `task_id`，支持进度轮询 + 结果下载
- 📚 **Swagger 自动文档**：`/docs` / `/redoc` 即开即用
- 🐳 **Docker 一键部署**：多阶段构建，含 LibreOffice + 中文字体 + Tesseract
- 🛡️ **企业级健壮性**：路径安全、异常隔离、文件大小限制、自动清理
- 🧩 **可扩展**：新增转换类型只需在枚举加一行

## 📋 支持的转换

| 源格式 | 目标格式 | 说明 |
|--------|----------|------|
| `.xlsx`/`.xls` | `.pdf` | 保留格式（字体、颜色、边框、合并、图表）|
| `.xlsx`/`.xls` | `.png`/`.jpg` | 300 DPI 高清 |
| `.pdf` | `.xlsx` | 自动解析表格 |
| `.pdf` | `.png`/`.jpg` | 多页自动拆分 |
| `.docx`/`.doc` | `.pdf` | 保留格式（需本地 Office / LibreOffice）|
| `.pdf` | `.docx` | 文本提取 |
| `.png`/`.jpg`/`.jpeg`/`.bmp`/`.tiff`/`.webp` | `.pdf` | 多图合并多页 PDF |
| `.png`/`.jpg` (OCR) | `.xlsx` | 中文识别（需 Tesseract）|

## 📁 项目结构

```
api/
├── app/
│   ├── main.py                  # FastAPI 入口（lifespan、中间件、异常处理）
│   ├── config.py                # pydantic-settings 配置
│   ├── state.py                 # 全局单例（避免循环导入）
│   ├── api/
│   │   ├── __init__.py          # api_router 聚合
│   │   ├── dependencies.py      # FastAPI 依赖注入
│   │   └── routes/
│   │       ├── health.py        # GET /api/v1/health
│   │       ├── convert.py       # POST /api/v1/convert
│   │       └── tasks.py         # GET/DELETE /api/v1/tasks/*
│   ├── service/
│   │   ├── task_manager.py      # 任务状态管理（线程安全）
│   │   └── conversion_service.py  # 业务逻辑（包装 doc_converter）
│   ├── models/
│   │   ├── enums.py             # ConversionType, TaskStatus
│   │   └── schemas.py           # Pydantic 请求/响应模型
│   └── utils/
│       ├── logger.py            # 统一日志（控制台 + 文件 + 滚动）
│       └── file_utils.py        # 文件路径/大小工具
├── examples/                    # 客户端示例
│   ├── api_client.py            # 同步客户端封装
│   ├── single_convert_demo.py   # 单文件演示
│   ├── batch_convert_demo.py    # 批量演示
│   └── integration_test.py      # pytest 集成测试
├── uploads/                     # 上传临时文件
├── outputs/                     # 转换结果
├── logs/                        # 日志文件
├── requirements.txt             # Python 依赖
├── Dockerfile                   # 多阶段构建
├── docker-compose.yml           # 一键启动
├── .env.example                 # 环境变量示例
├── .dockerignore
├── gunicorn_conf.py             # 生产 gunicorn 配置
├── start.sh / start.bat         # 开发模式启动脚本
└── README.md
```

## 🚀 快速开始

### 方式一：本地 Python

#### Windows
```bash
cd api
start.bat
```

#### Linux / macOS
```bash
cd api
chmod +x start.sh
./start.sh
```

脚本会自动：创建虚拟环境 → 安装依赖 → 复制 `.env.example` → 启动 uvicorn

#### 手动方式
```bash
cd api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 把父目录加入 PYTHONPATH（必须，doc_converter 在 ../）
export PYTHONPATH="$(cd .. && pwd):$PYTHONPATH"
uvicorn app.main:app --reload --port 8000
```

### 方式二：Docker

```bash
cd api
docker compose up --build
```

服务在 `http://localhost:8000` 启动。

> **注意**：`docker-compose.yml` 的 `build.context` 设为 `..`（仓库根），这样 Dockerfile 能同时访问 `api/` 和 `doc_converter/`。

### 验证启动

```bash
curl http://localhost:8000/api/v1/health
```

返回：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "ok",
    "app": "Document Conversion API",
    "version": "1.0.0",
    "converters": 5,
    "supported_pairs": 23,
    "timestamp": "2026-06-12T13:43:28.995137"
  }
}
```

## 📚 API 文档

启动后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔌 API 参考

### 1. 健康检查

```http
GET /api/v1/health
```

返回服务状态与支持的转换组合数。

### 2. 单文件转换

```http
POST /api/v1/convert
Content-Type: multipart/form-data

file: <文件>
conversion_type: png_to_pdf
target_filename: 可选, 自定义输出名
dpi: 可选, 72-2400
jpg_quality: 可选, 1-100
overwrite: false
```

支持的 `conversion_type`：

| 枚举值 | 说明 |
|--------|------|
| `xlsx_to_pdf`, `xls_to_pdf` | Excel → PDF |
| `xlsx_to_png`, `xls_to_png` | Excel → PNG |
| `xlsx_to_jpg`, `xls_to_jpg` | Excel → JPG |
| `pdf_to_xlsx` | PDF → Excel（表格）|
| `pdf_to_png`, `pdf_to_jpg` | PDF → 图片（多页）|
| `docx_to_pdf`, `doc_to_pdf` | Word → PDF |
| `pdf_to_docx` | PDF → Word（文本）|
| `png_to_pdf`, `jpg_to_pdf`, `jpeg_to_pdf` | 图片 → PDF |
| `png_to_xlsx`, `jpg_to_xlsx` | 图片 OCR → Excel |

**响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "f2da9cda7952478b",
    "status": "success",
    "source_filename": "8e444cf7_test.png",
    "output_filename": "8e444cf7_test_525064.pdf",
    "download_url": "/api/v1/tasks/f2da9cda7952478b/download/8e444cf7_test_525064.pdf",
    "file_size": 3453,
    "file_size_human": "3.37 KB"
  }
}
```

### 3. 批量转换

```http
POST /api/v1/convert/batch
Content-Type: multipart/form-data

files: <多个文件>
conversion_type: png_to_pdf
target_subdir: 可选
dpi, jpg_quality, overwrite: 同上
zip_output: true（批量结果打包为 zip）
```

**响应**（异步返回 task_id）：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "abc123def456",
    "status": "pending",
    "total_files": 5,
    "message": "已接收任务，请轮询进度"
  }
}
```

### 4. 任务查询

```http
GET /api/v1/tasks/{task_id}
GET /api/v1/tasks?limit=50
```

**响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "abc123",
    "status": "success",            // pending/running/success/failed/partial_success
    "conversion_type": "png_to_pdf",
    "progress": 100.0,              // 0-100
    "total_files": 5,
    "processed_files": 5,
    "created_at": "2026-06-12T13:44:31",
    "updated_at": "2026-06-12T13:44:32",
    "finished_at": "2026-06-12T13:44:32",
    "error_message": null,
    "output_files": ["a.pdf", "b.pdf"],
    "download_url": "/api/v1/tasks/abc123/download"
  }
}
```

### 5. 文件下载

```http
GET /api/v1/tasks/{task_id}/download                 # 批量：下载 zip
GET /api/v1/tasks/{task_id}/download/{filename}     # 单文件：下载指定
```

### 6. 任务删除

```http
DELETE /api/v1/tasks/{task_id}
```

清理任务记录、输出文件、上传文件。

## 🐍 Python 客户端示例

### 同步客户端

```python
from examples.api_client import DocConverterClient

with DocConverterClient(base_url="http://localhost:8000") as client:
    # 健康检查
    print(client.health())

    # 单文件转换
    result = client.convert_single(
        file_path="report.xlsx",
        conversion_type="xlsx_to_pdf",
        save_to="report.pdf",  # 自动下载
    )
    print(f"输出: {result['output_filename']}")

    # 批量转换
    task_id = client.convert_batch(
        file_paths=["a.png", "b.png", "c.png"],
        conversion_type="png_to_pdf",
        zip_output=True,
    )

    # 轮询进度
    def on_progress(info):
        print(f"  [{info['progress']:.0f}%] {info['status']}")
    final = client.wait_for_task(task_id, on_progress=on_progress)

    # 下载结果
    client.download(task_id, save_to="batch_result.zip")
```

详细示例见 [`examples/`](./examples) 目录。

### 用 curl 调用

```bash
# 单文件转换
curl -X POST http://localhost:8000/api/v1/convert \
  -F "file=@test.png" \
  -F "conversion_type=png_to_pdf" \
  -F "dpi=300"

# 批量转换
curl -X POST http://localhost:8000/api/v1/convert/batch \
  -F "files=@a.png" \
  -F "files=@b.png" \
  -F "conversion_type=png_to_pdf" \
  -F "zip_output=true"

# 任务查询
curl http://localhost:8000/api/v1/tasks/{task_id}

# 下载
curl -O -J http://localhost:8000/api/v1/tasks/{task_id}/download/result.pdf
```

## ⚙️ 配置

通过环境变量或 `.env` 文件配置（参考 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |
| `UPLOAD_DIR` | `./uploads` | 上传目录 |
| `OUTPUT_DIR` | `./outputs` | 输出目录 |
| `LOG_DIR` | `./logs` | 日志目录 |
| `MAX_UPLOAD_SIZE_MB` | `100` | 单文件大小上限 |
| `MAX_BATCH_FILES` | `50` | 批量文件数上限 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `TASK_RESULT_TTL_HOURS` | `24` | 任务记录 TTL |
| `CORS_ORIGINS` | `["*"]` | 允许的跨域来源 |

## 🔒 平台差异

| 平台 | Excel/Word → PDF 引擎 | 备注 |
|------|----------------------|------|
| **Windows + MS Office** | `pywin32` (COM) | 最高保真度，需安装 `pywin32` |
| **macOS + MS Word** | `docx2pdf` | 需 `pip install docx2pdf` |
| **Linux** | LibreOffice headless | Docker 镜像已内置 |
| **无 Office** | 不可用 | 仅 PDF/图片/OCR 转换可用 |

## 🐛 故障排查

### `ModuleNotFoundError: No module named 'doc_converter'`

需要把父目录加入 `PYTHONPATH`：
```bash
export PYTHONPATH="$(cd .. && pwd):$PYTHONPATH"
```
启动脚本已自动处理。

### 启动脚本找不到 .env

`start.sh` / `start.bat` 会自动从 `.env.example` 复制。

### Docker 构建失败：`COPY ../doc_converter not found`

确认 `docker-compose.yml` 中 `context: ..` 设置正确（仓库根目录）。

### LibreOffice 中文乱码

Docker 镜像已内置 Noto CJK + 文泉驿字体；本地部署需自行安装中文字体。

### Tesseract 找不到

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# macOS
brew install tesseract tesseract-lang
```

## 🧪 测试

```bash
# 启动后端（一个终端）
uvicorn app.main:app --reload

# 跑集成测试（另一个终端）
cd api
pip install pytest pytest-asyncio httpx
python -m pytest examples/integration_test.py -v
```

## 📊 性能建议

- **大文件（>100 MB）**：调整 `MAX_UPLOAD_SIZE_MB`，给 gunicorn 加大 `timeout`（默认 300s）
- **批量任务并发**：当前单 worker 顺序处理，多 worker 可并行（注意 doc_converter 内部锁）
- **生产部署**：用 `gunicorn` 替代 `uvicorn --reload`，配置 `gunicorn_conf.py`
- **Nginx 反向代理**：`docker compose --profile with-nginx up` 自动拉起 nginx
- **磁盘 IO**：uploads/outputs 建议放在 SSD，挂载为独立 volume
- **日志清理**：日志按天滚动，保留 30 天（`LOG_RETENTION_DAYS`）

## 🛡️ 安全特性

- ✅ 路径穿越防护：所有文件操作校验父目录
- ✅ 文件大小硬限制：流式写入时强制检查
- ✅ 扩展名白名单：`ALLOWED_EXTENSIONS` 配置
- ✅ 下载越权防护：只能下载属于自己任务的文件
- ✅ 全局异常隔离：单个任务失败不影响其他
- ✅ CORS 可配置：生产环境应设为具体域名

## 📝 扩展指南

新增一种转换类型：

1. 在 [doc_converter/converters/](../doc_converter/converters/) 加新转换器
2. 在 `app/models/enums.py` 的 `ConversionType` 加新枚举值
3. 完成。Swagger 自动出现新选项。

## 📄 许可

MIT License
