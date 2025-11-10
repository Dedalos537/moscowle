"""
API Principal de Mensajería
Centro de Terapias Juan Pablo II
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import os
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import bcrypt
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from database import get_db_connection, test_connection
from models import (
    ContactInquiryCreate, MessageCreate, AdminMessageCreate,
    ContactInquiryResponse, MessageResponse, ConversationResponse,
    InquiryFilters, ConversationUpdate, InquiryUpdate,
    LoginRequest, TokenResponse, UserProfile,
    SuccessResponse, ErrorResponse, PaginatedResponse
)
from services import InquiryService, ConversationService, MessageService

# Configuración
SECRET_KEY = os.getenv("SECRET_KEY", "tu_clave_secreta_super_segura_aqui")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configuración de seguridad
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Crear aplicación FastAPI
app = FastAPI(
    title="API de Mensajería - Centro de Terapias Juan Pablo II",
    description="API para gestión de mensajes y consultas de contacto",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilidades de autenticación
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crear token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """Obtener usuario actual desde token JWT"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener datos del usuario
    db = get_db_connection()
    if not db:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    
    try:
        query = """
            SELECT u.id, u.email, u.status, up.first_name, up.last_name, up.specialty, r.name as role
            FROM users u
            JOIN user_profiles up ON u.id = up.user_id
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = %s AND u.status = 'active'
        """
        result = db.execute_query(query, (user_id,))
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado o inactivo"
            )
        
        user_data = result[0]
        return UserProfile(
            id=user_data['id'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            email=user_data['email'],
            role=user_data['role'],
            specialty=user_data['specialty']
        )
        
    finally:
        db.disconnect()

def get_client_ip(request: Request) -> str:
    """Obtener IP del cliente"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# Endpoints de salud y estado
@app.get("/health")
async def health_check():
    """Verificar estado de la API"""
    db_status = test_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }

# Endpoints de autenticación
@app.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Iniciar sesión"""
    db = get_db_connection()
    if not db:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    
    try:
        # Buscar usuario
        query = """
            SELECT u.id, u.email, u.password_hash, u.status, 
                   up.first_name, up.last_name, up.specialty, r.name as role
            FROM users u
            JOIN user_profiles up ON u.id = up.user_id
            JOIN roles r ON u.role_id = r.id
            WHERE u.email = %s
        """
        result = db.execute_query(query, (login_data.email,))
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )
        
        user_data = result[0]
        
        # Verificar contraseña
        if not verify_password(login_data.password, user_data['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )
        
        # Verificar estado del usuario
        if user_data['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo"
            )
        
        # Crear token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user_data['id'])},
            expires_delta=access_token_expires
        )
        
        # Actualizar último login
        db.execute_update(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
            (user_data['id'],)
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserProfile(
                id=user_data['id'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                email=user_data['email'],
                role=user_data['role'],
                specialty=user_data['specialty']
            )
        )
        
    finally:
        db.disconnect()

# Endpoints públicos (para la web)
@app.post("/public/contact", response_model=SuccessResponse)
async def create_contact_inquiry(
    inquiry_data: ContactInquiryCreate,
    request: Request
):
    """Crear nueva consulta de contacto desde la web (público)"""
    try:
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        created_inquiry = InquiryService.create_inquiry(
            inquiry_data, 
            ip_address=ip_address, 
            user_agent=user_agent
        )
        
        if not created_inquiry:
            raise HTTPException(status_code=500, detail="Error al crear la consulta")
        
        return SuccessResponse(
            message="Consulta enviada exitosamente. En breve nos pondremos en contacto contigo.",
            data={
                "inquiry_code": created_inquiry.get('inquiry_code'),
                "estimated_response_time": "24 horas"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/public/message", response_model=SuccessResponse)
async def send_public_message(message_data: MessageCreate):
    """Enviar mensaje público (respuesta a una consulta existente)"""
    try:
        # Validar que se proporcione inquiry_id o conversation_id
        if not message_data.inquiry_id and not message_data.conversation_id:
            raise HTTPException(
                status_code=400, 
                detail="Se requiere inquiry_id o conversation_id"
            )
        
        # Si solo hay inquiry_id, buscar la conversación
        if message_data.inquiry_id and not message_data.conversation_id:
            conversation = ConversationService.get_conversation_by_inquiry(message_data.inquiry_id)
            if conversation:
                message_data.conversation_id = conversation['id']
        
        created_message = MessageService.create_message(message_data)
        
        if not created_message:
            raise HTTPException(status_code=500, detail="Error al enviar el mensaje")
        
        return SuccessResponse(
            message="Mensaje enviado exitosamente",
            data={"message_id": created_message.get('id')}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Endpoints administrativos (requieren autenticación)
@app.get("/admin/inquiries", response_model=PaginatedResponse)
async def get_inquiries(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: UserProfile = Depends(get_current_user)
):
    """Obtener consultas con filtros (admin)"""
    try:
        filters = InquiryFilters(
            status=status,
            urgency=urgency,
            assigned_to=assigned_to,
            search=search,
            page=page,
            per_page=per_page
        )
        
        result = InquiryService.get_inquiries(filters)
        
        return PaginatedResponse(
            items=result['items'],
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            total_pages=result['total_pages']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/admin/inquiries/{inquiry_id}")
async def get_inquiry_detail(
    inquiry_id: int,
    current_user: UserProfile = Depends(get_current_user)
):
    """Obtener detalle de una consulta específica"""
    try:
        inquiry = InquiryService.get_inquiry_by_id(inquiry_id)
        if not inquiry:
            raise HTTPException(status_code=404, detail="Consulta no encontrada")
        
        # Obtener conversación asociada
        conversation = ConversationService.get_conversation_by_inquiry(inquiry_id)
        
        # Obtener mensajes si hay conversación
        messages = []
        if conversation:
            messages = MessageService.get_messages_by_conversation(conversation['id'])
        
        return {
            "inquiry": inquiry,
            "conversation": conversation,
            "messages": messages
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.put("/admin/inquiries/{inquiry_id}", response_model=SuccessResponse)
async def update_inquiry(
    inquiry_id: int,
    update_data: InquiryUpdate,
    current_user: UserProfile = Depends(get_current_user)
):
    """Actualizar una consulta"""
    try:
        success = InquiryService.update_inquiry(inquiry_id, update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Consulta no encontrada")
        
        return SuccessResponse(message="Consulta actualizada exitosamente")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/admin/conversations")
async def get_conversations(
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: UserProfile = Depends(get_current_user)
):
    """Obtener conversaciones para el dashboard administrativo"""
    try:
        result = ConversationService.get_conversations(
            user_id=current_user.id,
            status=status,
            page=page,
            per_page=per_page
        )
        
        return PaginatedResponse(
            items=result['items'],
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            total_pages=result['total_pages']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/admin/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    page: int = 1,
    per_page: int = 50,
    current_user: UserProfile = Depends(get_current_user)
):
    """Obtener mensajes de una conversación"""
    try:
        messages = MessageService.get_messages_by_conversation(
            conversation_id, page, per_page
        )
        
        # Marcar mensajes como leídos
        MessageService.mark_messages_as_read(conversation_id, current_user.id)
        
        return {"messages": messages}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/admin/messages", response_model=SuccessResponse)
async def send_admin_message(
    message_data: AdminMessageCreate,
    current_user: UserProfile = Depends(get_current_user)
):
    """Enviar mensaje desde el panel administrativo"""
    try:
        # Convertir a MessageCreate
        full_message_data = MessageCreate(
            conversation_id=message_data.conversation_id,
            message_text=message_data.message_text,
            is_internal=message_data.is_internal
        )
        
        created_message = MessageService.create_message(
            full_message_data, 
            sender_user_id=current_user.id
        )
        
        if not created_message:
            raise HTTPException(status_code=500, detail="Error al enviar el mensaje")
        
        return SuccessResponse(
            message="Mensaje enviado exitosamente",
            data={"message_id": created_message.get('id')}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/admin/stats")
async def get_admin_stats(current_user: UserProfile = Depends(get_current_user)):
    """Obtener estadísticas para el dashboard"""
    db = get_db_connection()
    if not db:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    
    try:
        # Estadísticas básicas
        stats = {}
        
        # Total de consultas
        result = db.execute_query("SELECT COUNT(*) as total FROM contact_inquiries")
        stats['total_inquiries'] = result[0]['total'] if result else 0
        
        # Consultas nuevas (últimas 24h)
        result = db.execute_query(
            "SELECT COUNT(*) as total FROM contact_inquiries WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        )
        stats['new_inquiries_24h'] = result[0]['total'] if result else 0
        
        # Consultas pendientes
        result = db.execute_query(
            "SELECT COUNT(*) as total FROM contact_inquiries WHERE status IN ('new', 'contacted')"
        )
        stats['pending_inquiries'] = result[0]['total'] if result else 0
        
        # Conversaciones activas
        result = db.execute_query(
            "SELECT COUNT(*) as total FROM conversations WHERE status = 'open'"
        )
        stats['active_conversations'] = result[0]['total'] if result else 0
        
        # Mensajes no leídos
        result = db.execute_query(
            "SELECT COUNT(*) as total FROM messages WHERE is_read = FALSE AND sender_type = 'anonymous'"
        )
        stats['unread_messages'] = result[0]['total'] if result else 0
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    
    finally:
        db.disconnect()

# Endpoint de prueba
@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "API de Mensajería - Centro de Terapias Juan Pablo II",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Obtener configuración del .env
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    
    print("🚀 Iniciando API de Mensajería...")
    print(f"📋 Documentación disponible en: http://localhost:{port}/docs")
    print("🏥 Centro de Terapias Juan Pablo II")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False
    )