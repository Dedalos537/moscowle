"""
Contact Inquiry and Message models for handling user inquiries and communication
"""

from datetime import datetime
from ..extensions import db


class ContactInquiry(db.Model):
    """Model for storing contact form submissions from public website"""
    
    __tablename__ = 'contact_inquiries'

    id = db.Column(db.Integer, primary_key=True)
    inquiry_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Contact information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(20))
    
    # Inquiry details
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    service_interest = db.Column(db.String(100))
    
    # Metadata
    urgency = db.Column(
        db.Enum('low', 'medium', 'high', name='inquiry_urgency'),
        default='medium',
        nullable=False
    )
    status = db.Column(
        db.Enum('new', 'contacted', 'in_progress', 'resolved', 'closed', name='inquiry_status'),
        default='new',
        nullable=False,
        index=True
    )
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    messages = db.relationship('Message', backref='inquiry', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ContactInquiry {self.inquiry_code} - {self.email}>'

    def to_dict(self):
        return {
            'id': self.id,
            'inquiry_code': self.inquiry_code,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'subject': self.subject,
            'message': self.message,
            'service_interest': self.service_interest,
            'urgency': self.urgency,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Message(db.Model):
    """Model for storing messages in conversations"""
    
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, index=True)
    
    # Foreign key to inquiry
    inquiry_id = db.Column(db.Integer, db.ForeignKey('contact_inquiries.id', ondelete='CASCADE'), index=True)
    
    # Sender information
    sender_type = db.Column(
        db.Enum('user', 'anonymous', 'system', 'admin', name='sender_type'),
        default='user',
        nullable=False
    )
    sender_name = db.Column(db.String(100))
    sender_email = db.Column(db.String(255))
    
    # Message content
    message_text = db.Column(db.Text, nullable=False)
    message_type = db.Column(
        db.Enum('text', 'file', 'image', 'system', name='message_type'),
        default='text',
        nullable=False
    )
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    is_internal = db.Column(db.Boolean, default=False)  # True if only visible to admins
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.id} - {self.sender_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'inquiry_id': self.inquiry_id,
            'sender_type': self.sender_type,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'message_text': self.message_text,
            'message_type': self.message_type,
            'is_read': self.is_read,
            'is_internal': self.is_internal,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
