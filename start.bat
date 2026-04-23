@echo off
setlocal

set "ROOT=%~dp0main"
set "PY=%ROOT%\venv\Scripts\python.exe"

echo ========================================
echo   TokaiTeio AI - Startup
echo ========================================
echo.

echo [1/3] Starting GPT-SoVITS API v2 (TTS)...
start "GPT-SoVITS" cmd /k "cd /d %ROOT%\plugins\GPT-SoVITS && ..\..\venv\Scripts\python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml"

echo       Waiting for TTS service (port 9880)...
:wait_tts
"%PY%" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',9880)))" 2>nul
if not errorlevel 1 goto tts_ready
ping -n 2 127.0.0.1 >nul
goto wait_tts
:tts_ready
echo       TTS ready

echo.
echo [2/3] Starting main program...
start "" cmd /k "%ROOT%\venv\Scripts\activate.bat && cd /d %ROOT% && python main.py"

echo       Waiting for main program (port 5000)...
:wait_main
"%PY%" -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(s.connect_ex(('127.0.0.1',5000)))" 2>nul
if not errorlevel 1 goto main_ready
ping -n 2 127.0.0.1 >nul
goto wait_main
:main_ready
echo       Main program ready

echo.
echo [3/3] Starting STT...
echo       Press Ctrl+C to exit
echo.

cd /d "%ROOT%"
call venv\Scripts\activate.bat
set PYTHONIOENCODING=utf-8
python core\realtimestt_process.py

echo.
echo ========================================
echo   Exited
echo ========================================
pause
