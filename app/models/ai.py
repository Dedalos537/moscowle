from datetime import datetime
from app.extensions import db


class AIConversation(db.Model):
    __tablename__ = 'ai_conversation'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('ai_conversations', lazy=True, cascade='all, delete-orphan'))

    messages = db.relationship('AIChatMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')


class AIChatMessage(db.Model):
    __tablename__ = 'ai_chat_message'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversation.id'), nullable=False)
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
