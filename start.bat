@echo off
chcp 65001 >nul
title 游戏文本翻译工具 v3.0

echo ============================================
echo   游戏文本翻译工具 v3.0
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 安装依赖
echo [信息] 正在检查依赖...
pip install openai tkinterdnd2 -q 2>nul

:: 启动
echo [信息] 正在启动 GUI...
python main.py

pause