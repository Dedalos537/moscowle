"""
Service for managing contact inquiries and messages
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import desc

from ..models.contact import ContactInquiry, Message
from ..extensions import db


class ContactService:
    """Service for handling contact inquiries and related operations"""

    @staticmethod
    def generate_inquiry_code():
        """Generate unique inquiry code"""
        return f"INQ-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def create_inquiry(data: dict) -> ContactInquiry:
        """
        Create a new contact inquiry from form submission
        
        Args:
            data: Dictionary containing inquiry data
                - first_name: str (required)
                - last_name: str (required)
                - email: str (required)
                - phone: str (optional)
                - subject: str (optional)
                - message: str (required)
                - service_interest: str (optional)
                - urgency: 'low'|'medium'|'high' (default: 'medium')
        
        Returns:
            ContactInquiry instance
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'message']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Field '{field}' is required")

        try:
            inquiry = ContactInquiry(
                inquiry_code=ContactService.generate_inquiry_code(),
                first_name=data.get('first_name', '').strip(),
                last_name=data.get('last_name', '').strip(),
                email=data.get('email', '').strip(),
                phone=data.get('phone', '').strip() or None,
                subject=data.get('subject', '').strip() or None,
                message=data.get('message', '').strip(),
                service_interest=data.get('service_interest', '').strip() or None,
                urgency=data.get('urgency', 'medium'),
                status='new'
            )
            
            db.session.add(inquiry)
            db.session.commit()
            
            return inquiry
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error creating inquiry: {str(e)}")

    @staticmethod
    def get_inquiry_by_id(inquiry_id: int) -> ContactInquiry:
        """Get a single inquiry by ID"""
        return ContactInquiry.query.get_or_404(inquiry_id)

    @staticmethod
    def get_inquiry_by_code(inquiry_code: str) -> ContactInquiry:
        """Get a single inquiry by code"""
        return ContactInquiry.query.filter_by(inquiry_code=inquiry_code).first_or_404()

    @staticmethod
    def list_inquiries(status: str = None, search: str = None, per_page: int = 50, page: int = 1):
        """
        List inquiries with optional filtering
        
        Args:
            status: Filter by status ('new', 'contacted', 'in_progress', 'resolved', 'closed')
            search: Search in name, email, subject, or message
            per_page: Items per page
            page: Page number
            
        Returns:
            Paginated response with inquiries
        """
        query = ContactInquiry.query

        if status and status != 'all':
            query = query.filter_by(status=status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    ContactInquiry.first_name.ilike(search_term),
                    ContactInquiry.last_name.ilike(search_term),
                    ContactInquiry.email.ilike(search_term),
                    ContactInquiry.subject.ilike(search_term),
                    ContactInquiry.message.ilike(search_term),
                )
            )

        # Sort by newest first
        query = query.order_by(desc(ContactInquiry.created_at))

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            'items': [item.to_dict() for item in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
        }

    @staticmethod
    def update_inquiry_status(inquiry_id: int, status: str) -> ContactInquiry:
        """Update inquiry status"""
        valid_statuses = ['new', 'contacted', 'in_progress', 'resolved', 'closed']
        
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        inquiry = ContactService.get_inquiry_by_id(inquiry_id)
        inquiry.status = status
        inquiry.updated_at = datetime.utcnow()
        
        db.session.commit()
        return inquiry

    @staticmethod
    def get_stats():
        """Get contact inquiry statistics"""
        now = datetime.utcnow()
        twenty_four_hours_ago = now - timedelta(hours=24)

        total = ContactInquiry.query.count()
        new_24h = ContactInquiry.query.filter(
            ContactInquiry.created_at >= twenty_four_hours_ago,
            ContactInquiry.status == 'new'
        ).count()
        pending = ContactInquiry.query.filter(
            ContactInquiry.status.in_(['new', 'contacted', 'in_progress'])
        ).count()

        return {
            'total_inquiries': total,
            'new_inquiries_24h': new_24h,
            'pending_inquiries': pending,
        }


class MessageService:
    """Service for handling messages"""

    @staticmethod
    def create_message(data: dict) -> Message:
        """
        Create a new message
        
        Args:
            data: Dictionary containing message data
                - inquiry_id: int (required)
                - message_text: str (required)
                - sender_type: 'user'|'admin'|'system' (default: 'user')
                - sender_name: str (optional)
                - sender_email: str (optional)
                - is_internal: bool (default: False)
        
        Returns:
            Message instance
        """
        if not data.get('inquiry_id'):
            raise ValueError("inquiry_id is required")
        
        if not data.get('message_text'):
            raise ValueError("message_text is required")

        # Verify inquiry exists
        inquiry = ContactService.get_inquiry_by_id(data.get('inquiry_id'))

        try:
            message = Message(
                inquiry_id=inquiry.id,
                sender_type=data.get('sender_type', 'user'),
                sender_name=data.get('sender_name'),
                sender_email=data.get('sender_email'),
                message_text=data.get('message_text', '').strip(),
                message_type=data.get('message_type', 'text'),
                is_internal=data.get('is_internal', False),
            )
            
            db.session.add(message)
            db.session.commit()
            
            return message
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error creating message: {str(e)}")

    @staticmethod
    def get_messages_by_inquiry(inquiry_id: int, include_internal: bool = False):
        """Get all messages for an inquiry"""
        query = Message.query.filter_by(inquiry_id=inquiry_id)
        
        if not include_internal:
            query = query.filter_by(is_internal=False)
        
        query = query.order_by(Message.created_at.asc())
        return [msg.to_dict() for msg in query.all()]

    @staticmethod
    def mark_message_as_read(message_id: int) -> Message:
        """Mark a message as read"""
        message = Message.query.get_or_404(message_id)
        message.is_read = True
        message.updated_at = datetime.utcnow()
        db.session.commit()
        return message

    @staticmethod
    def mark_inquiry_messages_as_read(inquiry_id: int):
        """Mark all messages in an inquiry as read"""
        Message.query.filter_by(inquiry_id=inquiry_id).update({'is_read': True})
        db.session.commit()

    @staticmethod
    def get_unread_count():
        """Get total unread messages count"""
        return Message.query.filter_by(is_read=False).count()
