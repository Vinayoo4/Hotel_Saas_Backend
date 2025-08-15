from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.schemas import PredictionResponse, PredictionDataPointRead, BackgroundTaskRead
from app.services.prediction_service import PredictionService
from app.services.task_service import TaskService
from app.auth.auth import get_current_active_user, get_current_admin_user
from app.utils.errors import NotFoundError, BadRequestError
from loguru import logger

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.get("/occupancy", response_model=PredictionResponse)
async def predict_occupancy(
    days: int = 7,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Predict hotel occupancy for the next N days"""
    prediction_service = PredictionService(session)
    try:
        result = await prediction_service.predict_occupancy(days)
        return result
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction failed: {str(e)}")

@router.get("/data", response_model=List[PredictionDataPointRead])
async def get_prediction_data(
    limit: int = 100,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Get historical prediction data points (admin only)"""
    prediction_service = PredictionService(session)
    try:
        data = await prediction_service.get_prediction_data(limit)
        return data
    except Exception as e:
        logger.error(f"Error retrieving prediction data: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error retrieving prediction data: {str(e)}")

@router.post("/train", response_model=BackgroundTaskRead)
async def train_model(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Train prediction model using collected data points (admin only)"""
    prediction_service = PredictionService(session)
    task_service = TaskService(session)
    
    try:
        # Create training task
        task = await prediction_service.create_training_task()
        
        # Start task execution in background
        background_tasks.add_task(task_service.execute_task, task.task_id)
        
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating training task: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating training task: {str(e)}")

@router.get("/tasks/{task_id}", response_model=BackgroundTaskRead)
async def get_training_task(
    task_id: str,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Get ML training task status and result (admin only)"""
    task_service = TaskService(session)
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")
        
        if task.task_type != "ml_training":
            raise BadRequestError(f"Task {task_id} is not an ML training task")
        
        return task
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))