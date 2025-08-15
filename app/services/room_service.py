from typing import List, Optional, Dict, Any
from sqlmodel import Session, select

from app.models.models import Room
from app.schemas.schemas import RoomCreate, RoomUpdate, RoomType
from app.utils.errors import NotFoundError, ConflictError
from app.utils.helpers import get_current_time
from loguru import logger

class RoomService:
    def __init__(self, session: Session):
        self.session = session
    
    async def create_room(self, room_data: RoomCreate) -> Room:
        """Create a new room"""
        # Check if room with same number already exists
        query = select(Room).where(Room.number == room_data.number)
        existing_room = self.session.exec(query).first()
        if existing_room:
            logger.warning(f"Attempted to create duplicate room: {room_data.number}")
            raise ConflictError(f"Room with number {room_data.number} already exists")
        
        # Create new room
        room = Room(
            number=room_data.number,
            room_type=room_data.room_type,
            rate_per_night=room_data.rate_per_night,
            occupied=False,
            created_at=get_current_time()
        )
        
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        
        logger.info(f"Created new room: {room.number} - {room.room_type}")
        return room
    
    async def get_room(self, room_number: int) -> Room:
        """Get room by number"""
        query = select(Room).where(Room.number == room_number)
        room = self.session.exec(query).first()
        if not room:
            logger.warning(f"Room not found: {room_number}")
            raise NotFoundError(f"Room with number {room_number} not found")
        return room
    
    async def get_rooms(self, 
                       skip: int = 0, 
                       limit: int = 100, 
                       room_type: Optional[RoomType] = None,
                       occupied: Optional[bool] = None) -> List[Room]:
        """Get list of rooms with optional filters"""
        query = select(Room)
        
        # Apply room type filter if provided
        if room_type:
            query = query.where(Room.room_type == room_type)
        
        # Apply occupied filter if provided
        if occupied is not None:
            query = query.where(Room.occupied == occupied)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        rooms = self.session.exec(query).all()
        return rooms
    
    async def count_rooms(self, 
                         room_type: Optional[RoomType] = None,
                         occupied: Optional[bool] = None) -> int:
        """Count total rooms with optional filters"""
        query = select(Room)
        
        # Apply room type filter if provided
        if room_type:
            query = query.where(Room.room_type == room_type)
        
        # Apply occupied filter if provided
        if occupied is not None:
            query = query.where(Room.occupied == occupied)
        
        return len(self.session.exec(query).all())
    
    async def update_room(self, room_number: int, room_data: RoomUpdate) -> Room:
        """Update room information"""
        room = await self.get_room(room_number)
        
        # Update room fields if provided
        room_data_dict = room_data.dict(exclude_unset=True)
        for key, value in room_data_dict.items():
            setattr(room, key, value)
        
        # Update updated_at timestamp
        room.updated_at = get_current_time()
        
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        
        logger.info(f"Updated room: {room.number} - {room.room_type}")
        return room
    
    async def delete_room(self, room_number: int) -> None:
        """Delete room"""
        room = await self.get_room(room_number)
        
        # Check if room is occupied
        if room.occupied:
            logger.warning(f"Attempted to delete occupied room: {room_number}")
            raise ConflictError(f"Cannot delete room {room_number} as it is currently occupied")
        
        self.session.delete(room)
        self.session.commit()
        
        logger.info(f"Deleted room: {room_number}")
    
    async def occupy_room(self, room_number: int, guest_id: int) -> Room:
        """Mark room as occupied by a guest"""
        room = await self.get_room(room_number)
        
        # Check if room is already occupied
        if room.occupied:
            logger.warning(f"Attempted to occupy already occupied room: {room_number}")
            raise ConflictError(f"Room {room_number} is already occupied")
        
        # Update room status
        room.occupied = True
        room.current_guest_id = guest_id
        room.updated_at = get_current_time()
        
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        
        logger.info(f"Room {room_number} occupied by guest {guest_id}")
        return room
    
    async def vacate_room(self, room_number: int) -> Room:
        """Mark room as vacant"""
        room = await self.get_room(room_number)
        
        # Check if room is already vacant
        if not room.occupied:
            logger.warning(f"Attempted to vacate already vacant room: {room_number}")
            raise ConflictError(f"Room {room_number} is already vacant")
        
        # Update room status
        room.occupied = False
        room.current_guest_id = None
        room.updated_at = get_current_time()
        
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        
        logger.info(f"Room {room_number} vacated")
        return room
    
    async def get_available_rooms(self, room_type: Optional[RoomType] = None) -> List[Room]:
        """Get list of available (unoccupied) rooms"""
        return await self.get_rooms(occupied=False, room_type=room_type)
    
    async def get_occupied_rooms(self, room_type: Optional[RoomType] = None) -> List[Room]:
        """Get list of occupied rooms"""
        return await self.get_rooms(occupied=True, room_type=room_type)
    
    async def seed_rooms(self) -> Dict[str, Any]:
        """Seed rooms if none exist"""
        # Check if rooms already exist
        existing_count = await self.count_rooms()
        if existing_count > 0:
            logger.info(f"Rooms already seeded, found {existing_count} rooms")
            return {"seeded": False, "existing_count": existing_count}
        
        # Define room types and counts
        room_types = {
            RoomType.STANDARD: {"count": 10, "rate": 1000.0},
            RoomType.PREMIUM: {"count": 7, "rate": 1500.0},
            RoomType.SUITE: {"count": 3, "rate": 2500.0}
        }
        
        # Create rooms
        created_count = 0
        room_number = 101
        
        for room_type, config in room_types.items():
            for _ in range(config["count"]):
                room = Room(
                    number=room_number,
                    room_type=room_type,
                    rate_per_night=config["rate"],
                    occupied=False,
                    created_at=get_current_time()
                )
                
                self.session.add(room)
                created_count += 1
                room_number += 1
        
        self.session.commit()
        
        logger.info(f"Seeded {created_count} rooms")
        return {"seeded": True, "created_count": created_count}
    
    async def get_occupancy_stats(self) -> Dict[str, Any]:
        """Get room occupancy statistics"""
        total_rooms = await self.count_rooms()
        occupied_rooms = await self.count_rooms(occupied=True)
        available_rooms = await self.count_rooms(occupied=False)
        
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        # Get occupancy by room type
        room_types = ["Standard", "Premium", "Suite"]
        occupancy_by_type = {}
        
        for room_type in room_types:
            total_type = await self.count_rooms(room_type=room_type)
            occupied_type = await self.count_rooms(room_type=room_type, occupied=True)
            occupancy_by_type[room_type] = {
                "total": total_type,
                "occupied": occupied_type,
                "available": total_type - occupied_type,
                "occupancy_rate": (occupied_type / total_type * 100) if total_type > 0 else 0
            }
        
        return {
            "total_rooms": total_rooms,
            "occupied_rooms": occupied_rooms,
            "available_rooms": available_rooms,
            "occupancy_rate": round(occupancy_rate, 2),
            "by_type": occupancy_by_type
        }
    
    async def toggle_maintenance_mode(self, room_number: int, maintenance_mode: bool) -> Room:
        """Toggle room maintenance mode"""
        room = await self.get_room(room_number)
        
        # Add maintenance field if it doesn't exist in the model
        # For now, we'll use a custom field approach
        if hasattr(room, 'maintenance_mode'):
            room.maintenance_mode = maintenance_mode
        else:
            # If maintenance field doesn't exist, we'll add a note
            if maintenance_mode:
                room.notes = f"Maintenance mode: {get_current_time()}"
            else:
                room.notes = None
        
        room.updated_at = get_current_time()
        
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        
        logger.info(f"Room {room_number} maintenance mode: {maintenance_mode}")
        return room