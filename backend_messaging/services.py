"""
Servicios de la API de mensajería
Centro de Terapias Juan Pablo II
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import secrets
import string
from database import get_db_connection
from models import (
    ContactInquiryCreate, MessageCreate, AdminMessageCreate,
    ContactInquiryResponse, MessageResponse, ConversationResponse,
    InquiryFilters, ConversationUpdate, InquiryUpdate
)

class InquiryService:
    """Servicio para gestionar consultas de contacto"""
    
    @staticmethod
    def generate_inquiry_code() -> str:
        """Generar código único para la consulta"""
        return 'INQ' + ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def create_inquiry(inquiry_data: ContactInquiryCreate, ip_address: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """Crear una nueva consulta de contacto"""
        db = get_db_connection()
        if not db:
            return None
        
        try:
            # Generar código único
            inquiry_code = InquiryService.generate_inquiry_code()
            
            # Verificar que el código sea único
            while True:
                existing = db.execute_query(
                    "SELECT id FROM contact_inquiries WHERE inquiry_code = %s",
                    (inquiry_code,)
                )
                if not existing:
                    break
                inquiry_code = InquiryService.generate_inquiry_code()
            
            # Insertar la consulta
            query = """
                INSERT INTO contact_inquiries 
                (inquiry_code, first_name, last_name, email, phone, subject, message, 
                 service_interest, urgency, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                inquiry_code,
                inquiry_data.first_name,
                inquiry_data.last_name,
                inquiry_data.email,
                inquiry_data.phone,
                inquiry_data.subject,
                inquiry_data.message,
                inquiry_data.service_interest,
                inquiry_data.urgency.value,
                ip_address,
                user_agent
            )
            
            result = db.execute_update(query, params)
            
            if result:
                inquiry_id = db.get_last_insert_id()
                
                # Crear conversación automáticamente
                ConversationService.create_conversation_for_inquiry(inquiry_id, db)
                
                # Obtener la consulta creada
                created_inquiry = InquiryService.get_inquiry_by_id(inquiry_id)
                return created_inquiry
            
            return None
            
        finally:
            db.disconnect()
    
    @staticmethod
    def get_inquiry_by_id(inquiry_id: int) -> Optional[Dict[str, Any]]:
        """Obtener consulta por ID"""
        db = get_db_connection()
        if not db:
            return None
        
        try:
            query = """
                SELECT ci.*, 
                       up.first_name as assigned_first_name,
                       up.last_name as assigned_last_name,
                       u.email as assigned_email,
                       r.name as assigned_role
                FROM contact_inquiries ci
                LEFT JOIN users u ON ci.assigned_to = u.id
                LEFT JOIN user_profiles up ON u.id = up.user_id
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE ci.id = %s
            """
            
            result = db.execute_query(query, (inquiry_id,))
            return result[0] if result else None
            
        finally:
            db.disconnect()
    
    @staticmethod
    def get_inquiries(filters: InquiryFilters) -> Dict[str, Any]:
        """Obtener consultas con filtros y paginación"""
        db = get_db_connection()
        if not db:
            return {"items": [], "total": 0}
        
        try:
            # Construir WHERE clause
            where_conditions = []
            params = []
            
            if filters.status:
                where_conditions.append("ci.status = %s")
                params.append(filters.status.value)
            
            if filters.urgency:
                where_conditions.append("ci.urgency = %s")
                params.append(filters.urgency.value)
            
            if filters.assigned_to:
                where_conditions.append("ci.assigned_to = %s")
                params.append(filters.assigned_to)
            
            if filters.date_from:
                where_conditions.append("ci.created_at >= %s")
                params.append(filters.date_from)
            
            if filters.date_to:
                where_conditions.append("ci.created_at <= %s")
                params.append(filters.date_to)
            
            if filters.search:
                search_condition = """(
                    ci.first_name LIKE %s OR 
                    ci.last_name LIKE %s OR 
                    ci.email LIKE %s OR 
                    ci.subject LIKE %s OR 
                    ci.message LIKE %s
                )"""
                where_conditions.append(search_condition)
                search_term = f"%{filters.search}%"
                params.extend([search_term] * 5)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Contar total
            count_query = f"""
                SELECT COUNT(*) as total
                FROM contact_inquiries ci
                {where_clause}
            """
            
            count_result = db.execute_query(count_query, params)
            total = count_result[0]['total'] if count_result else 0
            
            # Obtener datos paginados
            offset = (filters.page - 1) * filters.per_page
            
            query = f"""
                SELECT ci.*,
                       up.first_name as assigned_first_name,
                       up.last_name as assigned_last_name,
                       u.email as assigned_email,
                       r.name as assigned_role
                FROM contact_inquiries ci
                LEFT JOIN users u ON ci.assigned_to = u.id
                LEFT JOIN user_profiles up ON u.id = up.user_id
                LEFT JOIN roles r ON u.role_id = r.id
                {where_clause}
                ORDER BY ci.created_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([filters.per_page, offset])
            items = db.execute_query(query, params) or []
            
            total_pages = (total + filters.per_page - 1) // filters.per_page
            
            return {
                "items": items,
                "total": total,
                "page": filters.page,
                "per_page": filters.per_page,
                "total_pages": total_pages
            }
            
        finally:
            db.disconnect()
    
    @staticmethod
    def update_inquiry(inquiry_id: int, update_data: InquiryUpdate) -> bool:
        """Actualizar una consulta"""
        db = get_db_connection()
        if not db:
            return False
        
        try:
            # Construir campos a actualizar
            set_fields = []
            params = []
            
            if update_data.status:
                set_fields.append("status = %s")
                params.append(update_data.status.value)
            
            if update_data.assigned_to is not None:
                set_fields.append("assigned_to = %s")
                params.append(update_data.assigned_to)
            
            if update_data.notes is not None:
                set_fields.append("notes = %s")
                params.append(update_data.notes)
            
            if update_data.follow_up_date is not None:
                set_fields.append("follow_up_date = %s")
                params.append(update_data.follow_up_date)
            
            if not set_fields:
                return True  # Nada que actualizar
            
            set_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(inquiry_id)
            
            query = f"""
                UPDATE contact_inquiries 
                SET {', '.join(set_fields)}
                WHERE id = %s
            """
            
            result = db.execute_update(query, params)
            return result is not None and result > 0
            
        finally:
            db.disconnect()

class ConversationService:
    """Servicio para gestionar conversaciones"""
    
    @staticmethod
    def create_conversation_for_inquiry(inquiry_id: int, db=None) -> Optional[int]:
        """Crear conversación para una consulta"""
        should_close_db = False
        if db is None:
            db = get_db_connection()
            should_close_db = True
        
        if not db:
            return None
        
        try:
            query = """
                INSERT INTO conversations (inquiry_id, type, priority, status)
                VALUES (%s, 'inquiry', 'medium', 'open')
            """
            
            result = db.execute_update(query, (inquiry_id,))
            
            if result:
                return db.get_last_insert_id()
            
            return None
            
        finally:
            if should_close_db:
                db.disconnect()
    
    @staticmethod
    def get_conversation_by_inquiry(inquiry_id: int) -> Optional[Dict[str, Any]]:
        """Obtener conversación por ID de consulta"""
        db = get_db_connection()
        if not db:
            return None
        
        try:
            query = """
                SELECT c.*,
                       up.first_name as assigned_first_name,
                       up.last_name as assigned_last_name,
                       u.email as assigned_email
                FROM conversations c
                LEFT JOIN users u ON c.assigned_to = u.id
                LEFT JOIN user_profiles up ON u.id = up.user_id
                WHERE c.inquiry_id = %s
            """
            
            result = db.execute_query(query, (inquiry_id,))
            return result[0] if result else None
            
        finally:
            db.disconnect()
    
    @staticmethod
    def get_conversations(user_id: int = None, status: str = None, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Obtener conversaciones con filtros"""
        db = get_db_connection()
        if not db:
            return {"items": [], "total": 0}
        
        try:
            where_conditions = []
            params = []
            
            if user_id:
                where_conditions.append("(c.assigned_to = %s OR c.assigned_to IS NULL)")
                params.append(user_id)
            
            if status:
                where_conditions.append("c.status = %s")
                params.append(status)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Contar total
            count_query = f"SELECT COUNT(*) as total FROM conversations c {where_clause}"
            count_result = db.execute_query(count_query, params)
            total = count_result[0]['total'] if count_result else 0
            
            # Obtener conversaciones
            offset = (page - 1) * per_page
            
            query = f"""
                SELECT c.*,
                       ci.first_name as inquiry_first_name,
                       ci.last_name as inquiry_last_name,
                       ci.email as inquiry_email,
                       ci.subject as inquiry_subject,
                       up.first_name as assigned_first_name,
                       up.last_name as assigned_last_name,
                       (SELECT COUNT(*) FROM messages m 
                        WHERE m.conversation_id = c.id AND m.is_read = FALSE 
                        AND m.sender_type != 'user') as unread_count
                FROM conversations c
                LEFT JOIN contact_inquiries ci ON c.inquiry_id = ci.id
                LEFT JOIN users u ON c.assigned_to = u.id
                LEFT JOIN user_profiles up ON u.id = up.user_id
                {where_clause}
                ORDER BY c.last_message_at DESC
                LIMIT %s OFFSET %s
            """
            
            params.extend([per_page, offset])
            items = db.execute_query(query, params) or []
            
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            }
            
        finally:
            db.disconnect()

class MessageService:
    """Servicio para gestionar mensajes"""
    
    @staticmethod
    def create_message(message_data: MessageCreate, sender_user_id: int = None) -> Optional[Dict[str, Any]]:
        """Crear un nuevo mensaje"""
        db = get_db_connection()
        if not db:
            return None
        
        try:
            # Determinar tipo de remitente
            if sender_user_id:
                sender_type = "user"
                sender_name = None
                sender_email = None
            else:
                sender_type = "anonymous"
                sender_name = message_data.sender_name
                sender_email = message_data.sender_email
            
            query = """
                INSERT INTO messages 
                (conversation_id, inquiry_id, sender_type, sender_user_id, 
                 sender_name, sender_email, message_text, message_type, is_internal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                message_data.conversation_id,
                message_data.inquiry_id,
                sender_type,
                sender_user_id,
                sender_name,
                sender_email,
                message_data.message_text,
                message_data.message_type.value,
                message_data.is_internal
            )
            
            result = db.execute_update(query, params)
            
            if result:
                message_id = db.get_last_insert_id()
                return MessageService.get_message_by_id(message_id)
            
            return None
            
        finally:
            db.disconnect()
    
    @staticmethod
    def get_message_by_id(message_id: int) -> Optional[Dict[str, Any]]:
        """Obtener mensaje por ID"""
        db = get_db_connection()
        if not db:
            return None
        
        try:
            query = """
                SELECT m.*,
                       up.first_name as sender_first_name,
                       up.last_name as sender_last_name,
                       u.email as sender_email_user,
                       r.name as sender_role
                FROM messages m
                LEFT JOIN users u ON m.sender_user_id = u.id
                LEFT JOIN user_profiles up ON u.id = up.user_id
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE m.id = %s
            """
            
            result = db.execute_query(query, (message_id,))
            return result[0] if result else None
            
        finally:
            db.disconnect()
    
    @staticmethod
    def get_messages_by_conversation(conversation_id: int, page: int = 1, per_page: int = 50) -> List[Dict[str, Any]]:
        """Obtener mensajes de una conversación"""
        db = get_db_connection()
        if not db:
            return []
        
        try:
            offset = (page - 1) * per_page
            
            query = """
                SELECT m.*,
                       up.first_name as sender_first_name,
                       up.last_name as sender_last_name,
                       u.email as sender_email_user,
                       r.name as sender_role
                FROM messages m
                LEFT JOIN users u ON m.sender_user_id = u.id
                LEFT JOIN user_profiles up ON u.id = up.user_id
                LEFT JOIN roles r ON u.role_id = r.id
                WHERE m.conversation_id = %s
                ORDER BY m.created_at ASC
                LIMIT %s OFFSET %s
            """
            
            result = db.execute_query(query, (conversation_id, per_page, offset))
            return result or []
            
        finally:
            db.disconnect()
    
    @staticmethod
    def mark_messages_as_read(conversation_id: int, user_id: int) -> bool:
        """Marcar mensajes como leídos"""
        db = get_db_connection()
        if not db:
            return False
        
        try:
            query = """
                UPDATE messages 
                SET is_read = TRUE, read_at = CURRENT_TIMESTAMP, read_by = %s
                WHERE conversation_id = %s AND is_read = FALSE AND sender_type != 'user'
            """
            
            result = db.execute_update(query, (user_id, conversation_id))
            return result is not None
            
        finally:
            db.disconnect()