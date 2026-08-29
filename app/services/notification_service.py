"""Notification Service — routing layer that delegates to the Intelligence engine.

All notification creation now goes through the grouping system.
The old individual-row approach is replaced by group + item writes.
"""

import logging

from flask import current_app

from app.extensions import db, socketio
from app.services.notification_intelligence import (
    add_item_to_group,
    get_group_items,
    get_unread_notifications_legacy,
    get_user_group_count,
    get_user_groups,
    mark_all_groups_read,
    mark_group_read,
    toggle_group_collapse,
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        pass

    # ─── Grouped Notification API (new) ──────────────────────────────────────

    def notify_user(
        self,
        user_id,
        message,
        title=None,
        notif_type='info',
        link=None,
        category='system',
        priority='normal',
        icon=None,
        metadata_json=None,
        skip_telegram=False,
        event_type=None,
        event_kwargs=None,
    ):
        """Create a grouped notification with optional real-time push.

        This is the PRIMARY entry point for all new notifications.
        It checks preferences, groups similar notifications, and pushes via Socket.IO.
        """
        # Check user preferences
        prefs = self._get_preferences(user_id)
        if prefs:
            enabled_map = {
                'debt': getattr(prefs, 'debt_enabled', True),
                'activity': getattr(prefs, 'activity_enabled', True),
                'system': getattr(prefs, 'system_enabled', True),
                'alert': getattr(prefs, 'alert_enabled', True),
                'payment': getattr(prefs, 'payment_enabled', True),
                'security': getattr(prefs, 'system_enabled', True),
                'audit': getattr(prefs, 'activity_enabled', True),
                'report': getattr(prefs, 'system_enabled', True),
            }
            if not enabled_map.get(category, True):
                return None

        # Route through the intelligence engine
        etype = event_type or self._infer_event_type(category, notif_type, metadata_json)
        kwargs = dict(event_kwargs or {})
        if metadata_json and isinstance(metadata_json, dict):
            kwargs.update(metadata_json)

        group, is_new = add_item_to_group(
            user_id=user_id,
            event_type=etype,
            message=message,
            title=title,
            notif_type=notif_type,
            link=link,
            priority=priority,
            icon=icon,
            metadata_json=metadata_json,
            **kwargs,
        )

        # Always emit Socket.IO so the user sees the update in real-time
        count = get_user_group_count(user_id)
        socketio.emit(
            'notification:new',
            {
                'id': group.id,
                'title': group.title or self._default_title(category),
                'message': group.summary or message[:120],
                'type': notif_type,
                'category': group.category,
                'priority': group.priority,
                'icon': icon,
                'link': link,
                'timestamp': group.last_item_at.strftime('%d %b, %H:%M'),
                'unread_count': count,
                'group_count': group.count,
                'is_group': True,
            },
            room=f'user_{user_id}',
        )

        # Telegram: only for urgent/high priority or when group count hits threshold
        if not skip_telegram and (priority in ('urgent', 'high') or (group.count >= 5 and group.count % 5 == 0)):
            try:
                if current_app.config.get('TELEGRAM_BOT_TOKEN'):
                    from app.services.telegram_bot_service import send_notification_to_telegram

                    send_notification_to_telegram(
                        user_id=user_id,
                        title=title or group.title,
                        message=message,
                        priority=priority,
                    )
            except Exception:
                pass

        return group

    def create_notification(
        self,
        user_id,
        message,
        title=None,
        notif_type='info',
        link=None,
        category='system',
        priority='normal',
        icon=None,
        metadata_json=None,
    ):
        """Create a notification without preference check (for system/internal use).

        Routes through the grouping engine but skips preference filtering.
        Used by: tasks.py, report generation, scheduler jobs, etc.
        """
        etype = self._infer_event_type(category, notif_type, metadata_json)
        kwargs = {}
        if metadata_json and isinstance(metadata_json, dict):
            kwargs.update(metadata_json)

        group, is_new = add_item_to_group(
            user_id=user_id,
            event_type=etype,
            message=message,
            title=title,
            notif_type=notif_type,
            link=link,
            priority=priority,
            icon=icon,
            metadata_json=metadata_json,
            **kwargs,
        )

        # Emit Socket.IO
        count = get_user_group_count(user_id)
        socketio.emit(
            'notification:new',
            {
                'id': group.id,
                'title': group.title or self._default_title(category),
                'message': group.summary or message[:120],
                'type': notif_type,
                'category': group.category,
                'priority': group.priority,
                'icon': icon,
                'link': link,
                'timestamp': group.last_item_at.strftime('%d %b, %H:%M'),
                'unread_count': count,
                'group_count': group.count,
                'is_group': True,
            },
            room=f'user_{user_id}',
        )

        return group

    # ─── Read Operations ────────────────────────────────────────────────────

    def get_unread_notifications(self, user_id):
        """Get unread notifications (legacy format for backward compat)."""
        return get_unread_notifications_legacy(user_id)

    def get_unread_groups(self, user_id):
        """Get unread notification groups for the new UI."""
        return get_user_groups(user_id, include_read=False)

    def get_all_groups(self, user_id, category=None):
        """Get all groups optionally filtered by category."""
        return get_user_groups(user_id, category=category, include_read=True)

    def get_group_items(self, group_id, user_id, limit=20):
        """Get items within a group."""
        return get_group_items(group_id, user_id, limit=limit)

    def get_count(self, user_id):
        """Get unread group count for badge."""
        return get_user_group_count(user_id)

    def get_by_category(self, user_id, category, limit=20):
        """Get notifications by category (legacy format)."""
        groups = get_user_groups(user_id, category=category, include_read=True, limit=limit)
        result = []
        for g in groups:
            result.append(
                {
                    'id': g.id,
                    'title': g.title or category,
                    'type': 'info',
                    'category': g.category,
                    'priority': g.priority,
                    'icon': None,
                    'message': g.summary or f'{g.count} notificaciones de {category}',
                    'timestamp': g.last_item_at.strftime('%d %b, %H:%M'),
                    'link': None,
                    'count': g.count,
                }
            )
        return result

    def mark_all_as_read(self, user_id):
        """Mark all groups as read."""
        mark_all_groups_read(user_id)

    def mark_one_read(self, user_id, notif_id):
        """Mark a single group as read."""
        mark_group_read(notif_id, user_id)

    def mark_group_read(self, group_id, user_id):
        """Mark a group as read (explicit API)."""
        mark_group_read(group_id, user_id)

    def toggle_group_collapse(self, group_id, user_id):
        """Toggle the collapsed state of a group."""
        return toggle_group_collapse(group_id, user_id)

    # ─── Preferences ────────────────────────────────────────────────────────

    def get_preferences(self, user_id):
        """Get notification preferences."""
        return self._get_preferences(user_id)

    def update_preferences(self, user_id, data):
        """Update notification preferences."""
        return self._update_preferences(user_id, data)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _get_preferences(self, user_id):
        from app.models.notification import UserNotificationPreference as Pref

        prefs = Pref.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = Pref(user_id=user_id)
            db.session.add(prefs)
            db.session.commit()
        return prefs

    def _update_preferences(self, user_id, data):
        from app.models.notification import UserNotificationPreference as Pref

        prefs = Pref.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = Pref(user_id=user_id)
            db.session.add(prefs)
        for field in [
            'debt_enabled',
            'activity_enabled',
            'system_enabled',
            'alert_enabled',
            'payment_enabled',
            'sound_enabled',
            'browser_notifications',
            'digest_enabled',
            'digest_channel',
        ]:
            if field in data:
                setattr(prefs, field, data[field])
        db.session.commit()
        return prefs

    def _infer_event_type(self, category, notif_type, metadata_json):
        """Infer event_type from category and type for the group key."""
        if metadata_json and isinstance(metadata_json, dict):
            return metadata_json.get('event_type', category)
        return category

    def _default_title(self, category):
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
