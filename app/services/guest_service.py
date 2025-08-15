from typing import List, Optional, Dict, Any, Union
from sqlmodel import Session, select, or_
from fastapi import UploadFile
import csv
import io

from app.models.models import Guest
from app.schemas.schemas import GuestCreate, GuestUpdate
from app.utils.errors import NotFoundError, ConflictError
from app.utils.helpers import get_current_time
from loguru import logger

class GuestService:
    def __init__(self, session: Session):
        self.session = session
    
    async def create_guest(self, guest_data: GuestCreate) -> Guest:
        """Create a new guest"""
        # Check if guest with same email or phone already exists
        if guest_data.email or guest_data.phone:
            query = select(Guest).where(
                or_(
                    Guest.email == guest_data.email if guest_data.email else False,
                    Guest.phone == guest_data.phone if guest_data.phone else False
                )
            )
            existing_guest = self.session.exec(query).first()
            if existing_guest:
                logger.warning(f"Attempted to create duplicate guest: {guest_data.dict()}")
                raise ConflictError("Guest with this email or phone already exists")
        
        # Create new guest
        guest = Guest(
            name=guest_data.name,
            phone=guest_data.phone,
            email=guest_data.email,
            id_type=guest_data.id_type,
            id_number=guest_data.id_number,
            notes=guest_data.notes,
            is_premium=False,
            first_seen=get_current_time(),
            created_at=get_current_time()
        )
        
        self.session.add(guest)
        self.session.commit()
        self.session.refresh(guest)
        
        logger.info(f"Created new guest: {guest.id} - {guest.name}")
        return guest
    
    async def get_guest(self, guest_id: int) -> Guest:
        """Get guest by ID"""
        guest = self.session.get(Guest, guest_id)
        if not guest:
            logger.warning(f"Guest not found: {guest_id}")
            raise NotFoundError(f"Guest with ID {guest_id} not found")
        return guest
    
    async def get_guests(self, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[Guest]:
        """Get list of guests with optional search"""
        query = select(Guest)
        
        # Apply search filter if provided
        if search:
            query = query.where(
                or_(
                    Guest.name.contains(search),
                    Guest.email.contains(search),
                    Guest.phone.contains(search),
                    Guest.id_number.contains(search)
                )
            )
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        guests = self.session.exec(query).all()
        return guests
    
    async def count_guests(self, search: Optional[str] = None) -> int:
        """Count total guests with optional search"""
        query = select(Guest)
        
        # Apply search filter if provided
        if search:
            query = query.where(
                or_(
                    Guest.name.contains(search),
                    Guest.email.contains(search),
                    Guest.phone.contains(search),
                    Guest.id_number.contains(search)
                )
            )
        
        return len(self.session.exec(query).all())
    
    async def update_guest(self, guest_id: int, guest_data: GuestUpdate) -> Guest:
        """Update guest information"""
        guest = await self.get_guest(guest_id)
        
        # Update guest fields if provided
        guest_data_dict = guest_data.dict(exclude_unset=True)
        for key, value in guest_data_dict.items():
            setattr(guest, key, value)
        
        # Update last_seen if not already set in the update data
        if 'last_seen' not in guest_data_dict:
            guest.last_seen = get_current_time()
        
        # Update updated_at timestamp
        guest.updated_at = get_current_time()
        
        self.session.add(guest)
        self.session.commit()
        self.session.refresh(guest)
        
        logger.info(f"Updated guest: {guest.id} - {guest.name}")
        return guest
    
    async def delete_guest(self, guest_id: int) -> None:
        """Delete guest"""
        guest = await self.get_guest(guest_id)
        
        self.session.delete(guest)
        self.session.commit()
        
        logger.info(f"Deleted guest: {guest_id} - {guest.name}")
    
    async def update_digilocker_tokens(self, guest_id: int, token: str, refresh_token: str, expiry: Any) -> Guest:
        """Update DigiLocker tokens for guest"""
        guest = await self.get_guest(guest_id)
        
        guest.digilocker_token = token
        guest.digilocker_refresh_token = refresh_token
        guest.digilocker_token_expiry = expiry
        guest.updated_at = get_current_time()
        
        self.session.add(guest)
        self.session.commit()
        self.session.refresh(guest)
        
        logger.info(f"Updated DigiLocker tokens for guest: {guest_id}")
        return guest
    
    async def import_guests_from_csv(self, file: UploadFile) -> Dict[str, Any]:
        """Import guests from CSV file"""
        # Read CSV file
        contents = await file.read()
        csv_data = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        # Process CSV rows
        total_rows = 0
        imported = 0
        skipped = 0
        errors = []
        
        for row in csv_reader:
            total_rows += 1
            try:
                # Check if guest already exists
                query = select(Guest).where(
                    or_(
                        Guest.email == row.get('email') if row.get('email') else False,
                        Guest.phone == row.get('phone') if row.get('phone') else False
                    )
                )
                existing_guest = self.session.exec(query).first()
                
                if existing_guest:
                    skipped += 1
                    continue
                
                # Create guest from CSV data
                guest = Guest(
                    name=row.get('name', ''),
                    phone=row.get('phone'),
                    email=row.get('email'),
                    id_type=row.get('id_type'),
                    id_number=row.get('id_number'),
                    notes=row.get('notes'),
                    is_premium=row.get('is_premium', '').lower() in ['true', 'yes', '1'],
                    first_seen=get_current_time(),
                    created_at=get_current_time()
                )
                
                self.session.add(guest)
                imported += 1
                
            except Exception as e:
                errors.append(f"Row {total_rows}: {str(e)}")
        
        # Commit all changes
        self.session.commit()
        
        logger.info(f"Imported {imported} guests from CSV, skipped {skipped}, errors: {len(errors)}")
        
        return {
            "total_rows": total_rows,
            "imported": imported,
            "skipped": skipped,
            "errors": errors
        }