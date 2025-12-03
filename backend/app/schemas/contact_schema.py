"""
Schemas for contact inquiries and messages validation
"""

from marshmallow import Schema, fields, validate, ValidationError


class ContactInquirySchema(Schema):
    """Schema for validating contact inquiry submissions"""
    
    id = fields.Int(dump_only=True)
    inquiry_code = fields.Str(dump_only=True)
    
    first_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    
    subject = fields.Str(allow_none=True, validate=validate.Length(max=200))
    message = fields.Str(required=True, validate=validate.Length(min=10))
    service_interest = fields.Str(allow_none=True, validate=validate.Length(max=100))
    
    urgency = fields.Str(
        validate=validate.OneOf(['low', 'medium', 'high']),
        load_default='medium'
    )
    status = fields.Str(dump_only=True)
    
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ContactInquiryUpdateSchema(Schema):
    """Schema for updating contact inquiry status"""
    
    status = fields.Str(
        required=True,
        validate=validate.OneOf(['new', 'contacted', 'in_progress', 'resolved', 'closed'])
    )


class MessageSchema(Schema):
    """Schema for validating messages"""
    
    id = fields.Int(dump_only=True)
    conversation_id = fields.Int(allow_none=True)
    inquiry_id = fields.Int(required=True)
    
    sender_type = fields.Str(
        validate=validate.OneOf(['user', 'anonymous', 'system', 'admin']),
        load_default='user'
    )
    sender_name = fields.Str(allow_none=True, validate=validate.Length(max=100))
    sender_email = fields.Email(allow_none=True)
    
    message_text = fields.Str(required=True, validate=validate.Length(min=1))
    message_type = fields.Str(
        validate=validate.OneOf(['text', 'file', 'image', 'system']),
        load_default='text'
    )
    
    is_read = fields.Bool(dump_only=True)
    is_internal = fields.Bool(load_default=False)
    
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class MessageCreateSchema(Schema):
    """Schema for creating messages"""
    
    inquiry_id = fields.Int(required=True)
    message_text = fields.Str(required=True, validate=validate.Length(min=1))
    sender_type = fields.Str(
        validate=validate.OneOf(['user', 'anonymous', 'system', 'admin']),
        load_default='user'
    )
    sender_name = fields.Str(allow_none=True)
    sender_email = fields.Email(allow_none=True)
    is_internal = fields.Bool(load_default=False)
