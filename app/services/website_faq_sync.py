"""Sincroniza las FAQ del bot con el contenido público de centrojuanpabloii.com.

La web es una SPA (React/Vite): no tiene una sección de preguntas frecuentes, el contenido vive dentro
del bundle JS. Se descarga la página, se localiza el bundle (mismo dominio) y se extraen con anclas
conocidas la misión, visión, datos de contacto, horarios y terapias. Es idempotente: cada FAQ se
identifica por su pregunta y se actualiza la respuesta si la web cambió.
"""

import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests

from app.extensions import db
from app.models.faq import Faq
from app.models.system_setting import SystemSetting
from app.services import live_sync

logger = logging.getLogger(__name__)

DEFAULT_URL = 'https://centrojuanpabloii.com'
URL_KEY = 'faq.website_url'
STATUS_KEY = 'faq.website_status'
MAX_BYTES = 3_000_000
TIMEOUT = 15
SOURCE = 'website'
CATEGORY = 'centro'

_STR = r'"((?:[^"\\]|\\.)*)"'


def _setting(key, default=''):
    row = db.session.get(SystemSetting, key)
    return row.value if row is not None and row.value is not None else default


def _put(key, value):
    row = db.session.get(SystemSetting, key)
    if row is None:
        db.session.add(SystemSetting(key=key, value=value))
    else:
        row.value = value


def get_url():
    return _setting(URL_KEY, DEFAULT_URL) or DEFAULT_URL


def set_url(url):
    parsed = urlparse((url or '').strip())
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('La dirección debe empezar con http:// o https://')
    _put(URL_KEY, f'{parsed.scheme}://{parsed.netloc}')
    db.session.commit()


def status():
    import json

    try:
        data = json.loads(_setting(STATUS_KEY, '{}') or '{}')
    except ValueError:
        data = {}
    data['url'] = get_url()
    return data


def _fetch(url, kind):
    resp = requests.get(url, timeout=TIMEOUT, stream=True, headers={'User-Agent': 'ChasquiFAQSync/1.0'})
    resp.raise_for_status()
    chunks, size = [], 0
    for chunk in resp.iter_content(65536):
        size += len(chunk)
        if size > MAX_BYTES:
            raise ValueError(f'{kind} demasiado grande')
        chunks.append(chunk)
    return b''.join(chunks).decode('utf-8', errors='ignore')


def _bundles(html, base):
    host = urlparse(base).hostname
    found = []
    for src in re.findall(r'<script[^>]+src="([^"]+\.js)"', html):
        full = urljoin(base + '/', src)
        if urlparse(full).hostname == host:  # nunca se sigue un script de otro dominio
            found.append(full)
    return found


def _text(raw):
    return re.sub(
        r'\s+', ' ', raw.encode('utf-8').decode('unicode_escape', errors='ignore') if '\\u' in raw else raw
    ).strip()


def extract(js):
    """Devuelve [(pregunta, respuesta, palabras_clave)] a partir del bundle."""
    items = []

    def paragraph_after(title):
        m = re.search(
            re.escape(title)
            + r'.{0,400}?children:'
            + _STR
            + r'\}\)\,?\s*h\.jsx\("p",\{className:"[^"]*",children:'
            + _STR,
            js,
            re.S,
        )
        if m:
            return _text(m.group(2))
        m = re.search(re.escape(title) + r'.{0,700}?leading-relaxed[^"]*",children:' + _STR, js, re.S)
        return _text(m.group(1)) if m else ''

    for title, question, kw in (
        ('Nuestra Misión', '¿Cuál es la misión del centro?', 'misión mision objetivo propósito'),
        ('Nuestra Visión', '¿Cuál es la visión del centro?', 'visión vision futuro'),
    ):
        text = paragraph_after(title)
        if len(text) > 40:
            items.append((question, text, kw))

    contact = {}
    for m in re.finditer(
        r'title:"(Teléfono|Correo Electrónico|Ubicación|Horario)",content:(?:"((?:[^"\\]|\\.)*)"|`([^`]*)`)(?:,description:(?:"((?:[^"\\]|\\.)*)"|`([^`]*)`))?',
        js,
    ):
        contact[m.group(1)] = (_text(m.group(2) or m.group(3) or ''), _text(m.group(4) or m.group(5) or ''))

    if 'Teléfono' in contact:
        phone, hours = contact['Teléfono']
        items.append(
            (
                '¿Cuál es el teléfono del centro?',
                f'Puedes llamarnos o escribirnos al {phone}. Atendemos {hours}.',
                'teléfono telefono celular llamar contacto número numero',
            )
        )
    if 'Correo Electrónico' in contact:
        mail, note = contact['Correo Electrónico']
        items.append(
            ('¿Cuál es el correo del centro?', f'Escríbenos a {mail}. {note}.', 'correo email mail e-mail escribir')
        )
    if 'Ubicación' in contact:
        place, city = contact['Ubicación']
        items.append(
            (
                '¿Dónde está ubicado el centro?',
                f'Estamos en {place.strip()}, {city}.',
                'ubicación ubicacion dirección direccion donde queda llegar local',
            )
        )
    if 'Horario' in contact:
        week, sat = contact['Horario']
        items.append(
            (
                '¿Cuál es el horario de atención?',
                f'{week.strip()}. {sat.strip()}.',
                'horario atención atencion hora abren cierran días dias sábado',
            )
        )

    therapies = re.findall(r'label:"(Terapia[^"]{2,40}|Habilidades Sociales)"', js)
    unique = list(dict.fromkeys(therapies))
    if unique:
        items.append(
            (
                '¿Qué terapias ofrece el centro?',
                'Ofrecemos: ' + ', '.join(unique) + '. Escríbenos para una evaluación inicial.',
                'terapias servicios especialidades ofrecen tratamientos lenguaje conductual tea down aprendizaje',
            )
        )

    stats = re.search(
        r'value:"(\d+\+?)",label:"Años de Experiencia".{0,200}?value:"(\d+\+?)",label:"Pacientes Atendidos"', js, re.S
    )
    if stats:
        items.append(
            (
                '¿Cuánta experiencia tiene el centro?',
                f'Tenemos más de {stats.group(1).rstrip("+")} años de experiencia y hemos atendido a más de {stats.group(2).rstrip("+")} pacientes.',
                'experiencia años trayectoria pacientes atendidos',
            )
        )
    return items


def sync(url=None):
    """Descarga la web y actualiza las FAQ. Devuelve un resumen; nunca lanza."""
    import json

    base = (url or get_url()).rstrip('/')
    summary = {'ok': False, 'created': 0, 'updated': 0, 'total': 0, 'at': datetime.utcnow().isoformat(), 'error': None}
    try:
        html = _fetch(base, 'La página')
        items = []
        for bundle in _bundles(html, base)[:4]:
            items = extract(_fetch(bundle, 'El script'))
            if items:
                break
        if not items:
            raise ValueError('No se encontró contenido reconocible en la web (¿cambió su diseño?)')
        for question, answer, keywords in items:
            faq = Faq.query.filter_by(source=SOURCE, question=question).first()
            if faq is None:
                db.session.add(
                    Faq(
                        question=question,
                        answer=answer,
                        category=CATEGORY,
                        keywords=keywords,
                        is_active=True,
                        source=SOURCE,
                        status='active',
                    )
                )
                summary['created'] += 1
            elif faq.answer != answer:
                faq.answer = answer
                summary['updated'] += 1
        summary.update(ok=True, total=len(items))
        if summary['created'] or summary['updated']:
            live_sync.bump('faq')
    except Exception as exc:
        db.session.rollback()
        logger.warning('Sincronización de FAQ desde la web falló: %s', exc)
        summary['error'] = str(exc)[:200]
    _put(STATUS_KEY, json.dumps(summary))
    db.session.commit()
    return summary
