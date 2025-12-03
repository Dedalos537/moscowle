"""
Routes for contact inquiries and messages
Includes:
- POST /api/public/contact - Submit contact form (public endpoint)
- GET /api/admin/inquiries - Get list of inquiries (admin)
- GET /api/admin/inquiries/<id> - Get specific inquiry (admin)
- PUT /api/admin/inquiries/<id> - Update inquiry (admin)
- POST /api/admin/messages - Create message (admin)
- GET /api/admin/messages/<inquiry_id> - Get messages (admin)
- GET /api/admin/stats - Get contact stats (admin)
"""

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from ..services.contact_service import ContactService, MessageService
from ..schemas.contact_schema import (
    ContactInquirySchema,
    ContactInquiryUpdateSchema,
    MessageSchema,
    MessageCreateSchema,
)
from ..extensions import jwt_required

contact_bp = Blueprint('contact', __name__)


# ============================================================================
# PUBLIC ENDPOINTS (No authentication required)
# ============================================================================

@contact_bp.route('/public/contact', methods=['POST'])
def submit_contact_form():
    """
    Submit a contact form
    
    Request body:
    {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+51 921 507 470",
        "subject": "Inquiry about services",
        "message": "I would like more information...",
        "service_interest": "Terapia de Lenguaje",
        "urgency": "medium"
    }
    """
    try:
        # Validate request data
        schema = ContactInquirySchema()
        data = schema.load(request.get_json())
        
        # Create inquiry
        inquiry = ContactService.create_inquiry(data)
        
        return jsonify({
            'success': True,
            'message': 'Inquiry submitted successfully',
            'inquiry_code': inquiry.inquiry_code,
            'data': inquiry.to_dict()
        }), 201
        
    except ValidationError as err:
        return jsonify({
            'success': False,
            'message': 'Validation error',
            'errors': err.messages
        }), 400
        
    except ValueError as err:
        return jsonify({
            'success': False,
            'message': str(err)
        }), 400
        
    except Exception as err:
        return jsonify({
            'success': False,
            'message': 'Error submitting inquiry',
            'error': str(err)
        }), 500


# ============================================================================
# ADMIN ENDPOINTS (Authentication required)
# ============================================================================

@contact_bp.route('/admin/inquiries', methods=['GET'])
@jwt_required()
def get_inquiries():
    """
    Get list of contact inquiries
    
    Query parameters:
    - status: Filter by status (new, contacted, in_progress, resolved, closed)
    - search: Search term
    - per_page: Items per page (default: 50)
    - page: Page number (default: 1)
    """
    try:
        status = request.args.get('status')
        search = request.args.get('search')
        per_page = request.args.get('per_page', 50, type=int)
        page = request.args.get('page', 1, type=int)
        
        result = ContactService.list_inquiries(
            status=status,
            search=search,
            per_page=per_page,
            page=page
        )
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as err:
        return jsonify({
            'success': False,
            'message': 'Error fetching inquiries',
            'error': str(err)
        }), 500


@contact_bp.route('/admin/inquiries/<int:inquiry_id>', methods=['GET'])
@jwt_required()
def get_inquiry(inquiry_id):
    """Get a specific inquiry"""
    try:
        inquiry = ContactService.get_inquiry_by_id(inquiry_id)
        
        # Mark messages as read
        MessageService.mark_inquiry_messages_as_read(inquiry_id)
        
        # Get messages
        messages = MessageService.get_messages_by_inquiry(inquiry_id)
        
        return jsonify({
            'success': True,
            'data': {
                'inquiry': inquiry.to_dict(),
                'messages': messages
            }
        }), 200
        
    except Exception as err:
        return jsonify({
            'success': False,
            'message': 'Error fetching inquiry',
            'error': str(err)
        }), 500


@contact_bp.route('/admin/inquiries/<int:inquiry_id>', methods=['PUT'])
@jwt_required()
def update_inquiry(inquiry_id):
    """Update inquiry status"""
    try:
        schema = ContactInquiryUpdateSchema()
        data = schema.load(request.get_json())
        
        inquiry = ContactService.update_inquiry_status(inquiry_id, data['status'])
        
        return jsonify({
            'success': True,
            'message': 'Inquiry updated successfully',
            'data': inquiry.to_dict()
        }), 200
        
    except ValidationError as err:
        return jsonify({
            'success': False,
            'message': 'Validation error',
            'errors': err.messages
        }), 400
        
    except ValueError as err:
        return jsonify({
            'success': False,
            'message': str(err)
        }), 400
        
    except Exception as err:
        return jsonify({
            'success': False,
            'message': 'Error updating inquiry',
            'error': str(err)
        }), 500


@contact_bp.route('/admin/messages', methods=['POST'])
@jwt_required()
def create_message():
    """Create a message in response to an inquiry"""
    try:
        schema = MessageCreateSchema()
        data = schema.load(request.get_json())
        
        message = MessageService.create_message(data)
        
        # Update inquiry status to 'contacted'
        inquiry = ContactService.get_inquiry_by_id(data['inquiry_id'])
        if inquiry.status == 'new':
            ContactService.update_inquiry_status(data['inquiry_id'], 'contacted')
        
        return jsonify({
            'success': True,
            'message': 'Message created successfully',
            'data': message.to_dict()
        }), 201
        
    except ValidationError as err:
        return jsonify({
            'success': False,
            'message': 'Validation error',
            'errors': err.messages
        }), 400
        
    except Exception as err:
        return jsonify({
            'success': False,
            'message': 'Error creating message',
            'error': str(err)
        }), 500


@contact_bp.route('/admin/messages/<int:inquiry_id>', methods=['GET'])
@jwt_required()
def get_messages(inquiry_id):
    """Get all messages for an inquiry"""
    try:
        # Verify inquiry exists
        ContactService.get_inquiry_by_id(inquiry_id)
        
        messages = MessageService.get_messages_by_inquiry(inquiry_id)
        
        return jsonify({
            'success': True,
            'data': messages
        }), 200
        
    except Exception as err:
        return jsonify({
            'success': False,
            'message': 'Error fetching messages',
            'error': str(err)
        }), 500


@contact_bp.route('/admin/stats', methods=['GET'])
@jwt_required()
def get_contact_stats():
    """Get contact inquiry statistics"""
    try:
        stats = ContactService.get_stats()
        unread = MessageService.get_unread_count()
        
        return jsonify({
            'success': True,
            'data': {
                **stats,
                'unread_messages': unread
            }
        }), 200
        
    except Exception as err:
        return jsonify({
            'success': False,
            'message': 'Error fetching stats',
            'error': str(err)
        }), 500
