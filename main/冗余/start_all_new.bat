@echo off
chcp 65001
echo ========================================
echo 东海帝王AI - 启动脚本
echo ========================================
echo.

echo [1/3] 启动 GPT-SoVITS API v2...
echo 请确保 GPT-SoVITS 的 api_v2.py 已正确配置
echo.
start "GPT-SoVITS API v2" cmd /k "cd /d "%~dp0plugins\GPT-SoVITS" && start_api_v2.bat"

echo 等待 GPT-SoVITS API v2 启动...
timeout /t 5 /nobreak > nul

echo.
echo [2/3] 启动 STT 服务器...
echo 请确保 STT 服务器已正确配置
echo.
start "STT 服务器" cmd /k "cd /d "%~dp0" && start_stt_server_fixed.bat"

echo 等待 STT 服务器启动...
timeout /t 5 /nobreak > nul

echo.
echo [3/3] 启动 东海帝王AI 主程序...
echo.
start "东海帝王AI" cmd /k "G:\gpt-sovits\v2\agent\main\venv\Scripts\activate.bat && cd /d G:\gpt-sovits\v2\agent\main && python main.py"

echo.
echo ========================================
echo 程序已退出
echo ========================================
pause
