#!/bin/bash

# Hotel Management Backend - Project Setup Script
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
    echo "  Project Setup Script"
    echo "========================================"
    echo
}

# Clear screen and show header
clear
print_header

# Check if Python is installed
print_status "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo
    echo "Please install Python 3.9 or higher:"
    echo
    echo "Ubuntu/Debian:"
    echo "  sudo apt update && sudo apt install python3 python3-venv python3-pip"
    echo
    echo "CentOS/RHEL:"
    echo "  sudo yum install python3 python3-venv python3-pip"
    echo
    echo "macOS:"
    echo "  brew install python3"
    echo
    exit 1
fi

# Display Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_success "Python $PYTHON_VERSION found"

# Check Python version (3.9+)
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info[1])")
if [ "$PYTHON_MINOR" -lt 9 ]; then
    print_error "Python 3.9 or higher is required"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment
echo
print_status "Creating virtual environment..."
if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists"
    echo "Removing old environment..."
    rm -rf .venv
fi

python3 -m venv .venv
if [ $? -ne 0 ]; then
    print_error "Failed to create virtual environment"
    exit 1
fi
print_success "Virtual environment created"

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip
print_status "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies"
    echo
    echo "Please check your internet connection and try again"
    exit 1
fi
print_success "Dependencies installed successfully"

# Create necessary directories
print_status "Creating project directories..."
mkdir -p uploads/ocr
mkdir -p ml_models
mkdir -p data
mkdir -p logs
mkdir -p backups
print_success "Project directories created"

# Generate ML models
print_status "Generating ML models..."
python generate_ml_models.py
if [ $? -ne 0 ]; then
    print_error "Failed to generate ML models"
    exit 1
fi
print_success "ML models generated"

# Test configuration
print_status "Testing configuration..."
python -c "from app.main import app; print('Configuration test successful')" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    print_error "Configuration test failed"
    echo "Please check the error messages above"
    exit 1
fi
print_success "Configuration test passed"

# Make scripts executable
print_status "Making scripts executable..."
chmod +x start_development.sh
chmod +x start_production.sh
chmod +x setup_project.sh

# Display completion message
echo
echo "========================================"
echo "  🎉 Setup Complete!"
echo "========================================"
echo
echo "Your Hotel Management Backend is ready!"
echo
echo "To start the development server:"
echo "  ./start_development.sh"
echo
echo "To start the production server:"
echo "  ./start_production.sh"
echo
echo "API Documentation will be available at:"
echo "  http://localhost:8000/docs"
echo
echo "========================================"
echo
