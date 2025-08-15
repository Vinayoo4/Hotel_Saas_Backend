#!/bin/bash
echo "Starting Hotel Management Backend Server in PRODUCTION mode..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy env.example to .env and configure your production settings"
    exit 1
fi

# Create necessary directories
mkdir -p uploads/ocr
mkdir -p ml_models
mkdir -p data
mkdir -p logs
mkdir -p backups

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

# Check if requirements are installed
echo "Checking dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error installing dependencies"
        exit 1
    fi
fi

# Set production environment variables
export ENVIRONMENT=production
export DEBUG=false

# Start the production server with Gunicorn (if available) or uvicorn
echo "Starting production server..."
if command -v gunicorn &> /dev/null; then
    echo "Using Gunicorn with Uvicorn workers..."
    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --keep-alive 5
else
    echo "Using Uvicorn (install gunicorn for better production performance)..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
fi
