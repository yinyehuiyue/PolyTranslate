@echo off
chcp 65001 >nul
title PyInstaller 打包 - GameTranslator v4.0

echo ============================================
echo   PyInstaller 单文件打包脚本 v4.0
echo ============================================
echo.

:: ── [1/7] 检测可用的 Python ──
echo [1/7] 检测 Python 环境...
set PYTHON=
for %%p in (py python python3) do (
    where %%p >nul 2>&1 && (
        %%p --version >nul 2>&1 && set PYTHON=%%p && goto :found
    )
)
echo [错误] 未找到可用的 Python，请安装 Python 3.10+
echo 下载地址: https://www.python.org/downloads/
pause
exit /b 1
:found
echo [信息] 检测到: %PYTHON%
%PYTHON% --version

:: ── [2/7] 安装打包依赖 ──
echo.
echo [2/7] 安装 PyInstaller...
%PYTHON% -m pip install pyinstaller -q

:: ── [3/7] 确保运行时依赖 ──
echo [3/7] 确保运行时依赖已安装...
%PYTHON% -m pip install openai tkinterdnd2 customtkinter -q

:: ── [4/7] 清理旧构建 ──
echo [4/7] 清理旧构建目录...
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "build" rmdir /s /q "build" 2>nul
if exist "*.spec" del /q "*.spec" 2>nul

:: ── [5/7] 检测图标 ──
echo [5/7] 检测图标文件...
set ICON_ARG=
if exist "resources\icon.ico" (
    set ICON_ARG=--icon="resources\icon.ico"
    echo [信息] 使用图标: resources\icon.ico
) else (
    echo [信息] 未找到 resources\icon.ico，跳过图标
    echo [提示] 可将自定义 ico 文件放入 resources\icon.ico
)

:: ── [6/7] 执行打包 ──
echo.
echo [6/7] 正在打包 (单文件 + 无控制台) ...
echo 这可能需要 1-3 分钟，请耐心等待...

%PYTHON% -m PyInstaller --onefile --noconsole ^
    %ICON_ARG% ^
    --name "GameTranslator" ^
    --add-data "theme.py;." ^
    --hidden-import "tkinterdnd2" ^
    --hidden-import "customtkinter" ^
    --hidden-import "openai" ^
    --hidden-import "engine" ^
    --hidden-import "engine.config_manager" ^
    --hidden-import "engine.api_client" ^
    --hidden-import "engine.prompt_builder" ^
    --hidden-import "engine.glossary_manager" ^
    --hidden-import "engine.backup_manager" ^
    --hidden-import "engine.progress_tracker" ^
    --hidden-import "engine.extractor" ^
    --hidden-import "engine.extractor.detector" ^
    --hidden-import "engine.extractor.rpgmaker" ^
    --hidden-import "engine.extractor.renpy" ^
    --hidden-import "engine.extractor.generic" ^
    --hidden-import "engine.injector" ^
    --hidden-import "engine.injector.base_injector" ^
    --hidden-import "engine.injector.file_injector" ^
    --hidden-import "engine.injector.memory_injector" ^
    --hidden-import "memory" ^
    --hidden-import "memory.winapi" ^
    --hidden-import "memory.memory_scanner" ^
    --hidden-import "memory.process_guard" ^
    --hidden-import "memory.shellcode_templates" ^
    --hidden-import "ui" ^
    --hidden-import "ui.main_window" ^
    --hidden-import "ui.settings_dialog" ^
    --hidden-import "ui.style_panel" ^
    --hidden-import "ui.glossary_editor" ^
    --hidden-import "ui.correction_editor" ^
    --hidden-import "ui.widgets" ^
    --hidden-import "utils" ^
    --hidden-import "utils.retry" ^
    --hidden-import "utils.text_guard" ^
    --hidden-import "utils.security" ^
    --hidden-import "utils.error_logger" ^
    --collect-all "openai" ^
    --collect-all "customtkinter" ^
    main.py

:: ── [7/7] 完成 ──
echo.
if exist "dist\GameTranslator.exe" (
    echo ============================================
    echo   ✅ 打包成功!
    echo   输出文件: dist\GameTranslator.exe
    echo ============================================
    echo.
    echo 使用说明:
    echo   1. 将 GameTranslator.exe 复制到任意目录
    echo   2. 双击运行即可（首次启动需等待 3-10 秒解压）
    echo   3. config.json 自动在 exe 同目录生成
    echo   4. dict.json 可放在 exe 同目录
    echo   5. 如程序崩溃，查看同目录 error.log
    echo.
    echo 体积预估: ~25-30MB
    echo.
) else (
    echo ============================================
    echo   ❌ 打包失败！
    echo   请检查 PyInstaller 是否正常安装
    echo   或查看上方错误信息
    echo ============================================
)

pause