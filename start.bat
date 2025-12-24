@echo off
echo Starting FastAPI Backend Server...
cd /d "%~dp0"

REM 激活虚拟环境（如果存在）
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM 使用 Python 启动脚本（推荐方式）
python start.py

pause
