"""
Схема данных для бронирований
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal


class BookingStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Slot(BaseModel):
    hall_id: str
    start_time: datetime
    end_time: datetime
    available: bool


class BookingCreateRequest(BaseModel):
    hall_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    customer_name: str
    customer_email: str
    customer_phone: str


class BookingResponse(BaseModel):
    booking_id: str
    hall_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    status: BookingStatus
    total_amount: Decimal
    customer_name: str
    customer_email: str
    customer_phone: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class AvailabilityRequest(BaseModel):
    hall_id: Optional[str] = None
    start_date: datetime
    end_date: datetime


class AvailabilityResponse(BaseModel):
    slots: List[Slot]


class BookingCreatedEvent(BaseModel):
    event_type: str = "booking.created"
    booking: BookingResponse
    timestamp: datetime


class BookingConfirmedEvent(BaseModel):
    event_type: str = "booking.confirmed"
    booking_id: str
    timestamp: datetime


class BookingCancelledEvent(BaseModel):
    event_type: str = "booking.cancelled"
    booking_id: str
    reason: Optional[str] = None
    timestamp: datetime

