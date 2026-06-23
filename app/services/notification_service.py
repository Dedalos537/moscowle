from app.extensions import socketio
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self):
        self.repo = NotificationRepository()

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
        return self.repo.create(user_id, message, title, notif_type, link, category, priority, icon, metadata_json)

    def get_unread_notifications(self, user_id):
        return self.repo.get_unread_by_user(user_id)

    def get_count(self, user_id):
        return self.repo.get_count_by_user(user_id)

    def get_by_category(self, user_id, category):
        return self.repo.get_by_category(user_id, category)

    def mark_all_as_read(self, user_id):
        self.repo.mark_all_read(user_id)

    def mark_one_read(self, user_id, notif_id):
        self.repo.mark_one_read(user_id, notif_id)

    def get_preferences(self, user_id):
        return self.repo.get_preferences(user_id)

    def update_preferences(self, user_id, data):
        return self.repo.update_preferences(user_id, data)

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
    ):
        prefs = self.repo.get_preferences(user_id)
        enabled_map = {
            'debt': prefs.debt_enabled,
            'activity': prefs.activity_enabled,
            'system': prefs.system_enabled,
            'alert': prefs.alert_enabled,
            'payment': prefs.payment_enabled,
        }
        enabled = enabled_map.get(category, True)
        if not enabled:
            return None
        notif = self.create_notification(
            user_id=user_id,
            message=message,
            title=title,
            notif_type=notif_type,
            link=link,
            category=category,
            priority=priority,
            icon=icon,
            metadata_json=metadata_json,
        )
        count = self.get_count(user_id)
        socketio.emit(
            'notification:new',
            {
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'type': notif.type or 'info',
                'category': notif.category,
                'priority': notif.priority,
                'icon': notif.icon,
                'link': notif.link,
                'timestamp': notif.timestamp.strftime('%d %b, %H:%M'),
                'unread_count': count,
            },
            room=f'user_{user_id}',
        )
        return notif
