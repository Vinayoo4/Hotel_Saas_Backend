from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from sqlmodel import Session

from app.db.database import get_session
from app.models.models import Guest
from app.schemas.schemas import GuestCreate, GuestRead, GuestUpdate, GuestList, DigiLockerTokenUpdate
from app.services.guest_service import GuestService
from app.services.digilocker_service import DigiLockerService
from app.auth.auth import get_current_active_user, get_current_admin_user
from app.utils.errors import NotFoundError, BadRequestError
from app.utils.helpers import save_upload_file
from loguru import logger

router = APIRouter(prefix="/guests", tags=["guests"])

@router.post("/", response_model=GuestRead, status_code=status.HTTP_201_CREATED)
async def create_guest(
    guest: GuestCreate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Create a new guest"""
    guest_service = GuestService(session)
    try:
        return await guest_service.create_guest(guest)
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=GuestList)
async def get_guests(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get all guests with optional search"""
    guest_service = GuestService(session)
    guests, total = await guest_service.get_guests(skip, limit, search)
    return {"guests": guests, "total": total}

@router.get("/{guest_id}", response_model=GuestRead)
async def get_guest(
    guest_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get a specific guest by ID"""
    guest_service = GuestService(session)
    try:
        return await guest_service.get_guest(guest_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{guest_id}", response_model=GuestRead)
async def update_guest(
    guest_id: int,
    guest: GuestUpdate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Update a guest"""
    guest_service = GuestService(session)
    try:
        return await guest_service.update_guest(guest_id, guest)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest(
    guest_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Delete a guest (admin only)"""
    guest_service = GuestService(session)
    try:
        await guest_service.delete_guest(guest_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/import", response_model=dict, status_code=status.HTTP_200_OK)
async def import_guests(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Import guests from CSV file (admin only)"""
    guest_service = GuestService(session)
    try:
        result = await guest_service.import_guests_from_csv(file)
        return {
            "message": "Guests imported successfully",
            "imported_count": result["imported"],
            "skipped_count": result["skipped"],
            "errors": result["errors"]
        }
    except Exception as e:
        logger.error(f"Error importing guests: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error importing guests: {str(e)}")

@router.put("/{guest_id}/digilocker", response_model=GuestRead)
async def update_digilocker_token(
    guest_id: int,
    token_data: DigiLockerTokenUpdate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Update a guest's DigiLocker token information"""
    guest_service = GuestService(session)
    try:
        return await guest_service.update_digilocker_tokens(
            guest_id, 
            token_data.digilocker_token, 
            token_data.digilocker_refresh_token, 
            token_data.digilocker_token_expiry
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{guest_id}/digilocker/auth-url", response_model=dict)
async def get_digilocker_auth_url(
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
        return {"auth_url": auth_url}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{guest_id}/digilocker/callback")
async def digilocker_callback(
    guest_id: int,
    code: str = Query(...),
    session: Session = Depends(get_session)
):
    """Handle DigiLocker authorization callback"""
    digilocker_service = DigiLockerService(session)
    try:
        # Exchange code for token
        token_info = await digilocker_service.exchange_code_for_token(code)
        
        # Update guest's DigiLocker token
        guest_service = GuestService(session)
        await guest_service.update_digilocker_tokens(
            guest_id, 
            token_info["access_token"], 
            token_info["refresh_token"], 
            token_info["expires_at"]
        )
        
        # Create background task to fetch documents
        await digilocker_service.create_fetch_documents_task(guest_id)
        
        return {"message": "DigiLocker authorization successful"}
    except Exception as e:
        logger.error(f"DigiLocker callback error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"DigiLocker authorization failed: {str(e)}")

@router.get("/{guest_id}/digilocker/documents", response_model=dict)
async def get_digilocker_documents(
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
        documents = await digilocker_service.fetch_documents(guest_id)
        return {"documents": documents}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))