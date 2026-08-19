#!/usr/bin/env bash
# 开发模式启动脚本
set -e

# 切到脚本所在目录
cd "$(dirname "$0")"

# 把父目录加入 PYTHONPATH
export PYTHONPATH="$(cd .. && pwd):$PYTHONPATH"

# 创建虚拟环境（如不存在）
if [ ! -d ".venv" ]; then
    echo "[start] 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活
source .venv/bin/activate

# 安装依赖
echo "[start] 安装依赖..."
pip install -q -r requirements.txt

# 复制 .env（如不存在）
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[start] 已创建 .env"
fi

# 启动
echo "[start] 启动服务..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
