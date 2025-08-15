from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enum for room types
class RoomType(str, Enum):
    STANDARD = "Standard"
    PREMIUM = "Premium"
    SUITE = "Suite"

# Enum for task status
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Enum for user roles
class UserRole(str, Enum):
    ADMIN = "admin"
    RECEPTIONIST = "receptionist"
    MANAGER = "manager"

# Base schemas
class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None

class ErrorResponse(BaseResponse):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.RECEPTIONIST

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

class UserRead(UserInDB):
    pass

class UserList(BaseModel):
    users: List[UserRead]
    total: int

class UserResponse(BaseResponse):
    data: UserInDB

class UsersResponse(BaseResponse):
    data: List[UserInDB]
    total: int

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserInDB

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# Guest schemas
class GuestBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    notes: Optional[str] = None

class GuestCreate(GuestBase):
    pass

class GuestUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    is_premium: Optional[bool] = None
    notes: Optional[str] = None

class GuestInDB(GuestBase):
    id: int
    is_premium: bool
    first_seen: datetime
    last_seen: Optional[datetime] = None
    digilocker_token: Optional[str] = None
    digilocker_refresh_token: Optional[str] = None
    digilocker_token_expiry: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class GuestRead(GuestInDB):
    pass

class GuestList(BaseModel):
    guests: List[GuestRead]
    total: int

class DigiLockerTokenUpdate(BaseModel):
    digilocker_token: Optional[str] = None
    digilocker_refresh_token: Optional[str] = None
    digilocker_token_expiry: Optional[datetime] = None

class GuestResponse(BaseResponse):
    data: GuestInDB

class GuestsResponse(BaseResponse):
    data: List[GuestInDB]
    total: int

# Room schemas
class RoomBase(BaseModel):
    number: int
    room_type: RoomType = RoomType.STANDARD
    rate_per_night: float = 1000.0

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    room_type: Optional[RoomType] = None
    occupied: Optional[bool] = None
    current_guest_id: Optional[int] = None
    rate_per_night: Optional[float] = None

class RoomInDB(RoomBase):
    occupied: bool
    current_guest_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class RoomRead(RoomInDB):
    pass

class RoomList(BaseModel):
    rooms: List[RoomRead]
    total: int

class RoomResponse(BaseResponse):
    data: RoomInDB

class RoomsResponse(BaseResponse):
    data: List[RoomInDB]
    total: int

# Booking schemas
class BookingBase(BaseModel):
    guest_id: int
    room_number: int

class BookingCreate(BookingBase):
    price: Optional[float] = None

class BookingUpdate(BaseModel):
    checkout_at: Optional[datetime] = None
    price: Optional[float] = None

class BookingInDB(BookingBase):
    id: int
    checkin_at: datetime
    checkout_at: Optional[datetime] = None
    price: Optional[float] = None
    invoice_path: Optional[str] = None
    subtotal: Optional[float] = None
    tax_total: Optional[float] = None
    discount_total: Optional[float] = None
    grand_total: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class BookingRead(BookingInDB):
    pass

class BookingList(BaseModel):
    bookings: List[BookingRead]
    total: int

class InvoiceLineItemCreate(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    item_type: str = "service"

class InvoiceTaxCreate(BaseModel):
    name: str
    rate: float

class InvoiceDiscountCreate(BaseModel):
    name: str
    amount: Optional[float] = None
    percentage: Optional[float] = None

class BookingResponse(BaseResponse):
    data: BookingInDB

class BookingsResponse(BaseResponse):
    data: List[BookingInDB]
    total: int

# Invoice schemas
class InvoiceLineItemBase(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    item_type: str = "room"

class InvoiceLineItemCreate(InvoiceLineItemBase):
    booking_id: int

class InvoiceLineItemInDB(InvoiceLineItemBase):
    id: int
    booking_id: int
    amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None

class InvoiceTaxBase(BaseModel):
    name: str
    rate: float

class InvoiceTaxCreate(InvoiceTaxBase):
    booking_id: int

class InvoiceTaxInDB(InvoiceTaxBase):
    id: int
    booking_id: int
    amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None

class InvoiceDiscountBase(BaseModel):
    name: str
    amount: Optional[float] = None
    percentage: Optional[float] = None

class InvoiceDiscountCreate(InvoiceDiscountBase):
    booking_id: int

class InvoiceDiscountInDB(InvoiceDiscountBase):
    id: int
    booking_id: int
    amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None

class InvoiceResponse(BaseResponse):
    booking: BookingInDB
    line_items: List[InvoiceLineItemInDB]
    taxes: List[InvoiceTaxInDB]
    discounts: List[InvoiceDiscountInDB]
    subtotal: float
    tax_total: float
    discount_total: float
    grand_total: float

# OCR schemas
class OCRRequest(BaseModel):
    lang: str = "eng"

class OCRTaskCreate(BaseModel):
    lang: str = "eng"

class OCRResult(BaseModel):
    text: str
    confidence: float
    fields: Dict[str, str]
    raw_data: Dict[str, Any]

class OCRResponse(BaseResponse):
    task_id: str

# Background task schemas
class BackgroundTaskBase(BaseModel):
    task_id: str
    task_type: str
    status: TaskStatus

class BackgroundTaskInDB(BackgroundTaskBase):
    id: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None

class BackgroundTaskRead(BackgroundTaskInDB):
    pass

class BackgroundTaskList(BaseModel):
    tasks: List[BackgroundTaskRead]
    total: int

class BackgroundTaskResponse(BaseResponse):
    data: BackgroundTaskInDB

# Prediction schemas
class PredictionDataPointBase(BaseModel):
    date: datetime
    day_of_week: int
    month: int
    is_holiday: bool = False
    is_weekend: bool = False
    occupancy_rate: float
    avg_stay_duration: Optional[float] = None
    avg_room_rate: Optional[float] = None
    weather_condition: Optional[str] = None
    local_events: Optional[str] = None

class PredictionDataPointInDB(PredictionDataPointBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class PredictionDataPointRead(PredictionDataPointInDB):
    pass

class PredictionResponse(BaseResponse):
    current_occupied: int
    total_rooms: int
    current_occupancy_rate: str
    avg_predicted_occupied: int
    avg_predicted_rate: str
    daily_predictions: List[Dict[str, Any]]

class ModelTrainingResponse(BaseResponse):
    task_id: str

class ModelInfoResponse(BaseResponse):
    algorithm: str
    features: List[str]
    target: str
    metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    training_samples: int
    validation_samples: int
    trained_at: datetime

# DigiLocker schemas
class DigiLockerAuthResponse(BaseResponse):
    auth_url: str

class DigiLockerCallbackResponse(BaseResponse):
    task_id: Optional[str] = None

class DigiLockerDocument(BaseModel):
    name: str
    type: str
    issuer: str
    issue_date: Optional[datetime] = None
    uri: str

class DigiLockerDocumentList(BaseModel):
    documents: List[DigiLockerDocument]
    total: int

class DigiLockerDocumentsResponse(BaseResponse):
    documents: List[DigiLockerDocument]