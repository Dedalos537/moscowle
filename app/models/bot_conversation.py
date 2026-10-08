"""Conversaciones del bot con las personas (Telegram, WhatsApp): historial para verlas en vivo y responder.

Antes el panel mostraba «Conversaciones» sin ningún mensaje (`last_message: None`): nada se guardaba.
"""

from datetime import UTC, datetime

from app.extensions import db


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


class BotConversation(db.Model):
    __tablename__ = 'bot_conversation'
    __table_args__ = (db.UniqueConstraint('channel', 'chat_key', name='uq_bot_conv_channel_chat'),)

    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(20), nullable=False, index=True)  # telegram | whatsapp
    chat_key = db.Column(db.String(80), nullable=False)  # chat_id de Telegram o teléfono (solo dígitos)
    contact_name = db.Column(db.String(160), nullable=True)
    contact_handle = db.Column(db.String(160), nullable=True)  # @usuario o +teléfono
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # usuario de la plataforma, si se conoce
    # Con la conversación tomada por una persona, el bot no contesta: contesta el administrador.
    human_takeover = db.Column(db.Boolean, default=False, nullable=False)
    taken_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    unread_count = db.Column(db.Integer, default=0, nullable=False)
    last_preview = db.Column(db.String(200), nullable=True)
    last_message_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    messages = db.relationship('BotMessage', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'channel': self.channel,
            'chat_key': self.chat_key,
            'contact': self.contact_name or self.contact_handle or self.chat_key,
            'handle': self.contact_handle,
            'user_id': self.user_id,
            'human_takeover': bool(self.human_takeover),
            'unread': self.unread_count or 0,
            'last_message': self.last_preview,
            'timestamp': self.last_message_at.isoformat() + 'Z' if self.last_message_at else None,
            'linked_phone': self.linked_phone(),
        }

    def linked_phone(self):
        """Teléfono real que un administrador asoció a un contacto con número oculto (@lid), si lo hay."""
        if self.channel != 'whatsapp' or not (self.contact_handle or '').startswith('lid:'):
            return None
        from app.models.system_setting import SystemSetting

        row = db.session.get(SystemSetting, f'wa.lid_phone.{self.chat_key}')
        return row.value if row is not None and row.value else None


class BotMessage(db.Model):
    __tablename__ = 'bot_message'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('bot_conversation.id'), nullable=False, index=True)
    direction = db.Column(db.String(3), nullable=False)  # in | out
    sender = db.Column(db.String(10), nullable=False)  # contact | bot | admin
    kind = db.Column(db.String(10), default='text', nullable=False)  # text | voice | image
    text = db.Column(db.Text, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(10), default='sent', nullable=False)  # sent | failed
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'direction': self.direction,
            'sender': self.sender,
            'kind': self.kind,
            'text': self.text,
            'admin_id': self.admin_id,
            'status': self.status,
            'error': self.error,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }
