from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, and_, or_
from datetime import datetime, timedelta

from app.models.models import Booking, Guest, Room, InvoiceLineItem, InvoiceTax, InvoiceDiscount
from app.schemas.schemas import BookingCreate, BookingUpdate
from app.utils.errors import NotFoundError, ConflictError, BadRequestError
from app.utils.helpers import get_current_time
from app.services.room_service import RoomService
from app.services.guest_service import GuestService
from loguru import logger

class BookingService:
    def __init__(self, session: Session):
        self.session = session
        self.room_service = RoomService(session)
        self.guest_service = GuestService(session)
    
    async def create_booking(self, booking_data: BookingCreate) -> Booking:
        """Create a new booking"""
        # Verify guest exists
        guest = await self.guest_service.get_guest(booking_data.guest_id)
        
        # Verify room exists and is available
        room = await self.room_service.get_room(booking_data.room_number)
        if room.occupied:
            logger.warning(f"Attempted to book occupied room: {room.number}")
            raise ConflictError(f"Room {room.number} is already occupied")
        
        # Create booking
        booking = Booking(
            guest_id=booking_data.guest_id,
            room_number=booking_data.room_number,
            checkin_at=get_current_time(),
            price=booking_data.price or room.rate_per_night,
            created_at=get_current_time()
        )
        
        # Mark room as occupied
        room.occupied = True
        room.current_guest_id = booking_data.guest_id
        room.updated_at = get_current_time()
        
        # Update guest's last_seen
        guest.last_seen = get_current_time()
        guest.updated_at = get_current_time()
        
        # Save changes
        self.session.add(booking)
        self.session.add(room)
        self.session.add(guest)
        self.session.commit()
        self.session.refresh(booking)
        
        # Add default line item for room charge
        line_item = InvoiceLineItem(
            booking_id=booking.id,
            description=f"{room.room_type} Room - {room.number}",
            quantity=1,
            unit_price=booking.price,
            amount=booking.price,
            item_type="room",
            created_at=get_current_time()
        )
        self.session.add(line_item)
        
        # Update booking totals
        booking.subtotal = booking.price
        booking.grand_total = booking.price
        self.session.add(booking)
        self.session.commit()
        self.session.refresh(booking)
        
        logger.info(f"Created booking {booking.id} for guest {guest.id} in room {room.number}")
        return booking
    
    async def get_booking(self, booking_id: int) -> Booking:
        """Get booking by ID"""
        booking = self.session.get(Booking, booking_id)
        if not booking:
            logger.warning(f"Booking not found: {booking_id}")
            raise NotFoundError(f"Booking with ID {booking_id} not found")
        return booking
    
    async def get_bookings(self, 
                          skip: int = 0, 
                          limit: int = 100,
                          guest_id: Optional[int] = None,
                          room_number: Optional[int] = None,
                          status: Optional[str] = None,
                          from_date: Optional[datetime] = None,
                          to_date: Optional[datetime] = None) -> Tuple[List[Booking], int]:
        """Get list of bookings with optional filters"""
        query = select(Booking)
        
        # Apply guest filter if provided
        if guest_id:
            query = query.where(Booking.guest_id == guest_id)
        
        # Apply room filter if provided
        if room_number:
            query = query.where(Booking.room_number == room_number)
        
        # Apply status filter if provided
        if status:
            if status == "active":
                query = query.where(Booking.checkout_at == None)
            elif status == "completed":
                query = query.where(Booking.checkout_at != None)
        
        # Apply date filters if provided
        if from_date:
            query = query.where(Booking.checkin_at >= from_date)
        if to_date:
            query = query.where(Booking.checkin_at <= to_date)
        
        # Get total count before pagination
        total_count = len(self.session.exec(query).all())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        bookings = self.session.exec(query).all()
        return bookings, total_count
    
    async def count_bookings(self,
                            guest_id: Optional[int] = None,
                            room_number: Optional[int] = None,
                            active_only: bool = False) -> int:
        """Count total bookings with optional filters"""
        query = select(Booking)
        
        # Apply guest filter if provided
        if guest_id:
            query = query.where(Booking.guest_id == guest_id)
        
        # Apply room filter if provided
        if room_number:
            query = query.where(Booking.room_number == room_number)
        
        # Apply active filter if requested
        if active_only:
            query = query.where(Booking.checkout_at == None)
        
        return len(self.session.exec(query).all())
    
    async def update_booking(self, booking_id: int, booking_data: BookingUpdate) -> Booking:
        """Update booking information"""
        booking = await self.get_booking(booking_id)
        
        # Update booking fields if provided
        booking_data_dict = booking_data.dict(exclude_unset=True)
        for key, value in booking_data_dict.items():
            setattr(booking, key, value)
        
        # Handle checkout if provided
        if booking_data.checkout_at and not booking.checkout_at:
            # Vacate the room
            await self.room_service.vacate_room(booking.room_number)
            
            # If price not provided, calculate based on duration
            if not booking_data.price and not booking.price:
                room = await self.room_service.get_room(booking.room_number)
                duration = (booking.checkout_at - booking.checkin_at).days or 1
                booking.price = room.rate_per_night * duration
        
        # Update updated_at timestamp
        booking.updated_at = get_current_time()
        
        self.session.add(booking)
        self.session.commit()
        self.session.refresh(booking)
        
        logger.info(f"Updated booking: {booking.id}")
        return booking
    
    async def checkin_booking(self, booking_id: int) -> Booking:
        """Check in a booking"""
        booking = await self.get_booking(booking_id)
        
        # Check if already checked in
        if booking.checkin_at:
            logger.warning(f"Attempted to checkin already checked-in booking: {booking_id}")
            raise ConflictError(f"Booking {booking_id} is already checked in")
        
        # Set checkin time
        checkin_time = get_current_time()
        booking.checkin_at = checkin_time
        booking.updated_at = checkin_time
        
        # Mark room as occupied
        room = await self.room_service.get_room(booking.room_number)
        await self.room_service.occupy_room(room.number, booking.guest_id)
        
        self.session.add(booking)
        self.session.commit()
        self.session.refresh(booking)
        
        logger.info(f"Checked in booking: {booking.id}")
        return booking
    
    async def checkout_booking(self, booking_id: int) -> Booking:
        """Checkout a booking"""
        booking = await self.get_booking(booking_id)
        
        # Check if already checked out
        if booking.checkout_at:
            logger.warning(f"Attempted to checkout already completed booking: {booking_id}")
            raise ConflictError(f"Booking {booking_id} is already checked out")
        
        # Set checkout time
        checkout_time = get_current_time()
        
        # Calculate duration and final price
        duration = (checkout_time - booking.checkin_at).days or 1
        room = await self.room_service.get_room(booking.room_number)
        
        # Update booking
        booking.checkout_at = checkout_time
        booking.updated_at = checkout_time
        
        # Vacate the room
        await self.room_service.vacate_room(booking.room_number)
        
        # Update line items if needed
        line_items = await self.get_line_items(booking_id)
        room_item = next((item for item in line_items if item.item_type == "room"), None)
        
        if room_item:
            # Update room line item with correct duration
            room_item.quantity = duration
            room_item.amount = room_item.unit_price * duration
            room_item.updated_at = checkout_time
            self.session.add(room_item)
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        self.session.commit()
        self.session.refresh(booking)
        
        logger.info(f"Checked out booking: {booking.id} after {duration} days")
        return booking
    
    async def delete_booking(self, booking_id: int) -> None:
        """Delete booking"""
        booking = await self.get_booking(booking_id)
        
        # If booking is active, vacate the room
        if not booking.checkout_at:
            try:
                await self.room_service.vacate_room(booking.room_number)
            except Exception as e:
                logger.warning(f"Failed to vacate room during booking deletion: {str(e)}")
        
        # Delete related invoice items
        await self.delete_all_invoice_items(booking_id)
        
        # Delete booking
        self.session.delete(booking)
        self.session.commit()
        
        logger.info(f"Deleted booking: {booking_id}")
    
    # Invoice line item methods
    async def add_invoice_item(self, booking_id: int, item_data) -> Booking:
        """Add invoice line item to booking"""
        # Create line item
        line_item = InvoiceLineItem(
            booking_id=booking_id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            amount=item_data.quantity * item_data.unit_price,
            item_type=item_data.item_type,
            created_at=get_current_time()
        )
        
        self.session.add(line_item)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Added invoice item to booking {booking_id}: {item_data.description}")
        return await self.get_booking(booking_id)
    
    async def remove_invoice_item(self, booking_id: int, item_id: int) -> Booking:
        """Remove invoice line item from booking"""
        line_item = self.session.get(InvoiceLineItem, item_id)
        if not line_item:
            raise NotFoundError(f"Line item with ID {item_id} not found")
        
        # Don't allow deleting the room charge for active bookings
        booking = await self.get_booking(booking_id)
        if line_item.item_type == "room" and not booking.checkout_at:
            raise BadRequestError("Cannot delete room charge for active booking")
        
        self.session.delete(line_item)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Removed invoice item {item_id} from booking {booking_id}")
        return await self.get_booking(booking_id)
    
    async def add_line_item(self, booking_id: int, description: str, quantity: float, unit_price: float, item_type: str = "extra") -> InvoiceLineItem:
        """Add line item to booking invoice"""
        booking = await self.get_booking(booking_id)
        
        # Create line item
        line_item = InvoiceLineItem(
            booking_id=booking_id,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            amount=quantity * unit_price,
            item_type=item_type,
            created_at=get_current_time()
        )
        
        self.session.add(line_item)
        self.session.commit()
        self.session.refresh(line_item)
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Added line item to booking {booking_id}: {description}")
        return line_item
    
    async def get_line_items(self, booking_id: int) -> List[InvoiceLineItem]:
        """Get all line items for a booking"""
        query = select(InvoiceLineItem).where(InvoiceLineItem.booking_id == booking_id)
        return self.session.exec(query).all()
    
    async def delete_line_item(self, line_item_id: int) -> None:
        """Delete line item from booking invoice"""
        line_item = self.session.get(InvoiceLineItem, line_item_id)
        if not line_item:
            raise NotFoundError(f"Line item with ID {line_item_id} not found")
        
        booking_id = line_item.booking_id
        
        # Don't allow deleting the room charge for active bookings
        booking = await self.get_booking(booking_id)
        if line_item.item_type == "room" and not booking.checkout_at:
            raise BadRequestError("Cannot delete room charge for active booking")
        
        self.session.delete(line_item)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Deleted line item {line_item_id} from booking {booking_id}")
    
    async def delete_all_invoice_items(self, booking_id: int) -> None:
        """Delete all invoice items for a booking"""
        # Delete line items
        line_items_query = select(InvoiceLineItem).where(InvoiceLineItem.booking_id == booking_id)
        line_items = self.session.exec(line_items_query).all()
        for item in line_items:
            self.session.delete(item)
        
        # Delete taxes
        taxes_query = select(InvoiceTax).where(InvoiceTax.booking_id == booking_id)
        taxes = self.session.exec(taxes_query).all()
        for tax in taxes:
            self.session.delete(tax)
        
        # Delete discounts
        discounts_query = select(InvoiceDiscount).where(InvoiceDiscount.booking_id == booking_id)
        discounts = self.session.exec(discounts_query).all()
        for discount in discounts:
            self.session.delete(discount)
        
        self.session.commit()
        logger.info(f"Deleted all invoice items for booking {booking_id}")
    
    # Tax methods
    async def add_tax(self, booking_id: int, tax_data) -> Booking:
        """Add tax to booking invoice"""
        # Calculate tax amount
        booking = await self.get_booking(booking_id)
        if not booking.subtotal:
            await self.recalculate_booking_totals(booking_id)
            self.session.refresh(booking)
        
        tax_amount = booking.subtotal * (tax_data.rate / 100)
        
        # Create tax
        tax = InvoiceTax(
            booking_id=booking_id,
            name=tax_data.name,
            rate=tax_data.rate,
            amount=tax_amount,
            created_at=get_current_time()
        )
        
        self.session.add(tax)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Added tax to booking {booking_id}: {tax_data.name} at {tax_data.rate}%")
        return await self.get_booking(booking_id)
    
    async def remove_tax(self, booking_id: int, tax_id: int) -> Booking:
        """Remove tax from booking invoice"""
        tax = self.session.get(InvoiceTax, tax_id)
        if not tax:
            raise NotFoundError(f"Tax with ID {tax_id} not found")
        
        self.session.delete(tax)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Deleted tax {tax_id} from booking {booking_id}")
        return await self.get_booking(booking_id)
    
    async def add_tax(self, booking_id: int, name: str, rate: float) -> InvoiceTax:
        """Add tax to booking invoice"""
        booking = await self.get_booking(booking_id)
        
        # Calculate tax amount
        if not booking.subtotal:
            await self.recalculate_booking_totals(booking_id)
            self.session.refresh(booking)
        
        tax_amount = booking.subtotal * (rate / 100)
        
        # Create tax
        tax = InvoiceTax(
            booking_id=booking_id,
            name=name,
            rate=rate,
            amount=tax_amount,
            created_at=get_current_time()
        )
        
        self.session.add(tax)
        self.session.commit()
        self.session.refresh(tax)
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Added tax to booking {booking_id}: {name} at {rate}%")
        return tax
    
    async def get_taxes(self, booking_id: int) -> List[InvoiceTax]:
        """Get all taxes for a booking"""
        query = select(InvoiceTax).where(InvoiceTax.booking_id == booking_id)
        return self.session.exec(query).all()
    
    async def delete_tax(self, tax_id: int) -> None:
        """Delete tax from booking invoice"""
        tax = self.session.get(InvoiceTax, tax_id)
        if not tax:
            raise NotFoundError(f"Tax with ID {tax_id} not found")
        
        booking_id = tax.booking_id
        
        self.session.delete(tax)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Deleted tax {tax_id} from booking {booking_id}")
    
    # Discount methods
    async def add_discount(self, booking_id: int, discount_data) -> Booking:
        """Add discount to booking invoice"""
        if discount_data.amount is None and discount_data.percentage is None:
            raise BadRequestError("Either amount or percentage must be provided")
        
        booking = await self.get_booking(booking_id)
        
        # Calculate discount amount
        if not booking.subtotal:
            await self.recalculate_booking_totals(booking_id)
            self.session.refresh(booking)
        
        if discount_data.percentage is not None:
            discount_amount = booking.subtotal * (discount_data.percentage / 100)
        else:
            discount_amount = discount_data.amount or 0
        
        # Create discount
        discount = InvoiceDiscount(
            booking_id=booking_id,
            name=discount_data.name,
            amount=discount_amount,
            percentage=discount_data.percentage,
            created_at=get_current_time()
        )
        
        self.session.add(discount)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Added discount to booking {booking_id}: {discount_data.name}")
        return await self.get_booking(booking_id)
    
    async def remove_discount(self, booking_id: int, discount_id: int) -> Booking:
        """Remove discount from booking invoice"""
        discount = self.session.get(InvoiceDiscount, discount_id)
        if not discount:
            raise NotFoundError(f"Discount with ID {discount_id} not found")
        
        self.session.delete(discount)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Deleted discount {discount_id} from booking {booking_id}")
        return await self.get_booking(booking_id)
    
    async def add_discount(self, booking_id: int, name: str, amount: Optional[float] = None, percentage: Optional[float] = None) -> InvoiceDiscount:
        """Add discount to booking invoice"""
        if amount is None and percentage is None:
            raise BadRequestError("Either amount or percentage must be provided")
        
        booking = await self.get_booking(booking_id)
        
        # Calculate discount amount
        if not booking.subtotal:
            await self.recalculate_booking_totals(booking_id)
            self.session.refresh(booking)
        
        if percentage is not None:
            discount_amount = booking.subtotal * (percentage / 100)
        else:
            discount_amount = amount or 0
        
        # Create discount
        discount = InvoiceDiscount(
            booking_id=booking_id,
            name=name,
            amount=discount_amount,
            percentage=percentage,
            created_at=get_current_time()
        )
        
        self.session.add(discount)
        self.session.commit()
        self.session.refresh(discount)
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Added discount to booking {booking_id}: {name}")
        return discount
    
    async def get_discounts(self, booking_id: int) -> List[InvoiceDiscount]:
        """Get all discounts for a booking"""
        query = select(InvoiceDiscount).where(InvoiceDiscount.booking_id == booking_id)
        return self.session.exec(query).all()
    
    async def delete_discount(self, discount_id: int) -> None:
        """Delete discount from booking invoice"""
        discount = self.session.get(InvoiceDiscount, discount_id)
        if not discount:
            raise NotFoundError(f"Discount with ID {discount_id} not found")
        
        booking_id = discount.booking_id
        
        self.session.delete(discount)
        self.session.commit()
        
        # Recalculate totals
        await self.recalculate_booking_totals(booking_id)
        
        logger.info(f"Deleted discount {discount_id} from booking {booking_id}")
    
    # Helper methods
    async def recalculate_booking_totals(self, booking_id: int) -> Booking:
        """Recalculate booking totals"""
        booking = await self.get_booking(booking_id)
        
        # Calculate subtotal from line items
        line_items = await self.get_line_items(booking_id)
        subtotal = sum(item.amount for item in line_items)
        
        # Calculate tax total
        taxes = await self.get_taxes(booking_id)
        tax_total = 0
        for tax in taxes:
            # Recalculate tax amount based on current subtotal
            tax.amount = subtotal * (tax.rate / 100)
            tax_total += tax.amount
            self.session.add(tax)
        
        # Calculate discount total
        discounts = await self.get_discounts(booking_id)
        discount_total = 0
        for discount in discounts:
            # Recalculate percentage-based discounts
            if discount.percentage is not None:
                discount.amount = subtotal * (discount.percentage / 100)
            discount_total += discount.amount
            self.session.add(discount)
        
        # Calculate grand total
        grand_total = subtotal + tax_total - discount_total
        
        # Update booking
        booking.subtotal = subtotal
        booking.tax_total = tax_total
        booking.discount_total = discount_total
        booking.grand_total = grand_total
        booking.updated_at = get_current_time()
        
        self.session.add(booking)
        self.session.commit()
        self.session.refresh(booking)
        
        return booking
    
    async def get_active_bookings(self) -> List[Booking]:
        """Get all active (not checked out) bookings"""
        return await self.get_bookings(active_only=True)
    
    async def get_booking_with_invoice_details(self, booking_id: int) -> Dict[str, Any]:
        """Get booking with all invoice details"""
        booking = await self.get_booking(booking_id)
        line_items = await self.get_line_items(booking_id)
        taxes = await self.get_taxes(booking_id)
        discounts = await self.get_discounts(booking_id)
        
        return {
            "booking": booking,
            "line_items": line_items,
            "taxes": taxes,
            "discounts": discounts,
            "subtotal": booking.subtotal or 0,
            "tax_total": booking.tax_total or 0,
            "discount_total": booking.discount_total or 0,
            "grand_total": booking.grand_total or 0
        }
    
    async def get_booking_statistics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get booking statistics for a date range"""
        # Set default date range if not provided
        if not end_date:
            end_date = get_current_time()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Query for bookings in date range
        query = select(Booking).where(
            and_(
                Booking.checkin_at >= start_date,
                or_(
                    Booking.checkout_at <= end_date,
                    Booking.checkout_at == None
                )
            )
        )
        bookings = self.session.exec(query).all()
        
        # Calculate statistics
        total_bookings = len(bookings)
        completed_bookings = sum(1 for b in bookings if b.checkout_at is not None)
        active_bookings = total_bookings - completed_bookings
        
        total_revenue = sum(b.grand_total or 0 for b in bookings if b.grand_total is not None)
        avg_booking_value = total_revenue / total_bookings if total_bookings > 0 else 0
        
        # Calculate average stay duration for completed bookings
        stay_durations = []
        for booking in bookings:
            if booking.checkout_at:
                duration = (booking.checkout_at - booking.checkin_at).days or 1
                stay_durations.append(duration)
        
        avg_stay_duration = sum(stay_durations) / len(stay_durations) if stay_durations else 0
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "active_bookings": active_bookings,
            "total_revenue": total_revenue,
            "avg_booking_value": avg_booking_value,
            "avg_stay_duration": avg_stay_duration
        }
    
    async def get_revenue_stats(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get revenue statistics for a date range"""
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Query for completed bookings in date range
        query = select(Booking).where(
            and_(
                Booking.checkout_at >= start_date,
                Booking.checkout_at <= end_date,
                Booking.checkout_at != None
            )
        )
        bookings = self.session.exec(query).all()
        
        # Calculate revenue statistics
        total_revenue = sum(b.grand_total or 0 for b in bookings if b.grand_total is not None)
        total_bookings = len(bookings)
        avg_booking_value = total_revenue / total_bookings if total_bookings > 0 else 0
        
        # Daily revenue breakdown
        daily_revenue = {}
        for booking in bookings:
            checkout_date = booking.checkout_at.date()
            if checkout_date not in daily_revenue:
                daily_revenue[checkout_date] = 0
            daily_revenue[checkout_date] += booking.grand_total or 0
        
        # Sort daily revenue by date
        sorted_daily_revenue = sorted(daily_revenue.items())
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_revenue": total_revenue,
            "total_bookings": total_bookings,
            "avg_booking_value": avg_booking_value,
            "daily_revenue": sorted_daily_revenue
        }