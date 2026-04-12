from app.models import Notification, db

class NotificationRepository:
    @staticmethod
    def create(user_id, message, link=None):
        notif = Notification(user_id=user_id, message=message, link=link)
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
