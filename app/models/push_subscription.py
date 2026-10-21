"""Suscripciones Web Push del navegador: permiten avisar aunque la página esté cerrada.

Cada navegador/dispositivo que acepta las notificaciones guarda aquí su endpoint y sus claves públicas.
Si el servicio de push responde 404/410 (el usuario quitó el permiso o desinstaló), la fila se borra.
"""

from datetime import datetime

from app.extensions import db


class PushSubscription(db.Model):
    __tablename__ = 'push_subscription'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    endpoint = db.Column(db.String(700), nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(64), nullable=False)
    user_agent = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_ok_at = db.Column(db.DateTime, nullable=True)
