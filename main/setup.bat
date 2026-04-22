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
    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo [警告] ffmpeg 安装失败，请手动安装后重试
        echo 下载地址：https://www.gyan.dev/ffmpeg/builds/
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
echo       安装 PyTorch (CUDA 12.1)...
venv\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 -q
echo       安装项目依赖（时间较长，请耐心等待）...
venv\Scripts\python.exe -m pip install -r requirements.txt -q
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
venv\Scripts\python.exe -c "
import os, sys, urllib.request, zipfile

# HuggingFace 镜像（国内加速）
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
from huggingface_hub import snapshot_download

pretrained_dir = 'plugins/GPT-SoVITS/GPT_SoVITS/pretrained_models'

# 下载底模
def dl_model(repo_id, local_dir, desc):
    if os.path.exists(local_dir) and os.listdir(local_dir):
        print(f'  {desc} 已存在，跳过')
        return
    print(f'  正在下载 {desc}...')
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        ignore_patterns=['*.h5', 'flax_model*', 'tf_model*', '*.msgpack']
    )
    print(f'  {desc} 下载完成')

dl_model('hfl/chinese-roberta-wwm-ext-large',
         f'{pretrained_dir}/chinese-roberta-wwm-ext-large',
         'chinese-roberta-wwm-ext-large')

dl_model('TencentGameMate/chinese-hubert-base',
         f'{pretrained_dir}/chinese-hubert-base',
         'chinese-hubert-base')

# 下载角色权重
weights_dir = 'character/TokaiTeio/weights'
if os.path.exists(f'{weights_dir}/TokaiTeio-e15.ckpt') and os.path.exists(f'{weights_dir}/TokaiTeio_e20_s220.pth'):
    print('  TokaiTeio 权重已存在，跳过')
else:
    print('  正在下载 TokaiTeio 权重...')
    os.makedirs(weights_dir, exist_ok=True)
    url = 'https://github.com/reflection27/aiTrainingcen-TokaiTeio/releases/download/weights/TokaiTeio-weights.zip'
    zip_path = 'TokaiTeio-weights.zip'
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(weights_dir)
    os.remove(zip_path)
    print('  TokaiTeio 权重下载完成')
"

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
    venv\Scripts\python.exe -c "
import urllib.request, zipfile, os
url = 'https://github.com/godotengine/godot/releases/download/4.6.2-stable/Godot_v4.6.2-stable_win64.exe.zip'
zip_path = 'godot_tmp.zip'
dest_dir = 'plugins/godot/Godot_v4.6.2-stable_win64.exe'
os.makedirs(dest_dir, exist_ok=True)
print('  下载中（约 100MB）...')
urllib.request.urlretrieve(url, zip_path)
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(dest_dir)
os.remove(zip_path)
print('  Godot 下载完成')
"
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
