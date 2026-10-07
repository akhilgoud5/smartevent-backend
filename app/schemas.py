from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field

class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class EventCreate(BaseModel):
    title: str
    description: str | None = None
    category: str
    location: str
    event_date: datetime
    ticket_price: float = Field(ge=0)
    banner_image: str | None = None
    total_tickets: int = Field(default=100, ge=1)

class EventOut(EventCreate):
    id: int
    available_tickets: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BookingCreate(BaseModel):
    event_id: int
    ticket_quantity: int = Field(gt=0, le=20)

class BookingOut(BaseModel):
    id: int
    event_id: int
    ticket_quantity: int
    total_price: float
    booking_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TicketOut(BaseModel):
    id: int
    booking_id: int
    ticket_code: str
    qr_code_url: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
