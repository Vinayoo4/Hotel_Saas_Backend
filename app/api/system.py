from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlmodel import Session, select
import os
from datetime import datetime

from app.db.database import get_session
from app.schemas.schemas import BackgroundTaskRead
from app.services.task_service import TaskService
from app.utils.backup import list_backups, cleanup_old_backups
from app.auth.auth import get_current_admin_user
from app.utils.errors import NotFoundError, BadRequestError
from loguru import logger

router = APIRouter(prefix="/system", tags=["system"])

@router.post("/backup", response_model=BackgroundTaskRead)
async def create_backup(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Create a full system backup (admin only)"""
    task_service = TaskService(session)
    
    try:
        # Create backup task
        task = await task_service.create_task(
            task_type="system_backup",
            params={}
        )
        
        # Start task execution in background
        background_tasks.add_task(task_service.execute_task, task.task_id)
        
        return task
    except Exception as e:
        logger.error(f"Error creating backup task: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating backup task: {str(e)}")

@router.get("/backups", response_model=List[dict])
async def get_backups(_: dict = Depends(get_current_admin_user)):
    """List all available backups (admin only)"""
    try:
        backups = list_backups()
        return backups
    except Exception as e:
        logger.error(f"Error listing backups: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error listing backups: {str(e)}")

@router.post("/backups/{backup_id}/restore", response_model=BackgroundTaskRead)
async def restore_backup(
    backup_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Restore system from a backup (admin only)"""
    task_service = TaskService(session)
    
    # Check if backup exists
    backups = list_backups()
    backup = next((b for b in backups if b["id"] == backup_id), None)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Backup not found: {backup_id}")
    
    try:
        # Create restore task
        task = await task_service.create_task(
            task_type="system_restore",
            params={"backup_id": backup_id}
        )
        
        # Start task execution in background
        background_tasks.add_task(task_service.execute_task, task.task_id)
        
        return task
    except Exception as e:
        logger.error(f"Error creating restore task: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating restore task: {str(e)}")

@router.delete("/backups/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: str,
    _: dict = Depends(get_current_admin_user)
):
    """Delete a specific backup (admin only)"""
    # Check if backup exists
    backups = list_backups()
    backup = next((b for b in backups if b["id"] == backup_id), None)
    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Backup not found: {backup_id}")
    
    try:
        # Delete backup file
        backup_path = backup["path"]
        if os.path.exists(backup_path):
            os.remove(backup_path)
            logger.info(f"Deleted backup: {backup_id}")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Backup file not found: {backup_path}")
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting backup: {str(e)}")

@router.post("/backups/cleanup", response_model=dict)
async def cleanup_backups(
    days: int = 30,
    _: dict = Depends(get_current_admin_user)
):
    """Clean up old backups (admin only)"""
    try:
        count = cleanup_old_backups(days)
        return {"message": f"Cleaned up {count} old backups"}
    except Exception as e:
        logger.error(f"Error cleaning up backups: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error cleaning up backups: {str(e)}")

@router.post("/backups/upload", response_model=dict)
async def upload_backup(
    backup_file: UploadFile = File(...),
    _: dict = Depends(get_current_admin_user)
):
    """Upload a backup file (admin only)"""
    try:
        # Ensure backup directory exists
        from app.config import settings
        backup_dir = settings.BACKUP_DIR
        os.makedirs(backup_dir, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(backup_dir, backup_file.filename)
        with open(file_path, "wb") as f:
            content = await backup_file.read()
            f.write(content)
        
        logger.info(f"Uploaded backup file: {backup_file.filename}")
        return {"message": f"Backup file uploaded: {backup_file.filename}"}
    except Exception as e:
        logger.error(f"Error uploading backup: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error uploading backup: {str(e)}")

@router.get("/health", response_model=dict)
async def health_check(session: Session = Depends(get_session)):
    """Enhanced system health check endpoint with database check (public)"""
    health = {
        "status": "ok",
        "timestamp": str(datetime.now()),
        "version": "1.0.0",  # Hardcoded for now
        "environment": "production" if not settings.DEBUG else "development",
    }
    
    try:
        # Check database connectivity
        session.exec(select(1))
        health["database"] = "connected"
    except Exception as e:
        health["status"] = "error"
        health["database"] = f"error: {str(e)}"
    
    return health