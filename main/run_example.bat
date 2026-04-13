
@echo off
chcp 65001
echo ========================================
echo STT到主程序 - 启动脚本
echo ========================================
echo.

echo [1/2] 启动主程序...
echo.
start "东海帝王AI" cmd /k "G:\gpt-sovits\v2\agent\main\venv\Scripts\activate.bat && cd /d G:\gpt-sovits\v2\agent\main && python main.py"

echo 等待主程序启动...
timeout /t 5 /nobreak > nul

echo.
echo [2/2] 启动STT程序...
echo.
cd /d "g:\gpt-sovits\v2\agent\main\plugins\RealtimeSTT-master"
call test_env\Scripts\activate.bat
cd /d "g:\gpt-sovits\v2\agent\main"

echo STT程序已启动，识别到的文本将自动发送到主程序
echo 按Ctrl+C退出程序
echo.

python realtimestt_process.py

echo.
echo ========================================
echo 程序已退出
echo ========================================
pause
