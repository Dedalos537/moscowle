from app.routes.api._shared import (
    db, User, Notification, Appointment, Message, Game, SessionMetrics,
    SessionImage, ContactMessage, Sede, Payment, json, os, time, warnings,
    genai, Groq, _ollama_client, predict_level, start_async_training,
    get_user_today_utc_range, get_user_now, localize_datetime_for_display,
    get_user_timezone, bcrypt, limiter, csrf, EmailService, api_response,
    AvailabilityService, requests, or_, func,
    notification_service,
    LIMA_TZ, _parse_json, _parse_datetime, analyze_contact_message_ai,
    AssignTherapistSchema, UpdateUserSchema, SendMessageSchema,
    uuid, secure_filename, datetime, timedelta, timezone,
)
from app.routes.api import api_bp
@api_bp.route('/notifications')
@login_required
def get_notifications():
    notifications = notification_service.get_unread_notifications(current_user.id)
    result = [{
        'id': n.id,
        'title': n.title,
        'type': n.type or 'info',
        'message': n.message,
        'timestamp': n.timestamp.strftime('%d %b, %H:%M'),
        'link': n.link
    } for n in notifications]
    return jsonify(result)

@api_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
@csrf.exempt
def mark_notifications_read():
    try:
        data = request.get_json() or {}
        notif_id = data.get('id')
        if notif_id:
            notification_service.mark_one_read(current_user.id, notif_id)
        else:
            notification_service.mark_all_as_read(current_user.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/notifications/create', methods=['POST'])
@login_required
@csrf.exempt
def create_notification():
    try:
        data = request.get_json()
        message = data.get('message')
        title = data.get('title')
        notif_type = data.get('type', 'info')
        link = data.get('link')

        if not message:
            return jsonify({'success': False, 'message': 'Mensaje es requerido'}), 400

        notification_service.create_notification(
            user_id=current_user.id,
            title=title,
            message=message,
            notif_type=notif_type,
            link=link
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

