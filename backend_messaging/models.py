"""
Modelos Pydantic para la API de mensajería
Centro de Terapias Juan Pablo II
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

# Enums para valores predefinidos
class InquiryStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class InquiryUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MessageType(str, Enum):
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    SYSTEM = "system"

class SenderType(str, Enum):
    USER = "user"
    ANONYMOUS = "anonymous"
    SYSTEM = "system"

class ConversationStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"

# Modelos para requests (entrada)
class ContactInquiryCreate(BaseModel):
    """Modelo para crear una nueva consulta de contacto desde la web"""
    first_name: str = Field(..., min_length=2, max_length=100, description="Nombre del remitente")
    last_name: str = Field(..., min_length=2, max_length=100, description="Apellido del remitente")
    email: EmailStr = Field(..., description="Email de contacto")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono de contacto")
    subject: Optional[str] = Field(None, max_length=200, description="Asunto del mensaje")
    message: str = Field(..., min_length=10, max_length=2000, description="Mensaje del usuario")
    service_interest: Optional[str] = Field(None, max_length=200, description="Servicio de interés")
    urgency: InquiryUrgency = Field(InquiryUrgency.MEDIUM, description="Nivel de urgencia")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise ValueError('Formato de teléfono inválido')
        return v

class MessageCreate(BaseModel):
    """Modelo para crear un nuevo mensaje"""
    conversation_id: Optional[int] = Field(None, description="ID de conversación existente")
    inquiry_id: Optional[int] = Field(None, description="ID de consulta (para primer mensaje)")
    message_text: str = Field(..., min_length=1, max_length=2000, description="Texto del mensaje")
    message_type: MessageType = Field(MessageType.TEXT, description="Tipo de mensaje")
    is_internal: bool = Field(False, description="Mensaje interno del staff")
    
    # Para mensajes anónimos (respuestas desde la web)
    sender_name: Optional[str] = Field(None, max_length=200, description="Nombre del remitente anónimo")
    sender_email: Optional[EmailStr] = Field(None, description="Email del remitente anónimo")

class AdminMessageCreate(BaseModel):
    """Modelo para mensajes desde el panel administrativo"""
    conversation_id: int = Field(..., description="ID de la conversación")
    message_text: str = Field(..., min_length=1, max_length=2000, description="Texto del mensaje")
    is_internal: bool = Field(False, description="Mensaje interno del staff")

class ConversationUpdate(BaseModel):
    """Modelo para actualizar una conversación"""
    status: Optional[ConversationStatus] = Field(None, description="Estado de la conversación")
    assigned_to: Optional[int] = Field(None, description="Usuario asignado")
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = Field(None, description="Prioridad")

class InquiryUpdate(BaseModel):
    """Modelo para actualizar una consulta"""
    status: Optional[InquiryStatus] = Field(None, description="Estado de la consulta")
    assigned_to: Optional[int] = Field(None, description="Usuario asignado")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas internas")
    follow_up_date: Optional[datetime] = Field(None, description="Fecha de seguimiento")

# Modelos para responses (salida)
class UserProfile(BaseModel):
    """Perfil básico de usuario"""
    id: int
    first_name: str
    last_name: str
    email: str
    role: str
    specialty: Optional[str] = None

class ContactInquiryResponse(BaseModel):
    """Respuesta con datos de consulta de contacto"""
    id: int
    inquiry_code: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    subject: Optional[str]
    message: str
    service_interest: Optional[str]
    urgency: str
    status: str
    assigned_to: Optional[UserProfile] = None
    notes: Optional[str]
    source: str
    created_at: datetime
    updated_at: datetime

class MessageResponse(BaseModel):
    """Respuesta con datos de mensaje"""
    id: int
    conversation_id: Optional[int]
    inquiry_id: Optional[int]
    sender_type: str
    sender_user: Optional[UserProfile] = None
    sender_name: Optional[str]
    sender_email: Optional[str]
    message_text: str
    message_type: str
    is_read: bool
    is_internal: bool
    created_at: datetime

class ConversationResponse(BaseModel):
    """Respuesta con datos de conversación"""
    id: int
    inquiry_id: Optional[int]
    title: Optional[str]
    type: str
    priority: str
    status: str
    assigned_to: Optional[UserProfile] = None
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    unread_count: int = 0
    messages: List[MessageResponse] = []

class InquiryWithConversation(BaseModel):
    """Consulta con su conversación asociada"""
    inquiry: ContactInquiryResponse
    conversation: Optional[ConversationResponse] = None

# Modelos para autenticación
class LoginRequest(BaseModel):
    """Solicitud de login"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Respuesta de autenticación"""
    access_token: str
    token_type: str
    user: UserProfile

# Modelos para respuestas generales
class SuccessResponse(BaseModel):
    """Respuesta de éxito general"""
    success: bool = True
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    """Respuesta de error"""
    success: bool = False
    error: str
    details: Optional[str] = None

class PaginatedResponse(BaseModel):
    """Respuesta paginada"""
    items: List[dict]
    total: int
    page: int
    per_page: int
    total_pages: int

# Validaciones adicionales
class InquiryFilters(BaseModel):
    """Filtros para buscar consultas"""
    status: Optional[InquiryStatus] = None
    urgency: Optional[InquiryUrgency] = None
    assigned_to: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    page: int = Field(1, ge=1, description="Número de página")
    per_page: int = Field(20, ge=1, le=100, description="Elementos por página")