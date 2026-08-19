# ---- 阶段 1: 构建 ----
# 注意：构建时 docker-compose.yml 已设置 context 为 .. （仓库根），
# 这样能同时访问 api/ 和 doc_converter/ 两个目录。
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装系统依赖（编译 PyMuPDF 等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- 阶段 2: 运行时 ----
FROM python:3.11-slim

# 元数据
LABEL maintainer="File_HZ Team" \
      version="1.0.0" \
      description="Document Conversion REST API"

# 系统时区 + 字体（中文支持）
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # LibreOffice（用于 Linux 上的 PDF 转换保真度）
    libreoffice \
    # 中文字体
    fonts-noto-cjk \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    # Tesseract OCR + 中文语言包
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    # 其它工具
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 拷贝构建好的 wheels 并安装
COPY --from=builder /wheels /wheels
COPY api/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# 拷贝应用代码（注意：构建 context 是仓库根 ../）
COPY api/app/ ./app/
COPY api/.env.example ./.env.example
COPY api/gunicorn_conf.py ./gunicorn_conf.py

# 拷贝 doc_converter 源码（来自父目录）
COPY doc_converter/ /doc_converter_src/
ENV PYTHONPATH=/doc_converter_src:$PYTHONPATH

# 创建运行时目录
RUN mkdir -p /app/uploads /app/outputs /app/logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令（生产模式用 gunicorn + uvicorn worker）
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
