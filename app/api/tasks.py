from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.schemas import BackgroundTaskRead, BackgroundTaskList
from app.services.task_service import TaskService
from app.auth.auth import get_current_active_user, get_current_admin_user
from app.utils.errors import NotFoundError, BadRequestError
from loguru import logger

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=BackgroundTaskList)
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Get all background tasks with optional filtering (admin only)"""
    task_service = TaskService(session)
    tasks = await task_service.get_tasks(status, task_type, limit, skip)
    return {"tasks": tasks, "total": len(tasks)}

@router.get("/{task_id}", response_model=BackgroundTaskRead)
async def get_task(
    task_id: str,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get a specific background task by ID"""
    task_service = TaskService(session)
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}")
    return task

@router.post("/{task_id}/execute", response_model=BackgroundTaskRead)
async def execute_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Execute a pending task (admin only)"""
    task_service = TaskService(session)
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")
        
        if task.status != "pending":
            raise BadRequestError(f"Task {task_id} is not pending (current status: {task.status})")
        
        # Start task execution in background
        background_tasks.add_task(task_service.execute_task, task_id)
        
        # Update task to running
        return await task_service.update_task_status(task_id, "running")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{task_id}/retry", response_model=BackgroundTaskRead)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Retry a failed task (admin only)"""
    task_service = TaskService(session)
    try:
        # Reset task for retry
        task = await task_service.retry_failed_task(task_id)
        
        # Start task execution in background
        background_tasks.add_task(task_service.execute_task, task_id)
        
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Delete a background task (admin only)"""
    task_service = TaskService(session)
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task not found: {task_id}")
    
    session.delete(task)
    session.commit()

@router.post("/process-pending", response_model=dict)
async def process_pending_tasks(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user),
    limit: int = 10
):
    """Process a batch of pending tasks (admin only)"""
    task_service = TaskService(session)
    
    # Start processing in background
    background_tasks.add_task(task_service.process_pending_tasks, limit)
    
    return {"message": f"Processing up to {limit} pending tasks in the background"}

@router.post("/cleanup", response_model=dict)
async def cleanup_old_tasks(
    days: int = 30,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Clean up old completed or failed tasks (admin only)"""
    task_service = TaskService(session)
    count = await task_service.cleanup_old_tasks(days)
    return {"message": f"Cleaned up {count} old tasks"}