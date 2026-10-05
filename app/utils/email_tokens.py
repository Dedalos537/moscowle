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
