#!/bin/bash
# Azure App Service startup script for Hotel Management Backend

echo "Starting Hotel Management Backend on Azure..."

# Create necessary directories
mkdir -p uploads/ocr
mkdir -p ml_models
mkdir -p data
mkdir -p logs
mkdir -p backups

# Generate ML models if they don't exist
if [ ! -f "ml_models/occupancy_model.joblib" ]; then
    echo "Generating ML models..."
    python generate_ml_models.py
fi

# Start the application with Gunicorn
echo "Starting application with Gunicorn..."
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --keep-alive 5
