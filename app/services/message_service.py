import contextlib

from flask import url_for

from app.models import Message, db
from app.services.notification_service import NotificationService


class MessageService:
    def __init__(self):
        self.notification_service = NotificationService()

    def send_message(self, sender_id, receiver_id, subject, body):
        msg = Message(sender_id=sender_id, receiver_id=receiver_id, subject=subject, body=body)
        db.session.add(msg)
        db.session.commit()

        with contextlib.suppress(Exception):
            self.notification_service.create_notification(
                receiver_id, f'Nuevo mensaje: {subject}', link=url_for('main.messages_list')
            )

        return msg

    def get_conversations(self, user_id):
        pass
