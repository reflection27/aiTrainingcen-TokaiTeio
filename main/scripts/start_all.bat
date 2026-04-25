@echo off
chcp 65001
echo ========================================
echo 东海帝王AI - 启动脚本
echo ========================================
echo.

echo [1/2] 启动 GPT-SoVITS API v2...
echo 请确保 GPT-SoVITS 的 api_v2.py 已正确配置
echo.
start "GPT-SoVITS API v2" cmd /k "cd /d "%~dp0..\plugins\GPT-SoVITS" && start_api_v2.bat"

echo 等待 GPT-SoVITS API v2 启动...
timeout /t 5 /nobreak > nul

echo.
echo [2/2] 启动 东海帝王AI 主程序...
echo.
start "东海帝王AI" cmd /k "cd /d "%~dp0.." && "%~dp0..\venv\Scripts\python.exe" main.py"

echo.
echo ========================================
echo 程序已退出
echo ========================================
pause
