from datetime import datetime
from app.extensions import db


class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_id])

    @property
    def last_message(self):
        return Message.query.filter_by(chat_id=self.id).order_by(Message.created_at.desc()).first()

    def unread_count_for(self, user_id):
        participant = ChatParticipant.query.filter_by(chat_id=self.id, user_id=user_id).first()
        if not participant or not participant.last_read_at:
            return Message.query.filter(
                Message.chat_id == self.id,
                Message.sender_id != user_id,
                Message.status.in_(['sent', 'delivered'])
            ).count()
        return Message.query.filter(
            Message.chat_id == self.id,
            Message.sender_id != user_id,
            Message.created_at > participant.last_read_at,
            Message.status.in_(['sent', 'delivered'])
        ).count()


class ChatParticipant(db.Model):
    __tablename__ = 'chat_participant'
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_read_at = db.Column(db.DateTime, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    chat = db.relationship('Chat', backref='participant_list', lazy='joined')
    user = db.relationship('User', backref='chat_participations', lazy='joined')


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    parent_message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=True)
    status = db.Column(db.String(20), default='sent')

    attachment_path = db.Column(db.String(500), nullable=True)
    attachment_type = db.Column(db.String(50), nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True, cascade="all, delete-orphan"))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True, cascade="all, delete-orphan"))
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy=True)

    @property
    def file_url(self):
        if self.attachment_path:
            from flask import url_for
            return url_for('uploads.protected_file', filename=f'messages/{self.attachment_path}', _external=False)
        return None


class ContactMessage(db.Model):
    __tablename__ = 'contact_message'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    service_interest = db.Column(db.String(100), nullable=True)
    urgency = db.Column(db.String(50), default='medium')
    status = db.Column(db.String(50), default='unread')
    ai_analysis = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
