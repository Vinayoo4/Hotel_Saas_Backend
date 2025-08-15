from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware.rate_limiter import RateLimiter
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.cors import setup_cors
from app.config.config import settings
from loguru import logger

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
        return response

def setup_middleware(app: FastAPI) -> None:
    """
    Setup all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    logger.info("Setting up application middleware...")
    
    # Production security middleware
    if settings.ENVIRONMENT == "production":
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Setup CORS middleware
    setup_cors(app)
    
    # Setup request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Setup rate limiter middleware if enabled
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimiter,
            rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
            exclude_paths=[
                '/docs', 
                '/redoc', 
                '/openapi.json',
                '/api/health'
            ]
        )
        logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_PER_MINUTE} requests per minute")
    else:
        logger.info("Rate limiting disabled")
    
    logger.info("Middleware setup complete")