import os
import secrets
from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Hotel Management Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///hotel.db")
    DB_ECHO_LOG: bool = os.getenv("DB_ECHO_LOG", "false").lower() == "true"
    POSTGRES_USER: Optional[str] = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_SERVER: Optional[str] = os.getenv("POSTGRES_SERVER")
    POSTGRES_PORT: Optional[str] = os.getenv("POSTGRES_PORT")
    POSTGRES_DB: Optional[str] = os.getenv("POSTGRES_DB")
    
    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    # CORS Settings
    CORS_ALLOW_ORIGINS: List[str] = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",") if os.getenv("CORS_ALLOW_ORIGINS") else ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    CORS_ALLOW_METHODS: List[str] = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",") if os.getenv("CORS_ALLOW_METHODS") else ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = os.getenv("CORS_ALLOW_HEADERS", "*").split(",") if os.getenv("CORS_ALLOW_HEADERS") else ["*"]
    
    # DigiLocker OAuth Settings
    DIGILOCKER_CLIENT_ID: Optional[str] = os.getenv("DIGILOCKER_CLIENT_ID")
    DIGILOCKER_CLIENT_SECRET: Optional[str] = os.getenv("DIGILOCKER_CLIENT_SECRET")
    DIGILOCKER_REDIRECT_URI: Optional[str] = os.getenv("DIGILOCKER_REDIRECT_URI")
    DIGILOCKER_AUTH_URL: str = os.getenv("DIGILOCKER_AUTH_URL", "https://api.digitallocker.gov.in/public/oauth2/1/authorize")
    DIGILOCKER_TOKEN_URL: str = os.getenv("DIGILOCKER_TOKEN_URL", "https://api.digitallocker.gov.in/public/oauth2/1/token")
    DIGILOCKER_API_BASE: str = os.getenv("DIGILOCKER_API_BASE", "https://api.digitallocker.gov.in/public/api/1.0")
    
    # OCR Settings
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")
    OCR_UPLOAD_DIR: str = os.getenv("OCR_UPLOAD_DIR", "./uploads/ocr")
    OCR_DEFAULT_LANGUAGE: str = os.getenv("OCR_DEFAULT_LANGUAGE", "eng")
    
    # ML Model Settings
    ML_MODEL_DIR: str = os.getenv("ML_MODEL_DIR", "./ml_models")
    ML_MIN_DATA_POINTS: int = int(os.getenv("ML_MIN_DATA_POINTS", "50"))
    ML_RETRAIN_THRESHOLD: int = int(os.getenv("ML_RETRAIN_THRESHOLD", "20"))
    
    # Backup Settings
    BACKUP_ENABLED: bool = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "./backups")
    BACKUP_INTERVAL_HOURS: int = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
    
    # Email Settings
    SMTP_SERVER: Optional[str] = os.getenv("SMTP_SERVER")
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM: Optional[str] = os.getenv("EMAIL_FROM")
    
    # Logging
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/app.log")
    
    # Initial Admin User
    INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
    INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")
    
    # Upload directory
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # Rate limiting per minute (for backward compatibility)
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    
    # Construct PostgreSQL URL if individual components are provided
    @validator("DATABASE_URL", pre=True)
    def assemble_postgres_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if v and not v.startswith("sqlite"):
            return v
            
        if all(values.get(key) for key in ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SERVER", "POSTGRES_DB"]):
            port = values.get("POSTGRES_PORT", "5432")
            return f"postgresql://{values['POSTGRES_USER']}:{values['POSTGRES_PASSWORD']}@{values['POSTGRES_SERVER']}:{port}/{values['POSTGRES_DB']}"
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance with error handling
try:
    settings = Settings()
except Exception as e:
    # Fallback to default settings if environment parsing fails
    print(f"Warning: Failed to parse environment settings: {e}")
    print("Using default configuration...")
    
    # Create a minimal settings object with defaults
    class FallbackSettings:
        OCR_UPLOAD_DIR = "./uploads/ocr"
        ML_MODEL_DIR = "./ml_models"
        BACKUP_DIR = "./backups"
        UPLOAD_DIR = "./uploads"
        APP_NAME = "Hotel Management Backend"
        VERSION = "1.0.0"
        ENVIRONMENT = "development"
        DEBUG = True
        SECRET_KEY = "fallback-secret-key-change-in-production"
        JWT_SECRET_KEY = "fallback-jwt-secret-change-in-production"
        DATABASE_URL = "sqlite:///hotel.db"
        HOST = "127.0.0.1"
        PORT = 8000
        API_PREFIX = "/api/v1"
        CORS_ALLOW_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
        CORS_ALLOW_CREDENTIALS = True
        CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        CORS_ALLOW_HEADERS = ["*"]
        JWT_ALGORITHM = "HS256"
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
        RATE_LIMIT_ENABLED = True
        RATE_LIMIT_REQUESTS = 100
        RATE_LIMIT_WINDOW_SECONDS = 60
        TESSERACT_CMD = "tesseract"
        OCR_DEFAULT_LANGUAGE = "eng"
        ML_MIN_DATA_POINTS = 50
        ML_RETRAIN_THRESHOLD = 20
        BACKUP_ENABLED = True
        BACKUP_INTERVAL_HOURS = 24
        LOG_LEVEL = "INFO"
        LOG_FILE = "./logs/app.log"
        INITIAL_ADMIN_EMAIL = "admin@example.com"
        INITIAL_ADMIN_PASSWORD = "admin123"
        # Add missing attributes
        DIGILOCKER_CLIENT_ID = None
        DIGILOCKER_CLIENT_SECRET = None
        DIGILOCKER_REDIRECT_URI = None
        DIGILOCKER_AUTH_URL = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
        DIGILOCKER_TOKEN_URL = "https://api.digitallocker.gov.in/public/oauth2/1/token"
        DIGILOCKER_API_BASE = "https://api.digitallocker.gov.in/public/api/1.0"
        SMTP_SERVER = None
        SMTP_PORT = None
        SMTP_USERNAME = None
        SMTP_PASSWORD = None
        EMAIL_FROM = None
        DB_ECHO_LOG = False
        POSTGRES_USER = None
        POSTGRES_PASSWORD = None
        POSTGRES_SERVER = None
        POSTGRES_PORT = None
        POSTGRES_DB = None
        RATE_LIMIT_PER_MINUTE = 100
    
    settings = FallbackSettings()

# Create directory structure
os.makedirs(settings.OCR_UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.ML_MODEL_DIR, exist_ok=True)
os.makedirs(settings.BACKUP_DIR, exist_ok=True)

# Paths for ML models
OCCUPANCY_MODEL_PATH = os.path.join(settings.ML_MODEL_DIR, "occupancy_model.joblib")
SCALER_PATH = os.path.join(settings.ML_MODEL_DIR, "scaler.joblib")

# For backward compatibility with existing code
CONFIG = {
    "app": {
        "name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "secret_key": settings.SECRET_KEY
    },
    "server": {
        "host": settings.HOST,
        "port": settings.PORT
    },
    "database": {
        "url": settings.DATABASE_URL
    },
    "jwt": {
        "secret_key": settings.JWT_SECRET_KEY,
        "algorithm": settings.JWT_ALGORITHM,
        "access_token_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    },
    "rate_limit": {
        "enabled": settings.RATE_LIMIT_ENABLED,
        "requests": settings.RATE_LIMIT_REQUESTS,
        "window_seconds": settings.RATE_LIMIT_WINDOW_SECONDS
    },
    "cors": {
        "allow_origins": settings.CORS_ALLOW_ORIGINS,
        "allow_credentials": settings.CORS_ALLOW_CREDENTIALS,
        "allow_methods": settings.CORS_ALLOW_METHODS,
        "allow_headers": settings.CORS_ALLOW_HEADERS
    },
    "digilocker": {
        "client_id": settings.DIGILOCKER_CLIENT_ID,
        "client_secret": settings.DIGILOCKER_CLIENT_SECRET,
        "redirect_uri": settings.DIGILOCKER_REDIRECT_URI,
        "auth_url": settings.DIGILOCKER_AUTH_URL,
        "token_url": settings.DIGILOCKER_TOKEN_URL,
        "api_base": settings.DIGILOCKER_API_BASE
    },
    "ocr": {
        "tesseract_path": settings.TESSERACT_CMD,
        "upload_dir": settings.OCR_UPLOAD_DIR,
        "default_language": settings.OCR_DEFAULT_LANGUAGE
    },
    "ml": {
        "model_dir": settings.ML_MODEL_DIR,
        "min_data_points": settings.ML_MIN_DATA_POINTS,
        "retrain_threshold": settings.ML_RETRAIN_THRESHOLD
    },
    "backup": {
        "enabled": settings.BACKUP_ENABLED,
        "dir": settings.BACKUP_DIR,
        "interval_hours": settings.BACKUP_INTERVAL_HOURS
    },
    "email": {
        "smtp_server": settings.SMTP_SERVER,
        "smtp_port": settings.SMTP_PORT,
        "smtp_username": settings.SMTP_USERNAME,
        "smtp_password": settings.SMTP_PASSWORD,
        "from": settings.EMAIL_FROM
    }
}