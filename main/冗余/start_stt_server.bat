@echo off
chcp 65001
echo ========================================
echo STT服务器 - 启动脚本
echo ========================================
echo.

echo 启动 STT 服务器...
echo.

cd /d "G:\gpt-sovits2gent\main\plugins\RealtimeSTT-master"
call "test_env\Scriptsctivate.bat"
cd /d "G:\gpt-sovits2gent\main"
python stt_server.py

echo.
echo ========================================
echo STT服务器已退出
echo ========================================
pause
