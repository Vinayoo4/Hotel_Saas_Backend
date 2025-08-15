from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from datetime import datetime

from app.config import settings
from app.db.database import init_db
from app.middleware.middleware import setup_middleware
from app.utils.logger import setup_logging

# Import API routers
from app.api.users import router as users_router, auth_router
from app.api.guests import router as guests_router
from app.api.rooms import router as rooms_router
from app.api.bookings import router as bookings_router
from app.api.ocr import router as ocr_router
from app.api.digilocker import router as digilocker_router
from app.api.predictions import router as predictions_router
from app.api.tasks import router as tasks_router
from app.api.system import router as system_router

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Hotel Management System API",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Setup middlewares
setup_middleware(app)

# Create static directories if they don't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API routers with prefix
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(guests_router, prefix=settings.API_PREFIX)
app.include_router(rooms_router, prefix=settings.API_PREFIX)
app.include_router(bookings_router, prefix=settings.API_PREFIX)
app.include_router(ocr_router, prefix=settings.API_PREFIX)
app.include_router(digilocker_router, prefix=settings.API_PREFIX)
app.include_router(predictions_router, prefix=settings.API_PREFIX)
app.include_router(tasks_router, prefix=settings.API_PREFIX)
app.include_router(system_router, prefix=settings.API_PREFIX)

@app.on_event("startup")
async def on_startup():
    """Initialize database and create tables on startup"""
    await init_db()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/api/health")
async def api_health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "api_version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

# For development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)