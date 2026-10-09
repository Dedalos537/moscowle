"""Adjuntos del chat: todo lo que se puede enviar también se puede abrir, sin tipos peligrosos ni nombres perdidos."""

import io
import uuid
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.services import attachments


def _user(role='admin'):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@chat.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def chat(app, client, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    me, other = _user('admin'), _user('terapista')
    h = {'Authorization': 'Bearer ' + create_access_token(identity=str(me.id))}
    cid = client.post('/api/chats', json={'user_id': other.id}, headers=h).get_json()['chat_id']

    def send(name, content=b'contenido', mime='application/octet-stream'):
        data = {'file': (io.BytesIO(content), name, mime)}
        return client.post(f'/api/chats/{cid}/messages', data=data, headers=h, content_type='multipart/form-data')

    return send, h


@pytest.mark.parametrize(
    'name,mime,kind',
    [
        ('Presentación.pptx', 'application/vnd.ms-powerpoint', 'file'),
        ('foto.heic', 'image/heic', 'image'),
        ('video.3gp', 'video/3gpp', 'video'),
        ('nota.opus', 'audio/ogg', 'audio'),
        ('clip.webm', 'video/webm', 'video'),
        ('nota.webm', 'audio/webm', 'audio'),
        ('lista.csv', 'text/csv', 'file'),
    ],
)
def test_every_sent_type_can_be_opened(client, chat, name, mime, kind):
    send, h = chat
    r = send(name, mime=mime)
    assert r.status_code == 200, r.get_json()
    msg = r.get_json()['message']
    assert msg['attachment_type'] == kind
    assert msg['file_name'] == name.replace(' ', '_')
    got = client.get(msg['file_url'], headers=h)
    assert got.status_code == 200 and got.data == b'contenido'
    assert got.headers['X-Content-Type-Options'] == 'nosniff'


@pytest.mark.parametrize('name', ['virus.exe', 'pagina.html', 'logo.svg', 'script.js', 'sin_extension'])
def test_dangerous_or_unknown_types_are_rejected(chat, name):
    send, _h = chat
    r = send(name)
    assert r.status_code == 400 and 'No se pueden enviar' in r.get_json()['message']


def test_documents_download_instead_of_opening_inline(client, chat):
    send, h = chat
    msg = send('Informe año 2026.docx').get_json()['message']
    got = client.get(msg['file_url'], headers=h)
    assert 'attachment' in got.headers['Content-Disposition']
    assert 'Informe_a' in got.headers['Content-Disposition']  # conserva el nombre original (con ñ codificada)


def test_size_limit_and_empty_file(chat):
    send, _h = chat
    with patch.object(attachments, 'MAX_BYTES', 10):
        r = send('grande.pdf', content=b'x' * 50)
    assert r.status_code == 400 and 'pesa más' in r.get_json()['message']
    assert send('vacio.pdf', content=b'').status_code == 400


def test_errors_do_not_leak_tracebacks(client, chat):
    _send, h = chat
    with patch('app.routes.chat_routes.sanitize_text', side_effect=RuntimeError('boom')):
        r = client.post('/api/chats/999999/messages', json={'body': 'x'}, headers=h)
    assert 'traceback' not in (r.get_json() or {})


def test_debug_endpoints_are_closed(client, app):
    assert client.get('/api/health/debug/run-sql?key=debug2026').status_code == 404
    assert client.get('/api/health/debug/last-error?key=debug2026').status_code == 404


def test_clean_name_keeps_accents_and_strips_paths():
    assert attachments.clean_name('../../etc/Niño pequeño.PDF') == 'Niño_pequeño.PDF'
    assert attachments.display_name('0123456789abcdef0123456789abcdef_Niño.pdf') == 'Niño.pdf'
