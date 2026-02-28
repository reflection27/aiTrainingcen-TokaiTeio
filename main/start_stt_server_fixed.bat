@echo off
chcp 65001
echo ========================================
echo STT服务器 - 启动脚本
echo ========================================
echo.

echo 启动 STT 服务器...
echo.

cd /d "G:\gpt-sovits\v2\agent\main\plugins\RealtimeSTT-master"
call "test_env\Scripts\activate.bat"
cd /d "G:\gpt-sovits\v2\agent\main"
python stt_server.py

echo.
echo ========================================
echo STT服务器已退出
echo ========================================
pause
