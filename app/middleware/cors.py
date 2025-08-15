from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.config import settings
from loguru import logger

def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware for the application. 
    
    Args:
       app: FastAPI application instance
    """
    # Parse allowed origins from settings
    origins = settings.CORS_ALLOW_ORIGINS if isinstance(settings.CORS_ALLOW_ORIGINS, list) else ["*"]
    
    # Log CORS configuration
    logger.info(f"Setting up CORS middleware with allowed origins: {origins}")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS if isinstance(settings.CORS_ALLOW_METHODS, list) else ["*"],
        allow_headers=settings.CORS_ALLOW_HEADERS if isinstance(settings.CORS_ALLOW_HEADERS, list) else ["*"],
        max_age=600,  # 10 minutes default
    )
    
    logger.info("CORS middleware setup complete")