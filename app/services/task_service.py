import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from sqlmodel import Session, select
from app.models.models import BackgroundTask
from app.utils.helpers import get_current_time
from app.config.config import settings
from app.services.ocr_service import OCRService
from app.services.prediction_service import PredictionService
from app.services.digilocker_service import DigiLockerService
from loguru import logger

class TaskService:

    def __init__(self, session: Session):
        self.session = session
        self.ocr_service = OCRService(session)
        self.prediction_service = PredictionService(session)
        self.digilocker_service = DigiLockerService(session)
    
    async def create_task(self, task_type: str, params: Dict[str, Any] = None) -> BackgroundTask:
        """Create a new background task"""
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            params=str(params) if params else None,
            status="pending",
            created_at=get_current_time()
        )
        
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        
        logger.info(f"Created background task: {task_id} of type: {task_type}")
        return task
    
    async def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get a task by ID"""
        return self.session.get(BackgroundTask, task_id)
    
    async def get_tasks(self, 
                       status: Optional[str] = None, 
                       task_type: Optional[str] = None,
                       limit: int = 100,
                       skip: int = 0) -> List[BackgroundTask]:
        """Get tasks with optional filtering"""
        query = select(BackgroundTask)
        
        if status:
            query = query.where(BackgroundTask.status == status)
        
        if task_type:
            query = query.where(BackgroundTask.task_type == task_type)
        
        query = query.order_by(BackgroundTask.created_at.desc()).offset(skip).limit(limit)
        return self.session.exec(query).all()
    
    async def update_task_status(self, task_id: str, status: str, 
                               result: Optional[str] = None,
                               error: Optional[str] = None) -> BackgroundTask:
        """Update a task's status"""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        task.status = status
        
        if status in ["completed", "failed"]:
            task.completed_at = get_current_time()
        
        if result is not None:
            task.result = result
        
        if error is not None:
            task.error = error
        
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        
        logger.info(f"Updated task {task_id} status to {status}")
        return task
    
    async def execute_task(self, task_id: str) -> BackgroundTask:
        """Execute a pending task"""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        if task.status != "pending":
            logger.warning(f"Task {task_id} is not pending (current status: {task.status})")
            return task
        
        # Update task to running
        await self.update_task_status(task_id, "running")
        
        try:
            # Execute task based on type
            if task.task_type == "ocr_processing":
                result = await self._execute_ocr_task(task)
            elif task.task_type == "ml_training":
                result = await self._execute_ml_task(task)
            elif task.task_type == "digilocker_fetch":
                result = await self._execute_digilocker_task(task)
            elif task.task_type == "system_backup":
                result = await self._execute_backup_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            # Update task to completed with result
            await self.update_task_status(task_id, "completed", result=str(result))
            
        except Exception as e:
            logger.error(f"Task {task_id} execution failed: {str(e)}")
            # Update task to failed with error
            await self.update_task_status(task_id, "failed", error=str(e))
        
        # Refresh task
        return await self.get_task(task_id)
    
    async def _execute_ocr_task(self, task: BackgroundTask) -> Dict[str, Any]:
        """Execute OCR processing task"""
        if not task.params:
            raise ValueError("OCR task requires parameters")
        
        # Parse params
        import ast
        params = ast.literal_eval(task.params)
        
        document_path = params.get("document_path")
        if not document_path:
            raise ValueError("OCR task requires document_path parameter")
        
        # Process OCR
        ocr_result = await self.ocr_service.process_document(document_path)
        
        return ocr_result
    
    async def _execute_ml_task(self, task: BackgroundTask) -> Dict[str, Any]:
        """Execute ML training task"""
        # Train model
        training_result = await self.prediction_service.train_model(task.task_id)
        
        return training_result
    
    async def _execute_digilocker_task(self, task: BackgroundTask) -> Dict[str, Any]:
        """Execute DigiLocker document fetch task"""
        if not task.params:
            raise ValueError("DigiLocker task requires parameters")
        
        # Parse params
        import ast
        params = ast.literal_eval(task.params)
        
        guest_id = params.get("guest_id")
        if not guest_id:
            raise ValueError("DigiLocker task requires guest_id parameter")
        
        # Fetch documents
        documents = await self.digilocker_service.fetch_documents(guest_id)
        
        return {"documents": documents}
    
    async def get_tasks(self, 
                       status: Optional[str] = None, 
                       task_type: Optional[str] = None,
                       limit: int = 100,
                       skip: int = 0) -> List[BackgroundTask]:
        """Get tasks with optional filtering"""
        query = select(BackgroundTask)
        
        if status:
            query = query.where(BackgroundTask.status == status)
        
        if task_type:
            query = query.where(BackgroundTask.task_type == task_type)
        
        query = query.order_by(BackgroundTask.created_at.desc()).offset(skip).limit(limit)
        return self.session.exec(query).all()
    
    async def _execute_backup_task(self, task: BackgroundTask) -> Dict[str, Any]:
        """Execute system backup task"""
        from app.utils.backup import create_backup
        
        # Create backup
        backup_path = await create_backup()
        
        return {"backup_path": backup_path}
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up old completed or failed tasks"""
        cutoff_date = get_current_time() - timedelta(days=days)
        
        query = select(BackgroundTask).where(
            BackgroundTask.status.in_(["completed", "failed"]),
            BackgroundTask.completed_at < cutoff_date
        )
        
        tasks_to_delete = self.session.exec(query).all()
        count = len(tasks_to_delete)
        
        for task in tasks_to_delete:
            self.session.delete(task)
        
        self.session.commit()
        logger.info(f"Cleaned up {count} old tasks")
        
        return count
    
    async def retry_failed_task(self, task_id: str) -> BackgroundTask:
        """Retry a failed task"""
        task = await self.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        if task.status != "failed":
            raise ValueError(f"Task {task_id} is not failed (current status: {task.status})")
        
        # Reset task status
        task.status = "pending"
        task.error = None
        task.result = None
        task.completed_at = None
        task.updated_at = get_current_time()
        
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        
        logger.info(f"Reset failed task {task_id} for retry")
        return task
    
    async def process_pending_tasks(self, limit: int = 10) -> List[BackgroundTask]:
        """Process a batch of pending tasks"""
        query = select(BackgroundTask).where(BackgroundTask.status == "pending").order_by(BackgroundTask.created_at).limit(limit)
        pending_tasks = self.session.exec(query).all()
        
        processed_tasks = []
        for task in pending_tasks:
            processed_task = await self.execute_task(task.task_id)
            processed_tasks.append(processed_task)
        
        return processed_tasks