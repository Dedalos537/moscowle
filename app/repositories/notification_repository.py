from app.models import Notification, UserNotificationPreference, db


class NotificationRepository:
    @staticmethod
    def create(
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
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            category=category,
            priority=priority,
            icon=icon,
            link=link,
            metadata_json=metadata_json,
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def get_unread_by_user(user_id):
        return (
            Notification.query.filter_by(user_id=user_id, is_read=False).order_by(Notification.timestamp.desc()).all()
        )

    @staticmethod
    def get_count_by_user(user_id):
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def get_by_category(user_id, category, limit=20):
        return (
            Notification.query.filter_by(user_id=user_id, category=category)
            .order_by(Notification.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_all_read(user_id):
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()

    @staticmethod
    def mark_one_read(user_id, notif_id):
        Notification.query.filter_by(user_id=user_id, id=notif_id).update({'is_read': True})
        db.session.commit()

    @staticmethod
    def delete_old_read(days=30):
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        Notification.query.filter(Notification.is_read, Notification.timestamp < cutoff).delete()
        db.session.commit()

    @staticmethod
    def get_by_user_and_type(user_id, notif_type, limit=1):
        return (
            Notification.query.filter_by(user_id=user_id, type=notif_type, is_read=False)
            .order_by(Notification.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_preferences(user_id):
        prefs = UserNotificationPreference.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = UserNotificationPreference(user_id=user_id)
            db.session.add(prefs)
            db.session.commit()
        return prefs

    @staticmethod
    def update_preferences(user_id, data):
        prefs = NotificationRepository.get_preferences(user_id)
        for field in [
            'debt_enabled',
            'activity_enabled',
            'system_enabled',
            'alert_enabled',
            'payment_enabled',
            'sound_enabled',
            'browser_notifications',
        ]:
            if field in data:
                setattr(prefs, field, data[field])
        db.session.commit()
        return prefs
