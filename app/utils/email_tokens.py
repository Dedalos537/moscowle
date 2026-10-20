"""Tokens firmados para el enlace de baja de los correos (sin login)."""

from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

_SALT = 'email-unsubscribe'
DEFAULT_MAX_AGE = 60 * 60 * 24 * 365  # 1 anio: un correo viejo debe poder darse de baja


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SALT)


def make_unsubscribe_token(user_id):
    return _serializer().dumps({'u': int(user_id)})


def read_unsubscribe_token(token, max_age=DEFAULT_MAX_AGE):
    """Devuelve el user_id del token o None si es invalido, manipulado o vencido."""
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=max_age)
        return int(data['u'])
    except (BadSignature, KeyError, TypeError, ValueError):
        return None


# ── Enlace para crear la contraseña (bienvenida / cambio por un admin) ───────
_SET_SALT = 'set-password'
SET_PASSWORD_MAX_AGE = 72 * 3600  # 72 h


def _password_fingerprint(user):
    # Cambia al cambiar la contraseña: el enlace sirve UNA vez (después queda inválido solo).
    return (user.password or '')[-12:]


def make_set_password_token(user):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SET_SALT)
    return s.dumps({'u': int(user.id), 'f': _password_fingerprint(user)})


def read_set_password_token(token, max_age=SET_PASSWORD_MAX_AGE):
    """Devuelve el usuario si el token es válido, no venció y la contraseña no cambió desde que se emitió."""
    from app.extensions import db
    from app.models import User

    if not token:
        return None
    try:
        data = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SET_SALT).loads(token, max_age=max_age)
        user = db.session.get(User, int(data['u']))
    except (BadSignature, KeyError, TypeError, ValueError):
        return None
    if not user or user.is_active is False or data.get('f') != _password_fingerprint(user):
        return None
    return user


def set_password_link(user):
    base = (current_app.config.get('FRONTEND_URL') or 'https://moscowle.centrojuanpabloii.com').rstrip('/')
    return f'{base}/auth/set-password?t={make_set_password_token(user)}'
