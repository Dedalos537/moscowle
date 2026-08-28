from datetime import datetime, timedelta

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

# ─── Group-based endpoints (new system) ───────────────────────────────────


@api_bp.route('/notifications/groups')
@login_required
def get_notification_groups():
    """Get all notification groups for the current user."""
    try:
        category = request.args.get('category')
        include_read = request.args.get('include_read', 'false').lower() == 'true'
        groups = notification_service.get_all_groups(current_user.id, category=category)
        if not include_read:
            groups = [g for g in groups if not g.is_read]

        result = []
        for g in groups:
            result.append(
                {
                    'id': g.id,
                    'title': g.title or _default_title(g.category),
                    'category': g.category,
                    'priority': g.priority,
                    'count': g.count,
                    'summary': g.summary,
                    'is_read': g.is_read,
                    'is_collapsed': g.is_collapsed,
                    'ai_summary_generated': g.ai_summary_generated,
                    'timestamp': g.last_item_at.strftime('%d %b, %H:%M'),
                    'last_item_at': g.last_item_at.isoformat(),
                }
            )
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'Error in get_notification_groups: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/groups/<int:group_id>/items')
@login_required
def get_notification_group_items(group_id):
    """Get items within a specific group."""
    try:
        limit = request.args.get('limit', 20, type=int)
        items = notification_service.get_group_items(group_id, current_user.id, limit=limit)
        result = []
        for item in items:
            result.append(
                {
                    'id': item.id,
                    'message': item.message,
                    'type': item.type or 'info',
                    'priority': item.priority or 'normal',
                    'icon': item.icon,
                    'link': item.link,
                    'timestamp': item.timestamp.strftime('%d %b, %H:%M'),
                }
            )
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'Error in get_notification_group_items: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/groups/<int:group_id>/read', methods=['POST'])
@login_required
def mark_group_read(group_id):
    """Mark a specific group as read."""
    try:
        notification_service.mark_group_read(group_id, current_user.id)
        count = notification_service.get_count(current_user.id)
        return jsonify({'success': True, 'unread_count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/groups/read-all', methods=['POST'])
@login_required
def mark_all_groups_read():
    """Mark all groups as read."""
    try:
        notification_service.mark_all_as_read(current_user.id)
        return jsonify({'success': True, 'unread_count': 0})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/groups/<int:group_id>/collapse', methods=['POST'])
@login_required
def toggle_group_collapse(group_id):
    """Toggle collapsed/expanded state of a group."""
    try:
        group = notification_service.toggle_group_collapse(group_id, current_user.id)
        if group:
            return jsonify({'success': True, 'is_collapsed': group.is_collapsed})
        return jsonify({'success': False, 'message': 'Group not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/groups/summary')
@login_required
def get_groups_summary():
    """Get a summary of groups for a date range (for daily digest preview)."""
    try:
        days = request.args.get('days', 1, type=int)
        since = datetime.utcnow() - timedelta(days=days)
        groups = notification_service.get_all_groups(current_user.id)
        recent = [g for g in groups if g.last_item_at >= since]

        total_items = sum(g.count for g in recent)
        by_category = {}
        for g in recent:
            cat = g.category
            by_category[cat] = by_category.get(cat, 0) + g.count

        by_priority = {}
        for g in recent:
            pri = g.priority
            by_priority[pri] = by_priority.get(pri, 0) + g.count

        return jsonify(
            {
                'total_groups': len(recent),
                'total_items': total_items,
                'by_category': by_category,
                'by_priority': by_priority,
                'period_days': days,
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/digest/test', methods=['POST'])
@login_required
def send_test_digest():
    """Send a test digest to the current user."""
    try:
        from app.services.daily_digest_service import send_test_digest

        result = send_test_digest(current_user.id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── Legacy endpoints (backward compatibility) ───────────────────────────


@api_bp.route('/notifications')
@login_required
def get_notifications():
    """Get unread notifications (legacy format using groups)."""
    try:
        notifications = notification_service.get_unread_notifications(current_user.id)
        return jsonify(notifications)
    except Exception as e:
        current_app.logger.error(f'Error in get_notifications: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/count')
@login_required
def get_notification_count():
    """Get unread count (group-based)."""
    try:
        count = notification_service.get_count(current_user.id)
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/category/<string:category>')
@login_required
def get_notifications_by_category(category):
    """Get notifications by category (legacy format using groups)."""
    try:
        notifications = notification_service.get_by_category(current_user.id, category)
        return jsonify(notifications)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/preferences', methods=['GET', 'PUT'])
@login_required
def notification_preferences():
    """Get or update notification preferences (includes digest settings)."""
    try:
        if request.method == 'GET':
            prefs = notification_service.get_preferences(current_user.id)
            return jsonify(
                {
                    'debt_enabled': getattr(prefs, 'debt_enabled', True),
                    'activity_enabled': getattr(prefs, 'activity_enabled', True),
                    'system_enabled': getattr(prefs, 'system_enabled', True),
                    'alert_enabled': getattr(prefs, 'alert_enabled', True),
                    'payment_enabled': getattr(prefs, 'payment_enabled', True),
                    'sound_enabled': getattr(prefs, 'sound_enabled', True),
                    'browser_notifications': getattr(prefs, 'browser_notifications', False),
                    'digest_enabled': getattr(prefs, 'digest_enabled', True),
                    'digest_channel': getattr(prefs, 'digest_channel', 'both'),
                }
            )
        else:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Datos requeridos'}), 400
            notification_service.update_preferences(current_user.id, data)
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
@csrf.exempt
def mark_notifications_read():
    """Mark notifications as read (legacy + new)."""
    try:
        data = request.get_json() or {}
        notif_id = data.get('id')
        if notif_id:
            notification_service.mark_one_read(current_user.id, notif_id)
        else:
            notification_service.mark_all_as_read(current_user.id)
        count = notification_service.get_count(current_user.id)
        return jsonify({'success': True, 'unread_count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/create', methods=['POST'])
@login_required
@csrf.exempt
def create_notification():
    """Create a notification (legacy endpoint, now routes through groups)."""
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


def _default_title(category):
    titles = {
        'message': 'Mensajes',
        'session': 'Sesiones',
        'game': 'Actividad',
        'payment': 'Pagos',
        'alert': 'Alertas',
        'security': 'Seguridad',
        'report': 'Reportes',
        'audit': 'Auditorías',
        'system': 'Sistema',
        'debt': 'Deudas',
        'activity': 'Actividad',
    }
    return titles.get(category, 'Notificaciones')
