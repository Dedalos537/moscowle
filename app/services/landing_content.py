"""Contenido editable de la landing: valores por defecto, validación y versión publicada.

El contenido por defecto vive en app/data/landing_default.json, que también usa la landing (landing/) como respaldo
si la API no responde, así ambos lados parten del mismo texto. La validación es estricta a propósito: el admin escribe
texto plano (la landing nunca interpreta HTML), con largos acotados y enlaces https.
"""

import copy
import json
import re
from functools import lru_cache
from pathlib import Path

from app.extensions import db
from app.models.landing import LandingContentVersion

DEFAULT_PATH = Path(__file__).resolve().parent.parent / 'data' / 'landing_default.json'


class ContentError(ValueError):
    pass


def _str(max_len, required=True, kind='text'):
    return {'type': 'str', 'max': max_len, 'required': required, 'kind': kind}


def _list(item, max_items, min_items=0):
    return {'type': 'list', 'item': item, 'max': max_items, 'min': min_items}


def _obj(**fields):
    return {'type': 'obj', 'fields': fields}


SCHEMA = _obj(
    seo=_obj(title=_str(70), description=_str(170)),
    brand=_obj(name=_str(80), short=_str(40)),
    contact=_obj(
        whatsapp=_str(15, kind='whatsapp'),
        phone=_str(25, kind='phone'),
        email=_str(120, required=False, kind='email'),
        address=_str(120),
        city=_str(80),
        maps_url=_str(400, required=False, kind='url'),
        phone_hours=_str(120, required=False),
        hours=_list(_obj(days=_str(40), time=_str(60)), 7),
        hours_note=_str(80, required=False),
    ),
    hero=_obj(
        title=_str(90),
        highlight=_str(90, required=False),
        subtitle=_str(320),
        cta_primary=_str(32),
        cta_secondary=_str(32, required=False),
    ),
    stats=_list(_obj(value=_str(10), label=_str(40)), 4),
    evaluation=_obj(
        title=_str(90),
        subtitle=_str(320),
        steps=_list(_obj(title=_str(60), body=_str(220)), 6, 2),
        whatsapp_message=_str(300),
    ),
    services_intro=_obj(title=_str(90), subtitle=_str(260, required=False)),
    services=_list(
        _obj(title=_str(60), body=_str(400), category=_str(40), image=_str(400, required=False, kind='url')),
        40,
        1,
    ),
    about=_obj(title=_str(90), body=_str(700), values=_list(_obj(title=_str(40), body=_str(200)), 8)),
    testimonials_intro=_obj(title=_str(90), subtitle=_str(260, required=False)),
    testimonials=_list(_obj(quote=_str(500), author=_str(60), relation=_str(60, required=False)), 12),
    faq=_list(_obj(q=_str(160), a=_str(600)), 12),
)

_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_PHONE = re.compile(r'^\+?[\d\s()-]{6,25}$')
_CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _check_str(value, spec, path):
    if value is None:
        value = ''
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ContentError(f'{path}: debe ser texto')
    text = _CONTROL.sub('', str(value)).strip()
    if spec['required'] and not text:
        raise ContentError(f'{path}: es obligatorio')
    if len(text) > spec['max']:
        raise ContentError(f'{path}: máximo {spec["max"]} caracteres (tiene {len(text)})')
    if not text:
        return text
    kind = spec['kind']
    if kind == 'whatsapp':
        text = re.sub(r'\D', '', text)
        if not 8 <= len(text) <= 15:
            raise ContentError(f'{path}: número de WhatsApp con código de país, solo dígitos (ej. 51921507470)')
    elif kind == 'phone' and not _PHONE.match(text):
        raise ContentError(f'{path}: teléfono no válido')
    elif kind == 'email' and not _EMAIL.match(text):
        raise ContentError(f'{path}: correo no válido')
    elif kind == 'url' and not (text.startswith('https://') or (text.startswith('/') and not text.startswith('//'))):
        raise ContentError(f'{path}: el enlace debe empezar por https://')
    return text


def _clean(value, spec, path):
    if spec['type'] == 'str':
        return _check_str(value, spec, path)
    if spec['type'] == 'list':
        if not isinstance(value, list):
            raise ContentError(f'{path}: debe ser una lista')
        if len(value) > spec['max']:
            raise ContentError(f'{path}: máximo {spec["max"]} elementos')
        if len(value) < spec['min']:
            raise ContentError(f'{path}: mínimo {spec["min"]} elementos')
        return [_clean(item, spec['item'], f'{path}[{i + 1}]') for i, item in enumerate(value)]
    if not isinstance(value, dict):
        raise ContentError(f'{path or "contenido"}: formato no válido')
    return {key: _clean(value.get(key), sub, f'{path}.{key}' if path else key) for key, sub in spec['fields'].items()}


def validate(content):
    """Contenido limpio (claves desconocidas fuera, textos recortados) o ContentError con la ruta del campo."""
    return _clean(content, SCHEMA, '')


@lru_cache(maxsize=1)
def _default():
    return validate(json.loads(DEFAULT_PATH.read_text(encoding='utf-8')))


def default_content():
    return copy.deepcopy(_default())


def current_version():
    return LandingContentVersion.query.order_by(LandingContentVersion.id.desc()).first()


def current_content():
    """La última versión publicada; si nunca se publicó, el contenido por defecto (el del sitio anterior)."""
    row = current_version()
    if row is None:
        return default_content(), None
    try:
        return validate(row.content), row
    except ContentError:
        # Una versión guardada con un esquema anterior no debe tumbar el sitio público.
        return default_content(), row


def publish(content, user_id, note=None):
    clean = validate(content)
    row = LandingContentVersion(content=clean, created_by=user_id, note=(note or '').strip()[:200] or None)
    db.session.add(row)
    db.session.commit()
    return row
