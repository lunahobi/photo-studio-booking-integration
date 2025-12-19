"""
Схема данных для платежей
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
from decimal import Decimal


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    YOOKASSA = "yookassa"
    SBERPAY = "sberpay"
    TINKOFF = "tinkoff"


class PaymentType(str, Enum):
    PREPAYMENT = "prepayment"  # Предоплата
    FULL_PAYMENT = "full_payment"  # Полная оплата


class PaymentRequest(BaseModel):
    booking_id: str
    amount: Decimal
    payment_type: PaymentType
    payment_method: PaymentMethod
    return_url: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: str
    booking_id: str
    amount: Decimal
    status: PaymentStatus
    payment_method: PaymentMethod
    payment_url: Optional[str] = None  # URL для редиректа на оплату
    external_payment_id: Optional[str] = None  # ID из платежного шлюза
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaymentWebhook(BaseModel):
    payment_id: str
    external_payment_id: str
    status: PaymentStatus
    amount: Decimal
    gateway: PaymentMethod
    metadata: Optional[dict] = None
    timestamp: datetime


class PaymentSucceededEvent(BaseModel):
    event_type: str = "payment.succeeded"
    payment: PaymentResponse
    booking_id: str
    timestamp: datetime


class PaymentFailedEvent(BaseModel):
    event_type: str = "payment.failed"
    payment_id: str
    booking_id: str
    reason: Optional[str] = None
    timestamp: datetime


class RefundRequest(BaseModel):
    payment_id: str
    amount: Optional[Decimal] = None  # Если None - полный возврат
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    refund_id: str
    payment_id: str
    amount: Decimal
    status: str
    timestamp: datetime

