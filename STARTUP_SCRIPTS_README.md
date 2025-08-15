# 🚀 Hotel Management Backend - Startup Scripts Guide

This guide explains how to use the startup scripts to run the Hotel Management Backend on different operating systems.

## 📋 Prerequisites

- **Python 3.9 or higher** installed and added to PATH
- **Git** (for cloning the repository)
- **Internet connection** (for installing dependencies)

## 🗂️ Available Scripts

### **Setup Scripts** (Run once for initial setup)

| OS | Script | Description |
|----|--------|-------------|
| Windows | `setup_project.bat` | Initial project setup for Windows |
| Linux/Mac | `setup_project.sh` | Initial project setup for Linux/Mac |

### **Development Scripts** (For development/testing)

| OS | Script | Description |
|----|--------|-------------|
| Windows | `start_development.bat` | Start development server on Windows |
| Linux/Mac | `start_development.sh` | Start development server on Linux/Mac |

### **Production Scripts** (For production deployment)

| OS | Script | Description |
|----|--------|-------------|
| Windows | `start_production.bat` | Start production server on Windows |
| Linux/Mac | `start_production.sh` | Start production server on Linux/Mac |

## 🚀 Quick Start Guide

### **Step 1: Clone the Repository**
```bash
git clone <your-repository-url>
cd Hotel_management_Backend_python
```

### **Step 2: Initial Setup** (Choose your OS)

#### **Windows:**
```cmd
setup_project.bat
```

#### **Linux/Mac:**
```bash
chmod +x setup_project.sh
./setup_project.sh
```

### **Step 3: Start the Server** (Choose your mode)

#### **Development Mode:**
```cmd
# Windows
start_development.bat

# Linux/Mac
./start_development.sh
```

#### **Production Mode:**
```cmd
# Windows
start_production.bat

# Linux/Mac
./start_production.sh
```

## 🔧 What Each Script Does

### **Setup Scripts (`setup_project.*`)**
- ✅ Check Python version (3.9+ required)
- ✅ Create virtual environment (`.venv`)
- ✅ Install all dependencies from `requirements.txt`
- ✅ Create necessary directories (`uploads/`, `ml_models/`, `logs/`, etc.)
- ✅ Generate ML models for occupancy prediction
- ✅ Test configuration and imports
- ✅ Make scripts executable (Linux/Mac only)

### **Development Scripts (`start_development.*`)**
- ✅ Activate virtual environment
- ✅ Check dependencies
- ✅ Create directories if missing
- ✅ Generate ML models if missing
- ✅ Start server with auto-reload
- ✅ Display server information and URLs

### **Production Scripts (`start_production.*`)**
- ✅ Activate virtual environment
- ✅ Check dependencies
- ✅ Create directories if missing
- ✅ Generate ML models if missing
- ✅ Start multi-worker production server
- ✅ Use Gunicorn if available, fallback to Uvicorn

## 🌐 Server Access

After starting the server, you can access:

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Root Endpoint**: http://localhost:8000/
- **API Base**: http://localhost:8000/api/v1/

## 🛠️ Troubleshooting

### **Common Issues and Solutions**

#### **1. "Python is not installed" Error**
```bash
# Windows: Download from https://www.python.org/downloads/
# Make sure to check "Add Python to PATH"

# Ubuntu/Debian:
sudo apt update && sudo apt install python3 python3-venv python3-pip

# CentOS/RHEL:
sudo yum install python3 python3-venv python3-pip

# macOS:
brew install python3
```

#### **2. "Virtual environment not found" Error**
```bash
# Run the setup script first:
# Windows: setup_project.bat
# Linux/Mac: ./setup_project.sh
```

#### **3. "Dependencies installation failed" Error**
```bash
# Check internet connection
# Try upgrading pip first:
python -m pip install --upgrade pip

# Then install requirements:
pip install -r requirements.txt
```

#### **4. "ML models not found" Error**
```bash
# The scripts will automatically generate ML models
# If manual generation is needed:
python generate_ml_models.py
```

#### **5. "Port 8000 already in use" Error**
```bash
# Find what's using port 8000:
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# Kill the process or change port in the script
```

### **Manual Dependency Installation**
If automatic installation fails, install manually:

```bash
# Activate virtual environment first
# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install production dependencies (optional)
pip install gunicorn
```

## 🔒 Security Notes

### **Development Mode**
- Server accessible from all network interfaces (0.0.0.0)
- Auto-reload enabled (not suitable for production)
- Debug mode enabled
- SQLite database (for development only)

### **Production Mode**
- Multi-worker setup for better performance
- Gunicorn recommended for production
- Use PostgreSQL database in production
- Set proper environment variables
- Enable HTTPS in production

## 📁 Directory Structure Created

```
Hotel_management_Backend_python/
├── .venv/                    # Virtual environment
├── uploads/                  # File uploads
│   └── ocr/                 # OCR processed files
├── ml_models/               # Machine learning models
│   ├── occupancy_model.joblib
│   ├── occupancy_scaler.joblib
│   └── sample_data.csv
├── data/                    # Data files
├── logs/                    # Application logs
├── backups/                 # Backup files
└── hotel.db                 # SQLite database (development)
```

## 🚀 Advanced Usage

### **Custom Port Configuration**
Edit the startup scripts to change the port:

```bash
# Change from port 8000 to 8080
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### **Environment Variables**
Create a `.env` file for custom configuration:

```bash
# .env file example
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@localhost:5432/hotel
CORS_ALLOW_ORIGINS=https://yourdomain.com
```

### **Production Deployment**
For production deployment:

1. **Use production scripts**: `start_production.*`
2. **Install Gunicorn**: `pip install gunicorn`
3. **Set up reverse proxy** (Nginx/Apache)
4. **Configure SSL certificates**
5. **Use PostgreSQL database**
6. **Set up monitoring and logging**

## 📞 Support

If you encounter issues:

1. **Check the logs** in the `logs/` directory
2. **Verify Python version** (3.9+ required)
3. **Ensure virtual environment is activated**
4. **Check all dependencies are installed**
5. **Verify port 8000 is available**

## 🎯 Next Steps

After successful setup:

1. **Test the API**: Visit http://localhost:8000/docs
2. **Create admin user**: Use the default credentials
3. **Explore endpoints**: Test various API functions
4. **Customize configuration**: Update `.env` file
5. **Deploy to production**: Follow production deployment guide

---

**Happy coding! 🎉**
