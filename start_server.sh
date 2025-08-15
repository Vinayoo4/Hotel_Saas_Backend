#!/bin/bash
echo "Starting Hotel Management Backend Server..."

# Create necessary directories
mkdir -p uploads/ocr
mkdir -p ml_models
mkdir -p data
mkdir -p logs
mkdir -p backups

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python is not installed"
    echo "Please install Python 3.8 or higher"
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

# Start the server
echo "Starting server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000