"""Chasqui: lo que se configura en el panel debe cambiar el comportamiento real del bot.

Antes `persona_message`, `notify_supervision_enabled` e `intervention_enabled` se guardaban y se mostraban,
pero nada los leía; y el nombre/emoji de varios mensajes salían de constantes fijas ('Diego').
"""

import uuid

import pytest
from flask_jwt_extended import create_access_token

import app.services.telegram_bot_service as tbs
from app.extensions import db
from app.models import User
from app.models.bot_config import BotConfig
from app.models.notification_group import NotificationGroup


def _headers(user):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}


@pytest.fixture
def admin(session):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'adm{tag}', email=f'{tag}@bot.test', password='x', role='admin')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def cfg(app):
    c = BotConfig.get_or_create()
    saved = {
        k: getattr(c, k)
        for k in ('bot_name', 'bot_emoji', 'persona_message', 'notify_supervision_enabled', 'intervention_enabled')
    }
    yield c
    for k, v in saved.items():
        setattr(c, k, v)
    db.session.commit()


@pytest.fixture
def sent(monkeypatch):
    messages = []
    monkeypatch.setattr(tbs, 'send_telegram_message', lambda chat_id, text, *a, **k: messages.append(text) or True)
    return messages


# ───────────────────────────── identidad y presentación
def test_start_uses_configured_name_emoji_and_persona(app, cfg, sent):
    cfg.bot_name, cfg.bot_emoji, cfg.persona_message = 'Chasqui', '🏃', 'Soy el mensajero del centro.'
    db.session.commit()
    tbs._handle_start(990001, {'id': 990001, 'username': 'x', 'first_name': 'X'}, None, 'tok')
    text = sent[-1]
    assert 'Chasqui' in text and '🏃' in text and 'Soy el mensajero del centro.' in text
    assert 'Diego' not in text and 'Soy tu asistente inteligente' not in text


def test_start_falls_back_to_default_intro_without_persona(app, cfg, sent):
    cfg.persona_message = ''
    db.session.commit()
    tbs._handle_start(990002, {'id': 990002}, None, 'tok')
    assert 'Soy tu asistente inteligente' in sent[-1]


def test_help_status_and_menu_use_configured_identity(app, cfg, sent):
    cfg.bot_name, cfg.bot_emoji = 'Chasqui', '🏃'
    db.session.commit()
    tbs._handle_help(990003, 'tok')
    assert 'Chasqui' in sent[-1] and 'Diego' not in sent[-1]


# ───────────────────────────── aviso a supervisión
def _unanswered(text):
    tbs._note_if_unanswered({'response': 'no sé'}, text)


def _groups(admin):
    return NotificationGroup.query.filter_by(user_id=admin.id, group_key='bot_unanswered:bot').count()


def test_supervision_is_notified_when_enabled(app, cfg, admin):
    cfg.notify_supervision_enabled = True
    db.session.commit()
    before = NotificationGroup.query.filter(NotificationGroup.user_id == admin.id).count()
    _unanswered('¿cuánto cuesta una terapia grupal en la sede norte?')
    after = NotificationGroup.query.filter(NotificationGroup.user_id == admin.id).count()
    assert after == before + 1


def test_supervision_is_not_notified_when_disabled(app, cfg, admin):
    cfg.notify_supervision_enabled = False
    db.session.commit()
    before = NotificationGroup.query.filter(NotificationGroup.user_id == admin.id).count()
    _unanswered('otra pregunta sin respuesta')
    assert NotificationGroup.query.filter(NotificationGroup.user_id == admin.id).count() == before


# ───────────────────────────── intervención y validación
def test_reply_is_blocked_when_intervention_disabled(client, cfg, admin, monkeypatch):
    cfg.intervention_enabled = False
    db.session.commit()
    monkeypatch.setattr(tbs, 'send_telegram_message', lambda *a, **k: True)
    r = client.post('/api/telegram/reply', json={'chat_id': 1, 'text': 'hola'}, headers=_headers(admin))
    assert r.status_code == 403


def test_reply_works_when_intervention_enabled(client, cfg, admin, monkeypatch):
    cfg.intervention_enabled = True
    db.session.commit()
    monkeypatch.setattr(tbs, 'send_telegram_message', lambda *a, **k: True)
    r = client.post('/api/telegram/reply', json={'chat_id': 1, 'text': 'hola'}, headers=_headers(admin))
    assert r.status_code == 200


def test_config_validates_input(client, cfg, admin):
    h = _headers(admin)
    assert client.put('/api/telegram/config', json={'bot_name': '   '}, headers=h).status_code == 400
    assert client.put('/api/telegram/config', json={'persona_message': 'x' * 1001}, headers=h).status_code == 400
    ok = client.put('/api/telegram/config', json={'bot_name': ' Chasqui ', 'bot_emoji': '🏃'}, headers=h)
    assert ok.status_code == 200 and ok.get_json()['config']['bot_name'] == 'Chasqui'
