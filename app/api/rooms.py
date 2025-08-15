from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.database import get_session
from app.models.models import Room
from app.schemas.schemas import RoomCreate, RoomRead, RoomUpdate, RoomList
from app.services.room_service import RoomService
from app.auth.auth import get_current_active_user, get_current_admin_user
from app.utils.errors import NotFoundError, BadRequestError
from loguru import logger

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.post("/", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    room: RoomCreate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Create a new room (admin only)"""
    room_service = RoomService(session)
    try:
        return await room_service.create_room(room)
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=RoomList)
async def get_rooms(
    skip: int = 0,
    limit: int = 100,
    room_type: Optional[str] = None,
    available_only: bool = False,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get all rooms with optional filtering"""
    room_service = RoomService(session)
    if available_only:
        rooms = await room_service.get_available_rooms(room_type)
        total = len(rooms)
    else:
        rooms, total = await room_service.get_rooms(skip, limit, room_type)
    return {"rooms": rooms, "total": total}

@router.get("/{room_id}", response_model=RoomRead)
async def get_room(
    room_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get a specific room by ID"""
    room_service = RoomService(session)
    try:
        return await room_service.get_room(room_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{room_id}", response_model=RoomRead)
async def update_room(
    room_id: int,
    room: RoomUpdate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Update a room (admin only)"""
    room_service = RoomService(session)
    try:
        return await room_service.update_room(room_id, room)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Delete a room (admin only)"""
    room_service = RoomService(session)
    try:
        await room_service.delete_room(room_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed_rooms(
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Seed initial room data (admin only)"""
    room_service = RoomService(session)
    try:
        result = await room_service.seed_rooms()
        return {
            "message": "Rooms seeded successfully",
            "created_count": result["created"],
            "skipped_count": result["skipped"]
        }
    except Exception as e:
        logger.error(f"Error seeding rooms: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error seeding rooms: {str(e)}")

@router.get("/stats/occupancy", response_model=dict)
async def get_occupancy_stats(
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get room occupancy statistics"""
    room_service = RoomService(session)
    stats = await room_service.get_occupancy_stats()
    return stats

@router.put("/{room_id}/maintenance", response_model=RoomRead)
async def toggle_maintenance_mode(
    room_id: int,
    maintenance_mode: bool,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Toggle room maintenance mode (admin only)"""
    room_service = RoomService(session)
    try:
        return await room_service.toggle_maintenance_mode(room_id, maintenance_mode)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))