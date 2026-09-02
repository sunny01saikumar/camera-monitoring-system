@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo   RTSP Person Detection System Setup
echo ==============================================

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: Create Virtual Environment
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate Virtual Environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip and install requirements
echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies (opencv-python, numpy, Flask, requests)...
pip install opencv-python numpy Flask requests
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

:: Download model
echo Checking/Downloading model...
python download_model.py
if %errorlevel% neq 0 (
    echo Model download failed.
    pause
    exit /b 1
)

:: Start Flask app
echo Starting the application...
echo Web server will run on http://localhost:5000
python app.py

pause
