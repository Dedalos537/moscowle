"""Enlace directo al bot: https://t.me/<bot>?start=login_<CODIGO> hace que Telegram
envie '/start login_<CODIGO>' al pulsar START, y eso inicia sesion (un toque en vez
de copiar y escribir el comando). El nombre del bot sale de getMe, con cache."""

import random
import uuid

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.chat_login_code import ChatLoginCode
from app.models.telegram_user import TelegramUser
from app.services import telegram_bot_service as tb


@pytest.fixture
def bot(app, monkeypatch):
    sent = []
    app.config['TELEGRAM_BOT_TOKEN'] = 'test-token'
    monkeypatch.setattr(tb, 'send_telegram_message', lambda chat_id, text, *a, **k: sent.append((chat_id, text)))
    monkeypatch.setattr(tb, 'send_typing_action', lambda *a, **k: None)
    monkeypatch.setattr(tb, '_bot_enabled', lambda: True)
    tb._LOGIN_FAILURES.clear()
    tb._BOT_USERNAME_CACHE.update(value=None, at=0.0)
    return sent


def _user(session, role='terapista'):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'u{tag}', email=f'{tag}@dl.test', password='x', role=role)
    session.add(u)
    session.commit()
    return u


def _say(chat_id, text):
    tb.handle_webhook_update(
        {'message': {'chat': {'id': chat_id}, 'from': {'id': chat_id, 'first_name': 'Ana'}, 'text': text}}
    )


def _chat():
    return random.randint(10**10, 10**11)


def _row(chat_id):
    db.session.expire_all()
    return TelegramUser.query.filter_by(telegram_chat_id=chat_id).first()


def test_start_with_login_payload_signs_in(session, bot):
    user = _user(session)
    code = ChatLoginCode.issue(user.id)
    chat = _chat()
    _say(chat, f'/start login_{code}')
    row = _row(chat)
    assert row and row.is_linked and row.admin_user_id == user.id
    assert 'Sesión iniciada' in bot[-1][1]


def test_start_with_bad_payload_does_not_link_and_counts_failure(session, bot):
    chat = _chat()
    _say(chat, '/start login_ZZZZZZZZ')
    assert not (_row(chat) and _row(chat).is_linked)
    assert tb._LOGIN_FAILURES[chat][0] == 1


def test_start_payload_obeys_the_lockout(session, bot):
    user = _user(session)
    code = ChatLoginCode.issue(user.id)
    chat = _chat()
    for _ in range(tb._LOGIN_MAX_FAILURES):
        _say(chat, '/start login_ZZZZZZZZ')
    _say(chat, f'/start login_{code}')
    assert not (_row(chat) and _row(chat).is_linked)


def test_plain_start_unchanged(session, bot):
    chat = _chat()
    _say(chat, '/start')
    assert _row(chat) is not None and not _row(chat).is_linked
    assert '/login' in bot[-1][1]


def test_non_login_start_payload_is_ignored_as_plain_start(session, bot):
    chat = _chat()
    _say(chat, '/start otra_cosa')
    assert not (_row(chat) and _row(chat).is_linked)


def test_bot_username_is_fetched_once_and_cached(bot, monkeypatch):
    calls = []

    def fake(method, data=None, bot_token=None):
        calls.append(method)
        return {'ok': True, 'result': {'username': 'MoscowleBot'}}

    monkeypatch.setattr(tb, '_tg_request', fake)
    assert tb.get_bot_username() == 'MoscowleBot'
    assert tb.get_bot_username() == 'MoscowleBot'
    assert calls == ['getMe']


def test_bot_username_none_when_telegram_fails(bot, monkeypatch):
    monkeypatch.setattr(tb, '_tg_request', lambda *a, **k: {'ok': False})
    assert tb.get_bot_username() is None


def test_me_endpoint_exposes_bot_username(client, session, bot, monkeypatch):
    monkeypatch.setattr(tb, 'get_bot_username', lambda: 'MoscowleBot')
    user = _user(session)
    token = create_access_token(identity=str(user.id))
    body = client.get('/api/telegram/me', headers={'Authorization': f'Bearer {token}'}).get_json()
    assert body['bot_username'] == 'MoscowleBot'
