@echo off
title Hotel Management Backend - Development Mode
color 0A

echo.
echo ========================================
echo   Hotel Management Backend
echo   Development Server Startup
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

:: Activate virtual environment
echo 🔄 Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

:: Check if Python is available
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not available in virtual environment
    echo Please check your Python installation
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
echo   Server Configuration
echo ========================================
echo   Host: 0.0.0.0 (all interfaces)
echo   Port: 8000
echo   Mode: Development (auto-reload)
echo   API Docs: http://localhost:8000/docs
echo   Health Check: http://localhost:8000/health
echo ========================================
echo.

:: Start the development server
echo 🚀 Starting development server...
echo.
echo Press Ctrl+C to stop the server
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

echo.
echo Server stopped.
pause
