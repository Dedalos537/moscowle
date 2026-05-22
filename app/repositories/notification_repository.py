from app.models import Notification, db

class NotificationRepository:
    @staticmethod
    def create(user_id, message, title=None, notif_type='info', link=None):
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            link=link
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def get_unread_by_user(user_id):
        return Notification.query.filter_by(user_id=user_id, is_read=False).order_by(Notification.timestamp.desc()).all()

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
        Notification.query.filter(
            Notification.is_read == True,
            Notification.timestamp < cutoff
        ).delete()
        db.session.commit()

    @staticmethod
    def get_by_user_and_type(user_id, notif_type, limit=1):
        return Notification.query.filter_by(
            user_id=user_id, type=notif_type, is_read=False
        ).order_by(Notification.timestamp.desc()).limit(limit).all()
