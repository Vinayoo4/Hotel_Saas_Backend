from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

# Base model for common fields
class TimeStampModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

# Guest model
class Guest(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    id_type: Optional[str] = None  # Aadhaar/PAN/Passport
    id_number: Optional[str] = None
    is_premium: bool = False
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None
    notes: Optional[str] = None
    digilocker_token: Optional[str] = None
    digilocker_refresh_token: Optional[str] = None
    digilocker_token_expiry: Optional[datetime] = None
    
    # Relationships
    bookings: List["Booking"] = Relationship(back_populates="guest")

# Room model
class Room(TimeStampModel, table=True):
    number: int = Field(primary_key=True)
    room_type: str = "Standard"  # Standard/Premium/Suite
    occupied: bool = False
    current_guest_id: Optional[int] = None
    rate_per_night: float = 1000.0
    notes: Optional[str] = None
    
    # Relationships
    bookings: List["Booking"] = Relationship(back_populates="room")

# Booking model
class Booking(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    guest_id: int = Field(foreign_key="guest.id")
    room_number: int = Field(foreign_key="room.number")
    checkin_at: datetime = Field(default_factory=datetime.utcnow)
    checkout_at: Optional[datetime] = None
    price: Optional[float] = None
    invoice_path: Optional[str] = None
    subtotal: Optional[float] = None
    tax_total: Optional[float] = None
    discount_total: Optional[float] = None
    grand_total: Optional[float] = None
    
    # Relationships
    guest: Guest = Relationship(back_populates="bookings")
    room: Room = Relationship(back_populates="bookings")
    line_items: List["InvoiceLineItem"] = Relationship(back_populates="booking")
    taxes: List["InvoiceTax"] = Relationship(back_populates="booking")
    discounts: List["InvoiceDiscount"] = Relationship(back_populates="booking")

# Invoice Line Item model
class InvoiceLineItem(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")
    description: str
    quantity: float = 1.0
    unit_price: float
    amount: float
    item_type: str = "room"  # room, service, food, etc.
    
    # Relationships
    booking: Booking = Relationship(back_populates="line_items")

# Invoice Tax model
class InvoiceTax(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")
    name: str  # GST, Service Tax, etc.
    rate: float  # percentage
    amount: float
    
    # Relationships
    booking: Booking = Relationship(back_populates="taxes")

# Invoice Discount model
class InvoiceDiscount(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id")
    name: str  # Loyalty Discount, Seasonal Offer, etc.
    amount: float
    percentage: Optional[float] = None  # if discount is percentage-based
    
    # Relationships
    booking: Booking = Relationship(back_populates="discounts")

# Prediction Data Point model
class PredictionDataPoint(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(default_factory=datetime.utcnow)
    day_of_week: int  # 0-6 (Monday-Sunday)
    month: int  # 1-12
    is_holiday: bool = False
    is_weekend: bool = False
    occupancy_rate: float  # percentage of rooms occupied
    avg_stay_duration: Optional[float] = None  # in days
    avg_room_rate: Optional[float] = None
    weather_condition: Optional[str] = None  # sunny, rainy, etc.
    local_events: Optional[str] = None  # festivals, conferences, etc.

# Background Task model
class BackgroundTask(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(unique=True)
    task_type: str  # ocr, digilocker_fetch, train_model, etc.
    status: str  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result: Optional[str] = None  # JSON string of result
    error: Optional[str] = None
    params: Optional[str] = None  # JSON string of parameters

# User model for authentication
class User(TimeStampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    role: str = "receptionist"  # admin, receptionist, etc.