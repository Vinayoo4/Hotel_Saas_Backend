from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.schemas import DigiLockerAuthResponse, DigiLockerDocumentList, BackgroundTaskRead
from app.services.digilocker_service import DigiLockerService
from app.services.guest_service import GuestService
from app.services.task_service import TaskService
from app.auth.auth import get_current_active_user, get_current_admin_user
from app.utils.errors import NotFoundError, BadRequestError
from loguru import logger

router = APIRouter(prefix="/digilocker", tags=["digilocker"])

@router.get("/auth-url", response_model=DigiLockerAuthResponse)
async def get_auth_url(
    guest_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get DigiLocker authorization URL for a guest"""
    digilocker_service = DigiLockerService(session)
    try:
        # First check if guest exists
        guest_service = GuestService(session)
        await guest_service.get_guest(guest_id)
        
        # Generate auth URL
        auth_url = await digilocker_service.get_authorization_url(guest_id)
        return {"auth_url": auth_url, "guest_id": guest_id}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/callback")
async def digilocker_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: Session = Depends(get_session)
):
    """Handle DigiLocker authorization callback"""
    digilocker_service = DigiLockerService(session)
    try:
        # Extract guest ID from state parameter
        guest_id = int(state)
        
        # Exchange code for token
        token_info = await digilocker_service.exchange_code_for_token(code)
        
        # Update guest's DigiLocker token
        await digilocker_service.update_guest_tokens(guest_id, token_info["access_token"], token_info["refresh_token"], token_info["expires_in"])
        
        # Create background task to fetch documents
        task = await digilocker_service.create_fetch_documents_task(guest_id)
        
        # Return success page with HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DigiLocker Authorization Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .success {{ color: green; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">DigiLocker Authorization Successful</h1>
                <p>Your DigiLocker account has been successfully linked.</p>
                <p>We are now fetching your documents in the background.</p>
                <p>You can close this window and return to the application.</p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        logger.error(f"DigiLocker callback error: {str(e)}")
        # Return error page with HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DigiLocker Authorization Failed</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .error {{ color: red; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="error">DigiLocker Authorization Failed</h1>
                <p>There was an error linking your DigiLocker account:</p>
                <p>{str(e)}</p>
                <p>Please try again or contact support.</p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content, status_code=400)

@router.get("/documents/{guest_id}", response_model=DigiLockerDocumentList)
async def get_documents(
    guest_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get a guest's DigiLocker documents"""
    digilocker_service = DigiLockerService(session)
    try:
        # First check if guest exists
        guest_service = GuestService(session)
        guest = await guest_service.get_guest(guest_id)
        
        if not guest.digilocker_token:
            raise BadRequestError("Guest has not authorized DigiLocker access")
        
        # Fetch documents
        documents = await digilocker_service.fetch_documents(task.task_id, guest_id)
        return {"documents": documents, "guest_id": guest_id}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/refresh-token/{guest_id}", response_model=dict)
async def refresh_token(
    guest_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Refresh a guest's DigiLocker token"""
    digilocker_service = DigiLockerService(session)
    try:
        # First check if guest exists
        guest_service = GuestService(session)
        guest = await guest_service.get_guest(guest_id)
        
        if not guest.digilocker_refresh_token:
            raise BadRequestError("Guest has no DigiLocker refresh token")
        
        # Refresh token
        token_info = await digilocker_service.refresh_token(guest.digilocker_refresh_token)
        
        # Update guest's token
        await digilocker_service.update_guest_tokens(guest_id, token_info["access_token"], token_info["refresh_token"], token_info["expires_in"])
        
        return {"message": "Token refreshed successfully", "guest_id": guest_id}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/tasks/{task_id}", response_model=BackgroundTaskRead)
async def get_digilocker_task(
    task_id: str,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get DigiLocker task status and result"""
    task_service = TaskService(session)
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")
        
        if task.task_type != "digilocker_fetch":
            raise BadRequestError(f"Task {task_id} is not a DigiLocker fetch task")
        
        return task
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# Import this at the top of the file
from fastapi.responses import HTMLResponse