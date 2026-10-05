"""Login por chat: el usuario autenticado en la web genera un codigo de un solo
uso (POST /api/telegram/login-code) y escribe /login CODIGO en Telegram. El chat
queda ligado a SU User y el rol se resuelve siempre desde la BD."""

import random
import uuid
from datetime import datetime, timedelta

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
    return sent


def _user(session, role='terapista', **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'u{tag}', email=f'{tag}@login.test', password='x', role=role, **kw)
    session.add(u)
    session.commit()
    return u


def _issue(client, user):
    token = create_access_token(identity=str(user.id))
    return client.post('/api/telegram/login-code', headers={'Authorization': f'Bearer {token}'})


def _say(chat_id, text):
    tb.handle_webhook_update(
        {'message': {'chat': {'id': chat_id}, 'from': {'id': chat_id, 'first_name': 'Ana'}, 'text': text}}
    )


def _chat():
    return random.randint(10**10, 10**11)


def _row(chat_id):
    db.session.expire_all()
    return TelegramUser.query.filter_by(telegram_chat_id=chat_id).first()


@pytest.mark.parametrize('role', ['admin', 'supervisor', 'terapista', 'jugador'])
def test_any_authenticated_role_can_issue_a_code(client, session, role):
    r = _issue(client, _user(session, role))
    assert r.status_code == 200
    code = r.get_json()['code']
    assert len(code) == 8 and code == code.upper()


def test_issue_requires_authentication(client):
    assert client.post('/api/telegram/login-code').status_code in (401, 403, 422)


def test_inactive_user_cannot_issue(client, session):
    assert _issue(client, _user(session, is_active=False)).status_code in (401, 403)


def test_code_is_stored_hashed(client, session):
    user = _user(session)
    code = _issue(client, user).get_json()['code']
    stored = ChatLoginCode.query.filter_by(user_id=user.id).all()
    assert stored and all(code not in (s.code_hash or '') for s in stored)


def test_new_code_invalidates_previous(client, session, bot):
    user = _user(session)
    first = _issue(client, user).get_json()['code']
    _issue(client, user)
    chat = _chat()
    _say(chat, f'/login {first}')
    assert not (_row(chat) and _row(chat).is_linked)


def test_login_links_chat_to_the_right_user_and_role(client, session, bot):
    user = _user(session, 'jugador')
    code = _issue(client, user).get_json()['code']
    chat = _chat()
    _say(chat, f'/login {code}')
    row = _row(chat)
    assert row.is_linked and row.admin_user_id == user.id
    assert tb._real_role_for(row.admin_user_id) == 'jugador'
    assert 'paciente' in bot[-1][1].lower()


def test_code_is_single_use(client, session, bot):
    user = _user(session)
    code = _issue(client, user).get_json()['code']
    a, b = _chat(), _chat()
    _say(a, f'/login {code}')
    _say(b, f'/login {code}')
    assert _row(a).is_linked
    assert not (_row(b) and _row(b).is_linked)


def test_expired_code_rejected(client, session, bot):
    user = _user(session)
    code = _issue(client, user).get_json()['code']
    ChatLoginCode.query.filter_by(user_id=user.id).update({'expires_at': datetime.utcnow() - timedelta(seconds=1)})
    session.commit()
    chat = _chat()
    _say(chat, f'/login {code}')
    assert not (_row(chat) and _row(chat).is_linked)


def test_wrong_codes_lock_the_chat_out(client, session, bot):
    user = _user(session)
    code = _issue(client, user).get_json()['code']
    chat = _chat()
    for _ in range(tb._LOGIN_MAX_FAILURES):
        _say(chat, '/login ZZZZZZZZ')
    _say(chat, f'/login {code}')  # el correcto, pero el chat ya esta bloqueado
    assert not (_row(chat) and _row(chat).is_linked)


def test_user_deactivated_after_issue_cannot_login(client, session, bot):
    user = _user(session)
    code = _issue(client, user).get_json()['code']
    user.is_active = False
    session.commit()
    chat = _chat()
    _say(chat, f'/login {code}')
    assert not (_row(chat) and _row(chat).is_linked)


def test_chat_linked_to_other_user_must_unlink_first(client, session, bot):
    u1, u2 = _user(session), _user(session)
    chat = _chat()
    _say(chat, f'/login {_issue(client, u1).get_json()["code"]}')
    _say(chat, f'/login {_issue(client, u2).get_json()["code"]}')
    assert _row(chat).admin_user_id == u1.id


def test_confirmation_uses_current_role_not_stored_one(session, bot, monkeypatch):
    """Si el rol baja (o el usuario se desactiva) tras pedir la confirmacion, la
    operacion pendiente se ejecuta con el rol ACTUAL."""
    user = _user(session, 'admin')
    chat = _chat()
    seen = {}

    class FakeMCP:
        def process_message(self, **kw):
            seen.update(kw)
            return {'response': 'ok'}

    monkeypatch.setattr('app.services.mcp_service.MCPService', FakeMCP)
    db.session.add(TelegramUser(telegram_chat_id=chat, admin_user_id=user.id, is_linked=True))
    session.commit()
    tb._store_pending_confirmation(chat, {'user_id': user.id, 'user_role': 'admin', 'mode': 'grande', 'data': {}})
    user.role = 'jugador'
    session.commit()
    tb.confirm_pending_operation(chat, True)
    assert seen['user_role'] == 'jugador'
