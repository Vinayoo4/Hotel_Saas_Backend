@echo off
title Hotel Management Backend - Project Setup
color 0B

echo.
echo ========================================
echo   Hotel Management Backend
echo   Project Setup Script
echo ========================================
echo.

:: Check if Python is installed
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed or not in PATH
    echo.
    echo Please install Python 3.9 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

:: Display Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% found

:: Check Python version (3.9+)
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version_info[1])" 2^>^&1') do set PYTHON_MINOR=%%i
if %PYTHON_MINOR% LSS 9 (
    echo ❌ Python 3.9 or higher is required
    echo Current version: %PYTHON_VERSION%
    pause
    exit /b 1
)

:: Create virtual environment
echo.
echo 🔄 Creating virtual environment...
if exist ".venv" (
    echo ⚠️  Virtual environment already exists
    echo Removing old environment...
    rmdir /s /q ".venv"
)

python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b 1
)
echo ✅ Virtual environment created

:: Activate virtual environment
echo 🔄 Activating virtual environment...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

:: Upgrade pip
echo 🔄 Upgrading pip...
python -m pip install --upgrade pip

:: Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install dependencies
    echo.
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo ✅ Dependencies installed successfully

:: Create necessary directories
echo 📁 Creating project directories...
if not exist "uploads\ocr" mkdir "uploads\ocr"
if not exist "ml_models" mkdir "ml_models"
if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"
if not exist "backups" mkdir "backups"
echo ✅ Project directories created

:: Generate ML models
echo 🧠 Generating ML models...
python generate_ml_models.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to generate ML models
    pause
    exit /b 1
)
echo ✅ ML models generated

:: Test configuration
echo 🔍 Testing configuration...
python -c "from app.main import app; print('Configuration test successful')" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Configuration test failed
    echo Please check the error messages above
    pause
    exit /b 1
)
echo ✅ Configuration test passed

:: Display completion message
echo.
echo ========================================
echo   🎉 Setup Complete!
echo ========================================
echo.
echo Your Hotel Management Backend is ready!
echo.
echo To start the development server:
echo   start_development.bat
echo.
echo To start the production server:
echo   start_production.bat
echo.
echo API Documentation will be available at:
echo   http://localhost:8000/docs
echo.
echo ========================================
echo.

pause
