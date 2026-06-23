from app.routes.api import api_bp
from app.routes.api._shared import (
    csrf,
    current_app,
    current_user,
    jsonify,
    login_required,
    notification_service,
    request,
)


@api_bp.route('/notifications')
@login_required
def get_notifications():
    try:
        notifications = notification_service.get_unread_notifications(current_user.id)
        result = [
            {
                'id': n.id,
                'title': n.title,
                'type': n.type or 'info',
                'category': n.category,
                'priority': n.priority,
                'icon': n.icon,
                'message': n.message,
                'timestamp': n.timestamp.strftime('%d %b, %H:%M'),
                'link': n.link,
            }
            for n in notifications
        ]
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'Error in get_notifications: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/count')
@login_required
def get_notification_count():
    try:
        count = notification_service.get_count(current_user.id)
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/category/<string:category>')
@login_required
def get_notifications_by_category(category):
    try:
        notifications = notification_service.get_by_category(current_user.id, category)
        result = [
            {
                'id': n.id,
                'title': n.title,
                'type': n.type or 'info',
                'category': n.category,
                'priority': n.priority,
                'icon': n.icon,
                'message': n.message,
                'timestamp': n.timestamp.strftime('%d %b, %H:%M'),
                'link': n.link,
            }
            for n in notifications
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/preferences', methods=['GET', 'PUT'])
@login_required
def notification_preferences():
    try:
        if request.method == 'GET':
            prefs = notification_service.get_preferences(current_user.id)
            return jsonify(
                {
                    'debt_enabled': prefs.debt_enabled,
                    'activity_enabled': prefs.activity_enabled,
                    'system_enabled': prefs.system_enabled,
                    'alert_enabled': prefs.alert_enabled,
                    'payment_enabled': prefs.payment_enabled,
                    'sound_enabled': prefs.sound_enabled,
                    'browser_notifications': prefs.browser_notifications,
                }
            )
        else:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Datos requeridos'}), 400
            prefs = notification_service.update_preferences(current_user.id, data)
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


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
        category = data.get('category', 'system')
        priority = data.get('priority', 'normal')
        icon = data.get('icon')
        metadata_json = data.get('metadata_json')

        if not message:
            return jsonify({'success': False, 'message': 'Mensaje es requerido'}), 400

        notification_service.create_notification(
            user_id=current_user.id,
            title=title,
            message=message,
            notif_type=notif_type,
            link=link,
            category=category,
            priority=priority,
            icon=icon,
            metadata_json=metadata_json,
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
