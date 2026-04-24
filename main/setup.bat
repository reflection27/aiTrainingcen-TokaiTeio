@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   东海帝王AI - 一键安装脚本
echo ========================================
echo.

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

:: ============================================================
:: 1. 检查 Python
:: ============================================================
echo [1/6] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11
    echo 下载地址：https://www.python.org/downloads/
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo       Python %PY_VER% 已找到

:: ============================================================
:: 2. 检查/安装 ffmpeg
:: ============================================================
echo [2/6] 检查 ffmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo       未找到 ffmpeg，正在通过 winget 安装...
    winget install --id Gyan.FFmpeg -e --silent
    :: winget 修改了 PATH 但当前会话不自动刷新，从注册表重新加载
    for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=%%b"
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "PATH=!PATH!;%%b"
    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo [警告] ffmpeg 安装失败，请手动安装后重试
        echo        https://www.gyan.dev/ffmpeg/builds/
    ) else (
        echo       ffmpeg 安装完成
    )
) else (
    echo       ffmpeg 已安装，跳过
)

:: ============================================================
:: 3. 创建虚拟环境
:: ============================================================
echo [3/6] 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo       虚拟环境创建完成
) else (
    echo       虚拟环境已存在，跳过
)

:: ============================================================
:: 4. 安装依赖
:: ============================================================
echo [4/6] 安装依赖...
echo       升级 pip...
venv\Scripts\python.exe -m pip install --upgrade pip -q
echo       安装 PyTorch (CUDA 12.1)...
venv\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo [错误] PyTorch 安装失败，请检查网络后重试
    pause & exit /b 1
)
echo       安装项目依赖（时间较长，请耐心等待）...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请查看上方报错
    pause & exit /b 1
)
echo       依赖安装完成

:: ============================================================
:: 5. 初始化配置文件
:: ============================================================
echo [5/6] 初始化配置文件...
if not exist ".env" (
    copy .env.example .env >nul
    echo       已创建 .env，请填入你的 API Key
) else (
    echo       .env 已存在，跳过
)
if not exist "ai_agent_config.json" (
    copy ai_agent_config.example.json ai_agent_config.json >nul
    echo       已创建 ai_agent_config.json
) else (
    echo       ai_agent_config.json 已存在，跳过
)

:: ============================================================
:: 6. 下载模型
:: ============================================================
echo [6/7] 下载模型文件...
venv\Scripts\python.exe scripts\download_models.py

:: ============================================================
:: 7. 下载 Godot 可执行文件
:: ============================================================
echo [7/7] 下载 Godot 4.6.2...
set "GODOT_DIR=plugins\godot\Godot_v4.6.2-stable_win64.exe"
set "GODOT_EXE=%GODOT_DIR%\Godot_v4.6.2-stable_win64.exe"
if exist "%GODOT_EXE%" (
    echo       Godot 已存在，跳过
) else (
    echo       正在下载 Godot_v4.6.2-stable_win64.exe.zip...
    venv\Scripts\python.exe scripts\download_godot.py
)

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 下一步：
echo   1. 编辑 .env 文件，填入 DeepSeek / GLM4V API Key
echo   2. 运行 scripts\start_all.bat 启动程序
echo.
pause
