from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self):
        self.repo = NotificationRepository()

    def create_notification(self, user_id, message, title=None, notif_type='info', link=None):
        return self.repo.create(user_id, message, title, notif_type, link)

    def get_unread_notifications(self, user_id):
        return self.repo.get_unread_by_user(user_id)

    def mark_all_as_read(self, user_id):
        self.repo.mark_all_read(user_id)

    def mark_one_read(self, user_id, notif_id):
        self.repo.mark_one_read(user_id, notif_id)
