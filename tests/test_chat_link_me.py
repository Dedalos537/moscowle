"""Estado y desvinculacion del chat PROPIO, para cualquier rol autenticado.
GET /api/telegram/me y POST /api/telegram/me/unlink: nunca tocan chats ajenos."""

import random
import uuid

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.telegram_user import TelegramUser


def _user(session, role='terapista', **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'u{tag}', email=f'{tag}@me.test', password='x', role=role, **kw)
    session.add(u)
    session.commit()
    return u


def _link(user, **kw):
    row = TelegramUser(
        telegram_chat_id=random.randint(10**11, 10**12),
        admin_user_id=user.id,
        is_linked=True,
        telegram_username=kw.get('username', 'ana_tg'),
        telegram_first_name='Ana',
    )
    db.session.add(row)
    db.session.commit()
    return row


def _call(client, user, method, path, **kw):
    token = create_access_token(identity=str(user.id))
    return getattr(client, method)(path, headers={'Authorization': f'Bearer {token}'}, **kw)


def test_me_requires_auth(client):
    assert client.get('/api/telegram/me').status_code in (401, 403, 422)


@pytest.mark.parametrize('role', ['admin', 'supervisor', 'terapista', 'jugador'])
def test_me_not_linked_for_every_role(client, session, role):
    r = _call(client, _user(session, role), 'get', '/api/telegram/me')
    assert r.status_code == 200
    body = r.get_json()
    assert body['linked'] is False and body['accounts'] == [] and body['role'] == role


def test_me_lists_only_own_accounts(client, session):
    mine, other = _user(session), _user(session)
    row = _link(mine)
    _link(other, username='ajeno')
    body = _call(client, mine, 'get', '/api/telegram/me').get_json()
    assert body['linked'] is True
    assert [a['chat_id'] for a in body['accounts']] == [row.telegram_chat_id]
    assert body['accounts'][0]['username'] == 'ana_tg'
    assert 'link_code' not in body['accounts'][0]


def test_unlink_own_chat(client, session):
    user = _user(session)
    row = _link(user)
    r = _call(client, user, 'post', '/api/telegram/me/unlink', json={'chat_id': row.telegram_chat_id})
    assert r.status_code == 200
    db.session.expire_all()
    fresh = TelegramUser.query.get(row.id)
    assert fresh.is_linked is False and fresh.admin_user_id is None


def test_cannot_unlink_someone_elses_chat(client, session):
    mine, victim = _user(session), _user(session)
    row = _link(victim)
    r = _call(client, mine, 'post', '/api/telegram/me/unlink', json={'chat_id': row.telegram_chat_id})
    assert r.status_code == 404
    db.session.expire_all()
    assert TelegramUser.query.get(row.id).is_linked is True


def test_unlink_requires_chat_id(client, session):
    assert _call(client, _user(session), 'post', '/api/telegram/me/unlink', json={}).status_code == 400
