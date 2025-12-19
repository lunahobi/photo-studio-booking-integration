"""
Схемы для интеграционного сервиса
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    EVENT = "event"
    REQUEST = "request"
    RESPONSE = "response"


class IntegrationMessage(BaseModel):
    message_id: str
    message_type: MessageType
    source_service: str
    target_service: Optional[str] = None
    event_type: Optional[str] = None
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    retry_count: int = 0


class EventLog(BaseModel):
    event_id: str
    event_type: str
    source_service: str
    payload: Dict[str, Any]
    status: str  # processed, failed, pending
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    timestamp: datetime


class SyncRequest(BaseModel):
    entity_type: str  # booking, payment, etc.
    entity_id: str
    action: str  # create, update, delete
    timestamp: datetime
