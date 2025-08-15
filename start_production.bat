@echo off
title Hotel Management Backend - Production Mode
color 0C

echo.
echo ========================================
echo   Hotel Management Backend
echo   Production Server Startup
echo ========================================
echo.

:: Check if virtual environment exists
if not exist ".venv" (
    echo ❌ Virtual environment not found!
    echo.
    echo Please run the setup script first:
    echo   setup_project.bat
    echo.
    pause
    exit /b 1
)

:: Check if .env file exists
if not exist ".env" (
    echo ⚠️  .env file not found!
    echo.
    echo Creating default .env file for production...
    echo Please review and update the settings as needed.
    echo.
    pause
)

:: Activate virtual environment
echo 🔄 Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

:: Create necessary directories
echo 📁 Creating necessary directories...
if not exist "uploads\ocr" mkdir "uploads\ocr"
if not exist "ml_models" mkdir "ml_models"
if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"
if not exist "backups" mkdir "backups"

:: Check if ML models exist
if not exist "ml_models\occupancy_model.joblib" (
    echo ⚠️  ML models not found. Generating them...
    python generate_ml_models.py
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to generate ML models
        pause
        exit /b 1
    )
)

:: Check if requirements are installed
echo 🔍 Checking dependencies...
pip show fastapi >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Error installing dependencies
        pause
        exit /b 1
    )
)

:: Display server information
echo.
echo ========================================
echo   Production Server Configuration
echo ========================================
echo   Host: 0.0.0.0 (all interfaces)
echo   Port: 8000
echo   Mode: Production (multi-worker)
echo   API Docs: http://localhost:8000/docs
echo   Health Check: http://localhost:8000/health
echo ========================================
echo.

:: Start the production server with Gunicorn (if available) or uvicorn
echo 🚀 Starting production server...
pip show gunicorn >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ Using Gunicorn with Uvicorn workers...
    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --keep-alive 5
) else (
    echo ⚠️  Using Uvicorn (install gunicorn for better production performance)...
    echo 📦 To install Gunicorn: pip install gunicorn
    echo.
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
)

pause
