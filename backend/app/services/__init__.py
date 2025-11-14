"""
Servicios básicos del sistema
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import secrets
import string
from passlib.context import CryptContext
import jwt

from app.database.connection import get_db_session
from app.models import (
    ContactInquiryCreate, MessageCreate, UserLogin, 
    ContactInquiryResponse, MessageResponse, UserResponse,
    InquiryStatus, SenderType
)
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("services")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class InquiryService:
    """Servicio para gestionar consultas de contacto"""
    
    @staticmethod
    def generate_inquiry_code() -> str:
        """Generar código único de 6 dígitos"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def create_inquiry(inquiry_data: ContactInquiryCreate, ip_address: str = None) -> Optional[ContactInquiryResponse]:
        """Crear nueva consulta de contacto"""
        try:
            with get_db_session() as db:
                # Generar código único
                inquiry_code = InquiryService.generate_inquiry_code()
                
                # Verificar que sea único
                while True:
                    check_query = "SELECT COUNT(*) as count FROM contact_inquiries WHERE inquiry_code = %s"
                    result = db.execute_query(check_query, (inquiry_code,))
                    if result[0]['count'] == 0:
                        break
                    inquiry_code = InquiryService.generate_inquiry_code()
                
                # Insertar consulta
                query = """
                    INSERT INTO contact_inquiries 
                    (name, email, phone, message, inquiry_code, ip_address, 
                     service_type, preferred_contact_method, urgency_level, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                params = (
                    inquiry_data.name,
                    inquiry_data.email,
                    inquiry_data.phone,
                    inquiry_data.message,
                    inquiry_code,
                    ip_address,
                    inquiry_data.service_type,
                    inquiry_data.preferred_contact_method,
                    inquiry_data.urgency_level,
                    InquiryStatus.NEW.value
                )
                
                db.begin_transaction()
                result = db.execute_update(query, params)
                
                if result > 0:
                    inquiry_id = db.get_last_insert_id()
                    db.commit()
                    
                    logger.info(f"New inquiry created: {inquiry_code}")
                    return InquiryService.get_inquiry_by_id(inquiry_id)
                
                db.rollback()
                return None
                
        except Exception as e:
            logger.error(f"Error creating inquiry: {e}")
            return None
    
    @staticmethod
    def get_inquiry_by_id(inquiry_id: int) -> Optional[ContactInquiryResponse]:
        """Obtener consulta por ID"""
        try:
            with get_db_session() as db:
                query = """
                    SELECT ci.*, 
                           u.username as assigned_therapist_username,
                           up.first_name as therapist_first_name,
                           up.last_name as therapist_last_name
                    FROM contact_inquiries ci
                    LEFT JOIN users u ON ci.assigned_therapist_id = u.id
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE ci.id = %s
                """
                
                result = db.execute_query(query, (inquiry_id,))
                
                if result:
                    row = result[0]
                    return ContactInquiryResponse(
                        id=row['id'],
                        name=row['name'],
                        email=row['email'],
                        phone=row['phone'],
                        message=row['message'],
                        inquiry_code=row['inquiry_code'],
                        status=row['status'],
                        service_type=row['service_type'],
                        preferred_contact_method=row['preferred_contact_method'],
                        urgency_level=row['urgency_level'],
                        assigned_therapist_id=row['assigned_therapist_id'],
                        assigned_therapist_name=(
                            f"{row['therapist_first_name']} {row['therapist_last_name']}" 
                            if row['therapist_first_name'] else None
                        ),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting inquiry by ID: {e}")
            return None
    
    @staticmethod
    def get_inquiry_by_code(inquiry_code: str) -> Optional[ContactInquiryResponse]:
        """Obtener consulta por código"""
        try:
            with get_db_session() as db:
                query = """
                    SELECT ci.*, 
                           u.username as assigned_therapist_username,
                           up.first_name as therapist_first_name,
                           up.last_name as therapist_last_name
                    FROM contact_inquiries ci
                    LEFT JOIN users u ON ci.assigned_therapist_id = u.id
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE ci.inquiry_code = %s
                """
                
                result = db.execute_query(query, (inquiry_code,))
                
                if result:
                    row = result[0]
                    return ContactInquiryResponse(
                        id=row['id'],
                        name=row['name'],
                        email=row['email'],
                        phone=row['phone'],
                        message=row['message'],
                        inquiry_code=row['inquiry_code'],
                        status=row['status'],
                        service_type=row['service_type'],
                        preferred_contact_method=row['preferred_contact_method'],
                        urgency_level=row['urgency_level'],
                        assigned_therapist_id=row['assigned_therapist_id'],
                        assigned_therapist_name=(
                            f"{row['therapist_first_name']} {row['therapist_last_name']}" 
                            if row['therapist_first_name'] else None
                        ),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting inquiry by code: {e}")
            return None


class MessageService:
    """Servicio para gestionar mensajes"""
    
    @staticmethod
    def create_message(message_data: MessageCreate) -> Optional[MessageResponse]:
        """Crear nuevo mensaje"""
        try:
            with get_db_session() as db:
                query = """
                    INSERT INTO messages 
                    (conversation_id, sender_type, sender_id, content, 
                     message_type, attachments, is_read, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                params = (
                    message_data.conversation_id,
                    message_data.sender_type.value,
                    message_data.sender_id,
                    message_data.content,
                    message_data.message_type.value,
                    message_data.attachments,
                    message_data.is_read,
                    message_data.metadata
                )
                
                db.begin_transaction()
                result = db.execute_update(query, params)
                
                if result > 0:
                    message_id = db.get_last_insert_id()
                    db.commit()
                    
                    logger.info(f"New message created: {message_id}")
                    return MessageService.get_message_by_id(message_id)
                
                db.rollback()
                return None
                
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None
    
    @staticmethod
    def get_message_by_id(message_id: int) -> Optional[MessageResponse]:
        """Obtener mensaje por ID"""
        try:
            with get_db_session() as db:
                query = """
                    SELECT m.*, 
                           u.username as sender_username,
                           up.first_name as sender_first_name,
                           up.last_name as sender_last_name
                    FROM messages m
                    LEFT JOIN users u ON m.sender_id = u.id AND m.sender_type IN ('therapist', 'admin')
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE m.id = %s
                """
                
                result = db.execute_query(query, (message_id,))
                
                if result:
                    row = result[0]
                    return MessageResponse(
                        id=row['id'],
                        conversation_id=row['conversation_id'],
                        sender_type=row['sender_type'],
                        sender_id=row['sender_id'],
                        sender_name=(
                            f"{row['sender_first_name']} {row['sender_last_name']}" 
                            if row['sender_first_name'] and row['sender_type'] in ['therapist', 'admin']
                            else "Cliente"
                        ),
                        content=row['content'],
                        message_type=row['message_type'],
                        attachments=row['attachments'],
                        is_read=row['is_read'],
                        metadata=row['metadata'],
                        created_at=row['created_at']
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None


class AuthService:
    """Servicio de autenticación"""
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[UserResponse]:
        """Autenticar usuario"""
        try:
            with get_db_session() as db:
                query = """
                    SELECT u.*, up.first_name, up.last_name
                    FROM users u
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE u.username = %s AND u.is_active = TRUE
                """
                
                result = db.execute_query(query, (username,))
                
                if result and pwd_context.verify(password, result[0]['password_hash']):
                    row = result[0]
                    
                    # Actualizar último login
                    update_query = "UPDATE users SET last_login = %s WHERE id = %s"
                    db.execute_update(update_query, (datetime.utcnow(), row['id']))
                    
                    return UserResponse(
                        id=row['id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        is_active=row['is_active'],
                        created_at=row['created_at'],
                        last_login=datetime.utcnow()
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None
    
    @staticmethod
    def create_access_token(user_id: int) -> str:
        """Crear token JWT"""
        try:
            from datetime import timedelta
            
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
            to_encode = {
                "sub": str(user_id),
                "exp": expire,
                "type": "access"
            }
            
            return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
            
        except Exception as e:
            logger.error(f"Error creating token: {e}")
            return None
    
    @staticmethod
    def verify_token(token: str) -> Optional[int]:
        """Verificar token JWT"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            return int(user_id) if user_id else None
            
        except (jwt.PyJWTError, ValueError):
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[UserResponse]:
        """Obtener usuario por ID"""
        try:
            with get_db_session() as db:
                query = """
                    SELECT u.*, up.first_name, up.last_name
                    FROM users u
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE u.id = %s
                """
                
                result = db.execute_query(query, (user_id,))
                
                if result:
                    row = result[0]
                    return UserResponse(
                        id=row['id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        is_active=row['is_active'],
                        created_at=row['created_at'],
                        last_login=row['last_login']
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None