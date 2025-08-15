@echo off
echo Starting Hotel Management Backend Server...

:: Create necessary directories
if not exist "uploads\ocr" mkdir "uploads\ocr"
if not exist "ml_models" mkdir "ml_models"
if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"
if not exist "backups" mkdir "backups"

:: Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

:: Check if requirements are installed
echo Checking dependencies...
pip show fastapi >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo Error installing dependencies
        pause
        exit /b 1
    )
)

:: Start the server
echo Starting server...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause