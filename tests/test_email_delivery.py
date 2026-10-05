"""Entrega de correos: HTML en su parte correcta (con alternativa de texto),
cabeceras de correo automatico + baja con un clic (para que Gmail lo trate como
notificacion), y limites de frecuencia persistentes (mensajes de chat y SLA)."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import User
from app.models.email_throttle import EmailThrottle
from app.models.notification import UserNotificationPreference
from app.services import email_service as es
from app.services.email_service import EmailService
from app.utils.email_tokens import make_unsubscribe_token, read_unsubscribe_token


@pytest.fixture
def sent(app, monkeypatch):
    box = []
    app.config.update(MAIL_USERNAME='robot@test.local', MAIL_PASSWORD='x', MAIL_DEFAULT_SENDER=None)
    monkeypatch.setattr(es.mail, 'send', lambda msg: box.append(msg))
    return box


def _user(session, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'u{tag}', email=f'{tag}@mail.test', password='x', role='terapista', **kw)
    session.add(u)
    session.commit()
    return u


# ---------------------------------------------------------------- formato
def test_html_goes_in_html_part_with_plain_alternative(sent):
    EmailService.send_notification_email('Asunto', ['a@b.c'], 'texto plano', html='<p>Hola <b>mundo</b></p>')
    msg = sent[0]
    assert msg.html == '<p>Hola <b>mundo</b></p>'
    assert msg.body == 'texto plano'


def test_plain_alternative_is_derived_when_missing(sent):
    EmailService.send_notification_email('Asunto', ['a@b.c'], None, html='<h1>Resumen</h1><p>Hay <b>4</b> citas</p>')
    assert '<' not in sent[0].body and 'Resumen' in sent[0].body and 'Hay 4 citas' in sent[0].body


def test_text_only_message_unchanged(sent):
    EmailService.send_notification_email('Asunto', ['a@b.c'], 'solo texto')
    assert sent[0].html is None and sent[0].body == 'solo texto'


# ------------------------------------------------------------- cabeceras
def test_automation_headers_and_sender_name(sent):
    EmailService.send_notification_email('Asunto', ['a@b.c'], 'x')
    msg = sent[0]
    assert msg.extra_headers['Auto-Submitted'] == 'auto-generated'
    assert 'AutoReply' in msg.extra_headers['X-Auto-Response-Suppress']
    assert msg.sender == 'Centro Juan Pablo II · Notificaciones <robot@test.local>'


def test_unsubscribe_headers_when_user_is_known(sent, session):
    user = _user(session)
    EmailService.send_notification_email('Asunto', [user.email], 'x', user_id=user.id)
    headers = sent[0].extra_headers
    assert (
        headers['List-Unsubscribe'].startswith('<https://')
        and '/api/public/email/unsubscribe?t=' in headers['List-Unsubscribe']
    )
    assert headers['List-Unsubscribe-Post'] == 'List-Unsubscribe=One-Click'
    token = headers['List-Unsubscribe'].split('t=')[1].rstrip('>')
    assert read_unsubscribe_token(token) == user.id


def test_no_unsubscribe_headers_without_user(sent):
    EmailService.send_notification_email('Asunto', ['a@b.c'], 'x')
    assert 'List-Unsubscribe' not in sent[0].extra_headers


# ----------------------------------------------------------------- tokens
def test_token_roundtrip_tamper_and_expiry(app):
    token = make_unsubscribe_token(42)
    assert read_unsubscribe_token(token) == 42
    assert read_unsubscribe_token(token + 'x') is None
    assert read_unsubscribe_token('') is None
    assert read_unsubscribe_token(token, max_age=-1) is None


# --------------------------------------------------------------- endpoint
def test_post_unsubscribes_from_digest(client, session):
    user = _user(session)
    token = make_unsubscribe_token(user.id)
    r = client.post(f'/api/public/email/unsubscribe?t={token}', data='List-Unsubscribe=One-Click')
    assert r.status_code == 200
    db.session.expire_all()
    assert UserNotificationPreference.query.filter_by(user_id=user.id).one().digest_enabled is False


def test_get_shows_confirmation_and_changes_nothing(client, session):
    user = _user(session)
    r = client.get(f'/api/public/email/unsubscribe?t={make_unsubscribe_token(user.id)}')
    assert r.status_code == 200 and b'<form' in r.data
    assert UserNotificationPreference.query.filter_by(user_id=user.id).first() is None


def test_invalid_token_rejected(client):
    assert client.post('/api/public/email/unsubscribe?t=basura').status_code == 400
    assert client.get('/api/public/email/unsubscribe').status_code == 400


# ---------------------------------------------------------------- throttle
def test_throttle_allows_once_per_cooldown(app):
    key = f'k-{uuid.uuid4().hex}'
    assert EmailThrottle.allow(key, 30) is True
    assert EmailThrottle.allow(key, 30) is False
    assert EmailThrottle.allow(f'otra-{key}', 30) is True
    EmailThrottle.query.filter_by(key=key).update({'last_sent_at': datetime.utcnow() - timedelta(minutes=31)})
    db.session.commit()
    assert EmailThrottle.allow(key, 30) is True


def test_chat_message_emails_are_throttled_per_conversation(sent):
    rcpt = f'{uuid.uuid4().hex[:6]}@mail.test'
    for _ in range(5):
        EmailService.send_new_message_email(rcpt, 'Ana', 'Beto', 'hola')
    assert len(sent) == 1
    EmailService.send_new_message_email(rcpt, 'Ana', 'Carla', 'hola')  # otra conversacion
    assert len(sent) == 2


# ----------------------------------------------------------- SLA vencidos
def test_sla_breach_is_notified_once_per_window(session, monkeypatch):
    from app.models.incidente import Incidente
    from app.services.incident_detection_service import IncidentDetectionService
    from app.services.incident_notification_service import IncidentNotificationService

    user = _user(session)
    now = datetime.utcnow()
    inc = Incidente(
        titulo=f'SLA {uuid.uuid4().hex[:6]}',
        descripcion='x',
        categoria='OPERACIONES',
        prioridad=2,
        estado='NUEVO',
        user_id=user.id,
        evidencia_tipo='EVALUATION',
        evidencia_original='x',
        fecha_creacion=now - timedelta(hours=3),
        fecha_limite_sla=now - timedelta(hours=1),
    )
    db.session.add(inc)
    db.session.commit()

    calls = []
    monkeypatch.setattr(
        IncidentNotificationService,
        'notify_sla_breach_grouped',
        classmethod(lambda c, items: calls.append([i.id_incidente for i in items])),
    )
    for _ in range(4):  # el job corre cada 15 min
        IncidentDetectionService._check_expired_slas()
    assert sum(inc.id_incidente in call for call in calls) == 1


# ------------------------------------------------- resumen diario / reportes
def test_digest_sends_html_in_html_part(monkeypatch, session):
    from app.services import daily_digest_service as dd

    user = _user(session)
    seen = {}
    monkeypatch.setattr(EmailService, 'send_notification_email', staticmethod(lambda **kw: seen.update(kw)))
    dd._send_email_digest(user, '<p>html</p>')
    assert seen['html'] == '<p>html</p>' and seen.get('body') is None and seen['user_id'] == user.id


def test_message_serializes_with_non_ascii_sender_and_both_parts(sent, session):
    """Lo que realmente sale por SMTP: nombre con '·', multipart text+html y cabeceras."""
    from email import message_from_bytes
    from email.header import decode_header, make_header

    user = _user(session)
    EmailService.send_notification_email(
        'Resumen Diario — Centro', [user.email], None, html='<p>Hola <b>mundo</b></p>', user_id=user.id
    )
    parsed = message_from_bytes(sent[0].as_bytes())
    alternative = next(p for p in parsed.walk() if p.get_content_type() == 'multipart/alternative')
    assert [p.get_content_type() for p in alternative.get_payload()] == ['text/plain', 'text/html']
    assert 'Notificaciones' in str(make_header(decode_header(parsed['From'])))
    assert parsed['Auto-Submitted'] == 'auto-generated' and parsed['List-Unsubscribe-Post']
