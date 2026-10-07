"""Canales de aviso (SMS / WhatsApp): número de destino y plantillas, guardados en la base de datos.

Antes se escribían solo en `os.environ` del proceso: se perdían al reiniciar el servidor y no llegaban a otros procesos.
Orden de lectura: base de datos > configuración de la app > variable de entorno.
"""

import os
import re
import string

from app.extensions import db
from app.models.system_setting import SystemSetting
from app.services import live_sync

FIELDS = {
    'destination': 'NOTIFICATION_SMS_DESTINATION',
    'sms_template': 'NOTIFICATION_SMS_TEMPLATE',
    'whatsapp_template': 'NOTIFICATION_WHATSAPP_TEMPLATE',
}
PLACEHOLDERS = ('patient_name', 'amount', 'due_date_str', 'days_overdue')
MAX_TEMPLATE = 1000
_PHONE = re.compile(r'^\+?\d{7,15}$')


def _db_key(field):
    return f'channels.{field}'


def get(field, default=''):
    """Valor vigente de un campo (DB primero). Nunca lanza: si la tabla no existe todavía, cae al entorno."""
    from flask import current_app

    env_key = FIELDS[field]
    try:
        row = db.session.get(SystemSetting, _db_key(field))
        if row is not None and row.value is not None:
            return row.value
    except Exception:
        db.session.rollback()
    return current_app.config.get(env_key) or os.environ.get(env_key) or default


def get_all():
    return {field: get(field) for field in FIELDS}


def template_error(template):
    """Una plantilla solo puede usar {patient_name}, {amount}, {due_date_str} y {days_overdue}, sin atributos ni formatos raros."""
    if len(template) > MAX_TEMPLATE:
        return f'La plantilla no puede superar {MAX_TEMPLATE} caracteres'
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError:
        return 'Las llaves { } de la plantilla no están bien cerradas'
    for _literal, name, spec, conv in parsed:
        if name is None:
            continue
        if name not in PLACEHOLDERS or conv:
            return f'Variable no permitida: {{{name}}}. Usa: ' + ', '.join('{' + p + '}' for p in PLACEHOLDERS)
        if spec and not re.fullmatch(r'\.\d+f|\d*', spec):
            return f'Formato no permitido en {{{name}}}'
    return None


def validate(data):
    errors = {}
    clean = {}
    if 'destination' in data:
        value = re.sub(r'[\s\-().]', '', str(data['destination'] or ''))
        if value and not _PHONE.match(value):
            errors['destination'] = 'Escribe un número válido, con código de país (ej. +51921507470)'
        else:
            clean['destination'] = value
    for field in ('sms_template', 'whatsapp_template'):
        if field in data:
            value = str(data[field] or '').strip()
            problem = template_error(value) if value else None
            if problem:
                errors[field] = problem
            else:
                clean[field] = value
    return clean, errors


def update(data, user_id=None):
    """Guarda (o borra, si el valor es vacío) los campos recibidos. Devuelve (campos_guardados, errores)."""
    from flask import current_app

    clean, errors = validate(data)
    if errors:
        return [], errors
    for field, value in clean.items():
        env_key = FIELDS[field]
        row = db.session.get(SystemSetting, _db_key(field))
        if row is None:
            row = SystemSetting(key=_db_key(field))
            db.session.add(row)
        row.value = value
        row.updated_by_id = user_id
        # Misma vigencia inmediata que antes para el proceso actual.
        if value:
            current_app.config[env_key] = value
            os.environ[env_key] = value
        else:
            current_app.config.pop(env_key, None)
            os.environ.pop(env_key, None)
    db.session.commit()
    if clean:
        live_sync.bump('channels')
    return list(clean), {}


def render(template, values):
    """Rellena la plantilla; si algo falla devuelve None para que el llamador use el texto por defecto."""
    try:
        return template.format(**values)
    except Exception:
        return None
