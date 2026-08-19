@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 把父目录加入 PYTHONPATH
set PYTHONPATH=%~dp0\..;%PYTHONPATH%

REM 创建虚拟环境
if not exist ".venv" (
    echo [start] 创建虚拟环境...
    python -m venv .venv
)

REM 激活
call .venv\Scripts\activate.bat

REM 安装依赖
echo [start] 安装依赖...
pip install -q -r requirements.txt

REM 复制 .env
if not exist ".env" (
    copy .env.example .env >nul
    echo [start] 已创建 .env
)

REM 启动
echo [start] 启动服务...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
