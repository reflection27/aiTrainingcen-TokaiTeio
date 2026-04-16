@echo off
set GODOT_EXE=%~dp0plugins\godot\Godot_v4.6.2-stable_win64.exe\Godot_v4.6.2-stable_win64.exe
set PROJECT_DIR=%~dp0plugins\godot\tokai-teio

echo Godot: %GODOT_EXE%
echo Project: %PROJECT_DIR%
echo.

if not exist "%GODOT_EXE%" (
    echo [ERROR] Godot not found: %GODOT_EXE%
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%\project.godot" (
    echo [ERROR] project.godot not found: %PROJECT_DIR%
    pause
    exit /b 1
)

echo Starting Godot pet...
"%GODOT_EXE%" --path "%PROJECT_DIR%"

echo.
echo Godot exited.
pause
