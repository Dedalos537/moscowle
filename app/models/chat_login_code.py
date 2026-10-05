"""Codigos de un solo uso para iniciar sesion en un chat (Telegram).

El usuario ya autenticado en la web genera el codigo y lo escribe en el chat con
/login. Solo se guarda un HMAC del codigo: un volcado de la BD no sirve para
vincular chats.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db

# Sin caracteres ambiguos (0/O, 1/I): se dicta o se copia a mano.
CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
CODE_LENGTH = 8
CODE_TTL_MINUTES = 10


def _digest(code):
    key = (current_app.config.get('SECRET_KEY') or '').encode()
    return hmac.new(key, str(code).strip().upper().encode(), hashlib.sha256).hexdigest()


class ChatLoginCode(db.Model):
    __tablename__ = 'chat_login_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @classmethod
    def issue(cls, user_id):
        """Genera un codigo nuevo e invalida los pendientes del usuario."""
        now = datetime.utcnow()
        cls.query.filter(cls.user_id == user_id, cls.used_at.is_(None)).update({'used_at': now})
        code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        db.session.add(
            cls(user_id=user_id, code_hash=_digest(code), expires_at=now + timedelta(minutes=CODE_TTL_MINUTES))
        )
        db.session.commit()
        return code

    @classmethod
    def consume(cls, code):
        """Devuelve el User dueño del codigo y lo marca usado; None si no vale
        (inexistente, usado, expirado o usuario inactivo)."""
        from app.models.user import User  # noqa: PLC0415  (lazy: evita import circular con app.models)

        now = datetime.utcnow()
        rec = cls.query.filter(cls.code_hash == _digest(code), cls.used_at.is_(None), cls.expires_at > now).first()
        if rec is None:
            return None
        rec.used_at = now
        db.session.commit()
        user = db.session.get(User, rec.user_id)
        if user is None or not getattr(user, 'is_active', True):
            return None
        return user
