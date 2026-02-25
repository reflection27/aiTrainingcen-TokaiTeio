@echo off
chcp 65001 > nul
echo ====================================
echo SenseVoice ASR API 服务启动
echo ====================================
echo.

cd /d "%~dp0"

echo 当前目录: %cd%
echo.

echo 正在启动API服务...
python api.py

pause
