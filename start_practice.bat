@echo off
REM Quick launcher for Spelling Practice
REM Just double-click this file to start!

cd /d "%~dp0"

echo.
echo =====================================
echo   Spelling Practice Launcher
echo =====================================
echo.

REM Check if virtual environment exists
if exist ".venv\Scripts\python.exe" (
    echo Starting with virtual environment...
    echo.
    .venv\Scripts\python.exe spelling_practice.py
) else (
    echo Starting with system Python...
    echo.
    python spelling_practice.py
)

pause
