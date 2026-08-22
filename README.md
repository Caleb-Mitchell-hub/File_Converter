<p align="center">
  <h1 align="center">File Converter · 文件转换平台</h1>
  <p align="center">
    企业级文档转换工具 · Excel / Word / PDF / 图片 / OCR 多向互转
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/Vue-3.x-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white" alt="Vue 3">
    <img src="https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License">
  </p>
</p>

> 一个开箱即用的文档格式转换平台：核心转换库（纯 Python）、REST API（FastAPI）、Web 界面（Vue 3）三合一。
> 支持 Excel / Word / PDF / 图片之间的多向转换，以及基于本地 Tesseract 或云端 Qwen-VL 大模型的图片 OCR → Excel 表格识别。

---

## ✨ 功能特性

- 🔄 **多格式互转** — 覆盖 Excel、Word、PDF、图片 4 大类，13 种转换方向
- 🤖 **三引擎 OCR** — 支持 Tesseract（本地）、Qwen-VL（云端大模型）、OpenCV 混合（几何检测 + 大模型）三种表格识别引擎，可在线切换
- 🖥️ **Web 界面** — Vue 3 + Element Plus 构建的现代化前端，支持拖拽上传、批量转换、任务进度追踪
- ⚡ **异步处理** — 批量转换走后台任务队列，`task_id` 轮询进度，不阻塞请求
- 🔌 **可扩展架构** — `Registry` + `BaseConverter` 插件式设计，新增转换类型只需写一个类
- 🎯 **高保真** — Windows 下优先调用本地 Office COM 接口，字体/颜色/图表/合并单元格完整保留
- 🌐 **跨平台** — Windows / macOS / Linux，无 Office 时自动回退 LibreOffice
- 🔒 **健壮容错** — 单文件失败不影响批量任务，同名文件自动追加后缀，不覆盖原始文件
- 👤 **用户体系** — 注册 / 登录 / JWT 鉴权（PBKDF2 加盐密码哈希），任务与文件按用户严格隔离
- 💾 **数据持久化** — 用户与任务存入 SQLite（零依赖），服务重启不丢失，历史任务可继续查询/下载
- 👁️ **在线预览** — 任务完成后可直接预览产物：PDF / 图片原生展示，XLSX / DOCX 渲染为 HTML 表格

---

## 📋 支持矩阵

| 输入 ↓ / 输出 → | PDF | XLSX | PNG | JPG | DOCX |
|:----------------|:---:|:----:|:---:|:---:|:----:|
| **Excel (.xlsx/.xls)** | ✅ |  —  | ✅ | ✅ |  —  |
| **PDF**          |  —  |  ✅  | ✅ | ✅ |  ✅  |
| **Word (.docx/.doc)** | ✅ |  —  |  —  |  —  |  —  |
| **图片 (.png/.jpg/.bmp/.tiff/.webp)** | ✅ | ✅* |  —  |  —  |  —  |

> `✅*` 表示图片 → Excel 走 OCR 识别，支持三种引擎（见下文 [OCR 引擎](#-ocr-引擎配置)）。

**13 种转换方向：**

| # | 转换 | 默认引擎 |
|:-:|------|----------|
| 1 | Excel → PDF | Windows: `pywin32` · 其它: `LibreOffice` |
| 2 | Excel → 图片 | `LibreOffice` + `PyMuPDF` |
| 3 | PDF → Excel | `pdfplumber` + `openpyxl` |
| 4 | PDF → 图片 | `PyMuPDF` |
| 5 | 图片 → PDF | `Pillow` |
| 6 | Word → PDF | Windows: `docx2pdf`/`pywin32` · 其它: `LibreOffice` |
| 7 | PDF → Word | `pdfplumber` + `python-docx` |
| 8 | 图片 → Excel (OCR) | `Tesseract` / `Qwen-VL` / `OpenCV Hybrid` |

---

## 🧰 技术栈

| 层 | 技术 |
|----|------|
| 核心库 | Python 3.10+ · PyMuPDF · pdfplumber · Pillow · openpyxl · python-docx |
| 后端 API | FastAPI · Pydantic Settings · Uvicorn |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · Pinia · Vue Router · Axios |
| OCR | pytesseract · Qwen-VL（DashScope 兼容接口）· OpenCV |

---

## 📁 项目结构

```
File_HZ/
├── doc_converter/              # 核心转换库（纯 Python，可独立使用）
│   ├── core/                   # BaseConverter / Registry / Converter / BatchProcessor
│   ├── converters/             # excel / pdf / word / image / ocr / opencv_ocr / qwen_ocr
│   └── utils/                  # 路径 / 平台检测
├── api/                        # FastAPI 后端服务
│   ├── app/
│   │   ├── api/routes/         # auth / convert / tasks / settings / health / info
│   │   ├── models/             # 枚举 / Pydantic schema
│   │   ├── service/            # ConversionService / TaskManager / UserService
│   │   ├── security.py         # 密码哈希 + JWT
│   │   ├── db.py               # SQLite 连接与建表
│   │   └── config.py           # 全局配置（.env 加载）
│   └── data/app.db             # SQLite 数据库（用户 + 任务，自动创建）
│   ├── .env.example            # 环境变量模板
│   └── requirements.txt
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── views/              # convert / tasks / settings / login
│       ├── api/                # 后端接口封装
│       ├── stores/             # Pinia 状态管理
│       └── types/              # TypeScript 类型
└── examples/                   # 核心库调用示例
```

---

## 🚀 快速开始

### 0. Windows 一键启动（双击，免命令行）

项目根目录提供了双击即用的启停脚本，后台运行、不弹命令行窗口，运行日志写入 `logs/` 目录：

| 脚本 | 作用 |
|------|------|
| `start.vbs` | 后台启动后端（`8000`）+ 前端（`5213`），启动后访问 http://localhost:5213 |
| `stop.vbs` | 停止上述两个服务 |

> 前提：`api/.venv`（Python 虚拟环境）与 `frontend/node_modules` 需已安装，首次使用请先按下方第 1、2 步装好依赖。
>
> 日志：`logs/startup.log`（启动状态）、`logs/backend.log` / `backend.err.log`（后端）、`logs/frontend.log` / `frontend.err.log`（前端）。

### 前置依赖

- **Python 3.10+**
- **Node.js 18+**（前端）
- 可选：Tesseract（本地 OCR）、LibreOffice / Microsoft Office（Excel/Word → PDF）

### 1. 启动后端

```bash
cd api
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt

# 复制环境变量模板并填写
cp .env.example .env

# 启动（默认端口 8000）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后可访问：
- Swagger 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

> **默认管理员账号**：\`admin / admin123\`（首次启动自动创建，登录后请及时修改密码）。
> 所有转换 / 任务接口均需登录（JWT），未登录返回 401。

### 2. 启动前端

```bash
cd frontend
npm install

# 开发模式（默认端口 5173）
npm run dev
```

> 前端通过 Vite 代理访问后端，可在 `frontend/.env.development` 中配置 `VITE_API_BASE` 指向后端地址。

### 3. Docker 部署（可选）

```bash
cd api
docker compose up -d
```

---

## 🤖 OCR 引擎配置

图片 → Excel（OCR）支持三种引擎，可在 **前端「系统设置」页** 或通过 **REST API** 在线切换，无需重启服务：

| 引擎 | 值 | 说明 | 适用场景 |
|------|-----|------|----------|
| OpenCV 混合 | `opencv_hybrid` | OpenCV 几何检测 + Qwen-VL 云端 OCR（默认） | 带边框的规整表格 |
| Qwen-VL | `qwen_vl` | 纯 Qwen-VL 大模型云端识别 | 无边框表格，需配置 API Key |
| Tesseract | `tesseract` | 纯本地 Tesseract，无需网络 | 简单文字识别，离线可用 |

**配置 Qwen-VL 大模型**（在 `.env` 或前端设置页）：

```bash
OCR_ENGINE=qwen_vl
QWEN_API_KEY=sk-xxxxxx
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-vl-plus
QWEN_TIMEOUT=60
```

**安装本地 Tesseract**（使用 `tesseract` 引擎时）：

| 平台 | 命令 |
|------|------|
| Windows | 前往 [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装，勾选中文语言包 |
| macOS | `brew install tesseract tesseract-lang` |
| Ubuntu/Debian | `sudo apt install tesseract-ocr tesseract-ocr-chi-sim` |

---

## ⚙️ 配置项（`.env`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `8000` | 后端端口 |
| `MAX_UPLOAD_SIZE_MB` | `100` | 单文件上传大小上限 |
| `MAX_BATCH_FILES` | `50` | 批量上传文件数上限 |
| `OCR_ENGINE` | `opencv_hybrid` | OCR 引擎（`opencv_hybrid` / `qwen_vl` / `tesseract`） |
| `QWEN_API_KEY` | 空 | Qwen-VL 大模型 API Key |
| `QWEN_BASE_URL` | `dashscope.aliyuncs.com/...` | Qwen-VL 接口地址 |
| `QWEN_MODEL` | `qwen-vl-plus` | Qwen-VL 模型名称 |
| `QWEN_TIMEOUT` | `60` | Qwen-VL 请求超时（秒） |
| `CORS_ORIGINS` | `["*"]` | 允许的跨域来源 |

---

## 📡 REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/convert` | 单文件转换（同步返回结果） |
| `POST` | `/api/v1/convert/batch` | 批量转换（异步，返回 `task_id`） |
| `GET` | `/api/v1/tasks/{task_id}` | 查询任务进度与结果 |
| `GET` | `/api/v1/tasks/{task_id}/download/{filename}` | 下载单文件任务产物 |
| `GET` | `/api/v1/tasks/{task_id}/preview/{filename}` | 在线预览产物：PDF/图片 inline，XLSX/DOCX 转 HTML |
| `GET` | `/api/v1/settings/ocr` | 读取 OCR 配置（API Key 脱敏） |
| `PUT` | `/api/v1/settings/ocr` | 更新 OCR 配置（持久化到 `.env`） |
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/info` | 服务信息 |

### 示例：单文件转换

```bash
curl -X POST http://localhost:8000/api/v1/convert \
  -F "file=@report.xlsx" \
  -F "conversion_type=xlsx_to_pdf"
```

### 示例：切换 OCR 引擎

```bash
curl -X PUT http://localhost:8000/api/v1/settings/ocr \
  -H "Content-Type: application/json" \
  -d '{"engine":"qwen_vl"}'
```

---

## 🐍 作为 Python 库使用

核心库 `doc_converter` 可脱离 Web 服务独立使用：

```python
from doc_converter import Converter

# Excel → PDF
Converter.convert("report.xlsx", "report.pdf")

# PDF → 多页 PNG（自动命名 page_001.png / page_002.png...）
Converter.convert("manual.pdf", "manual_page.png")

# 图片 → PDF
Converter.convert("photo.png", "photo.pdf")

# 扫描件 OCR → Excel
Converter.convert("scan.png", "scan.xlsx")
```

更多场景见 [`examples/`](./examples/)。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交改动：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 发起 Pull Request

---

## 📄 License

[MIT](./LICENSE) © 2026 File Converter contributors
