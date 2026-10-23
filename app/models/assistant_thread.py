"""Conversaciones del asistente del admin (PRP 015).

Se guardan los bloques ya calculados: al reabrir no se vuelve a consultar («Actualizar» recalcula). Una
conversación es de su autor; si la comparte, la ven los demás administradores. Las no fijadas se borran a los
180 días. `AssistantSchedule` repite una pregunta cada día o semana y manda la respuesta por correo o Telegram.
"""

from datetime import datetime

from app.extensions import db


class AssistantThread(db.Model):
    __tablename__ = 'assistant_thread'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False, default='Nueva conversación')
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    shared = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    messages = db.relationship(
        'AssistantMessage',
        backref='thread',
        cascade='all, delete-orphan',
        order_by='AssistantMessage.id',
        lazy='dynamic',
    )


class AssistantMessage(db.Model):
    __tablename__ = 'assistant_message'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(
        db.Integer, db.ForeignKey('assistant_thread.id', ondelete='CASCADE'), nullable=False, index=True
    )
    role = db.Column(db.String(12), nullable=False)  # user | assistant
    text = db.Column(db.Text, nullable=True)  # la pregunta (user) o el texto plano de la respuesta
    blocks = db.Column(db.JSON, nullable=True)
    sources = db.Column(db.JSON, nullable=True)
    model = db.Column(db.String(80), nullable=True)
    question = db.Column(db.Text, nullable=True)  # en respuestas: la pregunta que la originó (para «Actualizar»)
    feedback = db.Column(db.SmallInteger, nullable=True)  # 1 útil · -1 no útil
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AssistantSchedule(db.Model):
    __tablename__ = 'assistant_schedule'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('assistant_thread.id', ondelete='SET NULL'), nullable=True)
    question = db.Column(db.Text, nullable=False)
    cadence = db.Column(db.String(10), nullable=False, default='weekly')  # daily | weekly
    weekday = db.Column(db.SmallInteger, nullable=True)  # 0 = lunes (solo weekly)
    hour = db.Column(db.SmallInteger, nullable=False, default=8)  # hora de Lima
    channel = db.Column(db.String(10), nullable=False, default='email')  # email | telegram | both
    active = db.Column(db.Boolean, nullable=False, default=True)
    last_run_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
