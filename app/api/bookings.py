from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from datetime import date, datetime, timedelta

from app.db.database import get_session
from app.models.models import Booking
from app.schemas.schemas import BookingCreate, BookingRead, BookingUpdate, BookingList, InvoiceLineItemCreate, InvoiceTaxCreate, InvoiceDiscountCreate
from app.services.booking_service import BookingService
from app.services.email_service import EmailService
from app.auth.auth import get_current_active_user, get_current_admin_user
from app.utils.errors import NotFoundError, BadRequestError
from app.utils.helpers import get_current_time
from loguru import logger

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking: BookingCreate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Create a new booking"""
    booking_service = BookingService(session)
    try:
        new_booking = await booking_service.create_booking(booking)
        
        # Send booking confirmation email
        try:
            email_service = EmailService()
            guest = new_booking.guest
            if guest and guest.email:
                # Format dates for email template
                checkin_date = new_booking.checkin_at.strftime("%Y-%m-%d")
                checkout_date = new_booking.checkout_at.strftime("%Y-%m-%d") if new_booking.checkout_at else "Not checked out"
                
                # Prepare booking data for email template
                booking_data = {
                    "guest_name": guest.name,
                    "booking_id": new_booking.id,
                    "checkin_date": checkin_date,
                    "checkout_date": checkout_date,
                    "room_type": new_booking.room.room_type if new_booking.room else "Not assigned",
                    "room_number": new_booking.room.number if new_booking.room else "Not assigned",
                    "total_amount": f"${new_booking.grand_total:.2f}" if new_booking.grand_total else "Not calculated"
                }
                
                await email_service.send_booking_confirmation(booking_data, guest.email)
        except Exception as e:
            # Log error but don't fail the booking creation
            logger.error(f"Failed to send booking confirmation email: {str(e)}")
        
        return new_booking
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=BookingList)
async def get_bookings(
    skip: int = 0,
    limit: int = 100,
    guest_id: Optional[int] = None,
    room_id: Optional[int] = None,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get all bookings with optional filtering"""
    booking_service = BookingService(session)
    bookings, total = await booking_service.get_bookings(
        skip, limit, guest_id, room_id, status, from_date, to_date
    )
    return {"bookings": bookings, "total": total}

@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Get a specific booking by ID"""
    booking_service = BookingService(session)
    try:
        return await booking_service.get_booking(booking_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{booking_id}", response_model=BookingRead)
async def update_booking(
    booking_id: int,
    booking: BookingUpdate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Update a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.update_booking(booking_id, booking)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_booking(
    booking_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Delete a booking (admin only)"""
    booking_service = BookingService(session)
    try:
        await booking_service.delete_booking(booking_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{booking_id}/checkin", response_model=BookingRead)
async def checkin_booking(
    booking_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Check in a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.checkin_booking(booking_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{booking_id}/checkout", response_model=BookingRead)
async def checkout_booking(
    booking_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Check out a booking"""
    booking_service = BookingService(session)
    try:
        booking = await booking_service.checkout_booking(booking_id)
        
        # Send invoice email
        try:
            email_service = EmailService()
            guest = booking.guest
            if guest and guest.email:
                # Get invoice details from service
                invoice_details = await booking_service.get_booking_with_invoice_details(booking.id)
                
                # Format invoice items for email template
                invoice_items_html = ""
                for item in invoice_details["line_items"]:
                    item_html = f"""
                    <tr>
                        <td>{item.description}</td>
                        <td>{item.quantity}</td>
                        <td>${item.unit_price:.2f}</td>
                        <td>${item.amount:.2f}</td>
                    </tr>
                    """
                    invoice_items_html += item_html
                
                # Format tax rows
                tax_rows_html = ""
                for tax in invoice_details["taxes"]:
                    tax_html = f"""
                    <tr>
                        <td colspan="3">{tax.name} ({tax.rate:.2%})</td>
                        <td>${tax.amount:.2f}</td>
                    </tr>
                    """
                    tax_rows_html += tax_html
                
                # Format discount rows
                discount_rows_html = ""
                for discount in invoice_details["discounts"]:
                    discount_html = f"""
                    <tr>
                        <td colspan="3">{discount.name}</td>
                        <td>-${discount.amount:.2f}</td>
                    </tr>
                    """
                    discount_rows_html += discount_html
                
                # Prepare invoice data for email template
                invoice_data = {
                    "guest_name": guest.name,
                    "invoice_number": f"INV-{booking.id}",
                    "booking_id": booking.id,
                    "invoice_date": get_current_time().strftime("%Y-%m-%d"),
                    "invoice_items": invoice_items_html,
                    "subtotal": f"${invoice_details['subtotal']:.2f}",
                    "tax_rows": tax_rows_html,
                    "discount_rows": discount_rows_html,
                    "total_amount": f"${invoice_details['grand_total']:.2f}"
                }
                
                await email_service.send_invoice(invoice_data, guest.email)
        except Exception as e:
            # Log error but don't fail the checkout process
            logger.error(f"Failed to send invoice email: {str(e)}")
        
        return booking
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{booking_id}/invoice-items", response_model=BookingRead)
async def add_invoice_item(
    booking_id: int,
    item: InvoiceLineItemCreate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Add an invoice line item to a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.add_invoice_item(booking_id, item)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{booking_id}/invoice-items/{item_id}", response_model=BookingRead)
async def remove_invoice_item(
    booking_id: int,
    item_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Remove an invoice line item from a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.remove_invoice_item(booking_id, item_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{booking_id}/taxes", response_model=BookingRead)
async def add_tax(
    booking_id: int,
    tax: InvoiceTaxCreate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Add a tax to a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.add_tax(booking_id, tax)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{booking_id}/taxes/{tax_id}", response_model=BookingRead)
async def remove_tax(
    booking_id: int,
    tax_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Remove a tax from a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.remove_tax(booking_id, tax_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{booking_id}/discounts", response_model=BookingRead)
async def add_discount(
    booking_id: int,
    discount: InvoiceDiscountCreate,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Add a discount to a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.add_discount(booking_id, discount)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{booking_id}/discounts/{discount_id}", response_model=BookingRead)
async def remove_discount(
    booking_id: int,
    discount_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_active_user)
):
    """Remove a discount from a booking"""
    booking_service = BookingService(session)
    try:
        return await booking_service.remove_discount(booking_id, discount_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/stats/revenue", response_model=dict)
async def get_revenue_stats(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    session: Session = Depends(get_session),
    _: dict = Depends(get_current_admin_user)
):
    """Get revenue statistics (admin only)"""
    booking_service = BookingService(session)
    
    # Default to last 30 days if dates not provided
    if not end_date:
        end_date = datetime.now().date()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    stats = await booking_service.get_revenue_stats(start_date, end_date)
    return stats