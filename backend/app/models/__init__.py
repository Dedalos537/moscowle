"""
Modelos básicos del sistema
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums básicos
class InquiryStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MessageType(str, Enum):
    TEXT = "text"
    FILE = "file" 
    IMAGE = "image"
    SYSTEM = "system"


class SenderType(str, Enum):
    CLIENT = "client"
    THERAPIST = "therapist"
    ADMIN = "admin"
    SYSTEM = "system"


class UserRole(str, Enum):
    ADMIN = "admin"
    THERAPIST = "therapist"


# Modelos de entrada (requests)
class ContactInquiryCreate(BaseModel):
    """Crear nueva consulta de contacto"""
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    message: str = Field(..., min_length=10, max_length=2000)
    service_type: Optional[str] = Field(None, max_length=100)
    preferred_contact_method: Optional[str] = Field("email", max_length=50)
    urgency_level: Optional[str] = Field("medium", max_length=20)


class MessageCreate(BaseModel):
    """Crear nuevo mensaje"""
    conversation_id: int
    sender_type: SenderType
    sender_id: Optional[int] = None
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: MessageType = MessageType.TEXT
    attachments: Optional[str] = None
    is_read: bool = False
    metadata: Optional[str] = None


class UserLogin(BaseModel):
    """Login de usuario"""
    username: str
    password: str


# Modelos de respuesta
class ContactInquiryResponse(BaseModel):
    """Respuesta de consulta de contacto"""
    id: int
    name: str
    email: str
    phone: Optional[str]
    message: str
    inquiry_code: str
    status: str
    service_type: Optional[str]
    preferred_contact_method: Optional[str]
    urgency_level: Optional[str]
    assigned_therapist_id: Optional[int]
    assigned_therapist_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class MessageResponse(BaseModel):
    """Respuesta de mensaje"""
    id: int
    conversation_id: int
    sender_type: str
    sender_id: Optional[int]
    sender_name: Optional[str]
    content: str
    message_type: str
    attachments: Optional[str]
    is_read: bool
    metadata: Optional[str]
    created_at: datetime


class UserResponse(BaseModel):
    """Respuesta de usuario"""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class TokenResponse(BaseModel):
    """Respuesta de token de acceso"""
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse


# Modelos de filtros
class InquiryFilters(BaseModel):
    """Filtros para consultas"""
    status: Optional[InquiryStatus] = None
    service_type: Optional[str] = None
    urgency_level: Optional[str] = None
    assigned_therapist_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    per_page: int = 20


# Modelos genéricos
class SuccessResponse(BaseModel):
    """Respuesta exitosa genérica"""
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Respuesta de error"""
    error: str
    detail: Optional[str] = None