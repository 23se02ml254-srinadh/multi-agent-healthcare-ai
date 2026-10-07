@echo off
title MedIntel AI Assistant - Backend Server
echo ===================================================
echo Starting MedIntel Backend Server...
echo ===================================================
cd /d "%~dp0\backend"

if not exist venv (
    echo [ERROR] Virtual environment 'venv' not found in backend folder.
    echo Please ensure the backend virtual environment is created.
    pause
    exit /b
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Starting Flask backend on http://localhost:5000...
python run.py
pause
