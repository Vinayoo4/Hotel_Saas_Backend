from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.schemas import OCRResponse, OCRTaskCreate, BackgroundTaskRead
from app.services.ocr_service import OCRService
from app.services.task_service import TaskService
from app.auth.auth import get_current_active_user
from app.utils.errors import NotFoundError, BadRequestError
from app.utils.helpers import save_upload_file
from loguru import logger

router = APIRouter(prefix="/ocr", tags=["ocr"])

@router.post("/process", response_model=OCRResponse)
async def process_document(
    document: UploadFile = File(...),
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Process a document with OCR synchronously"""
    ocr_service = OCRService(session)
    try:
        # Save uploaded file
        document_path = await save_upload_file(document, "ocr")
        
        # Process document
        result = await ocr_service.process_document(str(document_path))
        return result
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR processing failed: {str(e)}")

@router.post("/process-async", response_model=BackgroundTaskRead)
async def process_document_async(
    document: UploadFile = File(...),
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Process a document with OCR asynchronously"""
    ocr_service = OCRService(session)
    task_service = TaskService(session)
    
    try:
        # Save uploaded file
        document_path = await save_upload_file(document, "ocr")
        
        # Create OCR task
        task_params = {"document_path": str(document_path)}
        task = await task_service.create_task("ocr_processing", task_params)
        
        # Start task execution in background
        background_task = BackgroundTasks()
        background_task.add_task(task_service.execute_task, task.task_id)
        
        return task
    except Exception as e:
        logger.error(f"OCR task creation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR task creation failed: {str(e)}")

@router.get("/tasks/{task_id}", response_model=BackgroundTaskRead)
async def get_ocr_task(
    task_id: str,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get OCR task status and result"""
    task_service = TaskService(session)
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")
        
        if task.task_type != "ocr_processing":
            raise BadRequestError(f"Task {task_id} is not an OCR processing task")
        
        return task
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))