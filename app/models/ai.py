from datetime import datetime
from app.extensions import db
from app.models.base import AuditMixin


class AIConversation(db.Model, AuditMixin):
    __tablename__ = 'ai_conversation'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    session_id = db.Column(db.String(100), nullable=True)
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('ai_conversations', lazy=True, cascade='all, delete-orphan'))

    messages = db.relationship('AIChatMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')


class AIChatMessage(db.Model, AuditMixin):
    __tablename__ = 'ai_chat_message'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversation.id'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(100), nullable=True)
    parameters = db.Column(db.JSON, nullable=True)
    action_status = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'intent': self.intent,
            'parameters': self.parameters,
            'action_status': self.action_status
        }
