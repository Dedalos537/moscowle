from app.models import Message, db
from app.services.notification_service import NotificationService
from flask import url_for

class MessageService:
    def __init__(self):
        self.notification_service = NotificationService()

    def send_message(self, sender_id, receiver_id, subject, body):
        msg = Message(sender_id=sender_id, receiver_id=receiver_id, subject=subject, body=body)
        db.session.add(msg)
        db.session.commit()
        
        try:
            self.notification_service.create_notification(receiver_id, f"Nuevo mensaje: {subject}", url_for('main.messages_list'))
        except Exception:
            pass
            
        return msg

    def get_conversations(self, user_id):
        # Complex query logic might be better here than in controller
        # For now, let's assume the controller handles the display logic 
        # or we move the query here.
        pass
