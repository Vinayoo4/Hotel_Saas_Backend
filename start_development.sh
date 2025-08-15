#!/bin/bash

# Hotel Management Backend - Development Server Startup Script
# For Linux and macOS systems

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo
    echo "========================================"
    echo "  Hotel Management Backend"
    echo "  Development Server Startup"
    echo "========================================"
    echo
}

# Clear screen and show header
clear
print_header

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found!"
    echo
    echo "Please run the setup script first:"
    echo "  ./setup_project.sh"
    echo
    exit 1
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Check if Python is available
print_status "Checking Python installation..."
if ! command -v python &> /dev/null; then
    print_error "Python is not available in virtual environment"
    echo "Please check your Python installation"
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p uploads/ocr
mkdir -p ml_models
mkdir -p data
mkdir -p logs
mkdir -p backups

# Check if ML models exist
if [ ! -f "ml_models/occupancy_model.joblib" ]; then
    print_warning "ML models not found. Generating them..."
    python generate_ml_models.py
    if [ $? -ne 0 ]; then
        print_error "Failed to generate ML models"
        exit 1
    fi
fi

# Check if requirements are installed
print_status "Checking dependencies..."
if ! python -c "import fastapi" &> /dev/null; then
    print_status "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_error "Error installing dependencies"
        exit 1
    fi
fi

# Display server information
echo
echo "========================================"
echo "  Server Configuration"
echo "========================================"
echo "  Host: 0.0.0.0 (all interfaces)"
echo "  Port: 8000"
echo "  Mode: Development (auto-reload)"
echo "  API Docs: http://localhost:8000/docs"
echo "  Health Check: http://localhost:8000/health"
echo "========================================"
echo

# Start the development server
print_success "Starting development server..."
echo
echo "Press Ctrl+C to stop the server"
echo

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

echo
print_status "Server stopped."
