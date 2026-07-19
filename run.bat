@echo off
title AI Talking Tom
echo ============================================
echo    AI Talking Tom - Starting...
echo ============================================
echo.

:: Find Python (venv first, then system)
set PYTHON=
if exist "%~dp0venv\Scripts\python.exe" (
    set PYTHON=%~dp0venv\Scripts\python.exe
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=python
    ) else (
        echo ERROR: Python not found! Install Python 3.10+ first.
        pause
        exit /b 1
    )
)

:: Find Godot
set GODOT=
for %%f in ("%~dp0Godot_*.exe") do (
    echo %%~nxf | findstr /i "console" >nul
    if errorlevel 1 set GODOT=%%f
)

if "%GODOT%"=="" (
    echo WARNING: Godot not found in project folder.
    echo Download Godot 4.6 from https://godotengine.org
)

echo [1/2] Starting Python backend...
start /b "" %PYTHON% "%~dp0backend\main.py"
timeout /t 3 /nobreak >nul

echo [2/2] Starting Godot...
if not "%GODOT%"=="" (
    start "" %GODOT% --path "%~dp0godot"
) else (
    echo Skipping Godot (not found).
)

echo.
echo ============================================
echo    AI Talking Tom is running!
echo    Dashboard: http://localhost:8000
echo    Press Ctrl+C to stop.
echo ============================================
echo.

:: Keep window open
pause
