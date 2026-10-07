"""Notificaciones por Telegram: el interruptor de cada usuario funciona, solo afecta sus cuentas y define qué se reenvía."""

import uuid

import pytest
from flask_jwt_extended import create_access_token

import app.services.telegram_bot_service as tbs
from app.extensions import db
from app.models import User
from app.models.telegram_user import TelegramUser
from app.services.notification_service import NotificationService


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@tgn.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def _link(user, enabled=True):
    chat = int(uuid.uuid4().int % 10**9) + 5 * 10**9
    t = TelegramUser(
        telegram_chat_id=chat,
        telegram_user_id=chat,
        telegram_first_name='Ana',
        is_linked=True,
        is_active=True,
        admin_user_id=user.id,
        notifications_enabled=enabled,
    )
    db.session.add(t)
    db.session.commit()
    return t


def _h(user):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}


@pytest.fixture
def sent(app, monkeypatch):
    app.config['TELEGRAM_BOT_TOKEN'] = 'tok'
    out = []
    monkeypatch.setattr(
        tbs, '_tg_request', lambda m, d=None, t=None: out.append(d) or {'result': {'message_id': len(out)}}
    )
    yield out
    app.config.pop('TELEGRAM_BOT_TOKEN', None)


def test_any_role_can_toggle_its_own_accounts(client):
    patient = _user('jugador')
    a, b = _link(patient), _link(patient)
    r = client.post('/api/telegram/notifications/toggle', json={'enabled': False}, headers=_h(patient))
    assert r.status_code == 200
    db.session.expire_all()
    assert (
        not TelegramUser.query.get(a.id).notifications_enabled
        and not TelegramUser.query.get(b.id).notifications_enabled
    )
    # una sola cuenta
    client.post(
        '/api/telegram/notifications/toggle',
        json={'enabled': True, 'telegram_chat_id': a.telegram_chat_id},
        headers=_h(patient),
    )
    db.session.expire_all()
    assert TelegramUser.query.get(a.id).notifications_enabled and not TelegramUser.query.get(b.id).notifications_enabled


def test_cannot_touch_someone_elses_account(client):
    owner, intruder = _user('terapista'), _user('terapista')
    acc = _link(owner)
    r = client.post(
        '/api/telegram/notifications/toggle',
        json={'enabled': False, 'telegram_chat_id': acc.telegram_chat_id},
        headers=_h(intruder),
    )
    assert r.status_code == 404
    db.session.expire_all()
    assert TelegramUser.query.get(acc.id).notifications_enabled


def test_toggle_validates_and_my_accounts_lists_only_own(client):
    user, other = _user('admin'), _user('admin')
    mine, _ = _link(user), _link(other)
    assert (
        client.post('/api/telegram/notifications/toggle', json={'enabled': 'no'}, headers=_h(user)).status_code == 400
    )
    got = client.get('/api/telegram/my-accounts', headers=_h(user)).get_json()
    assert [a['telegram_chat_id'] for a in got['accounts']] == [mine.telegram_chat_id]


def test_test_message_reports_muted_accounts(client, sent):
    user = _user('jugador')
    _link(user, enabled=False)
    r = client.post('/api/telegram/notifications/test', headers=_h(user))
    assert r.status_code == 200 and r.get_json()['muted'] == 1
    assert 'DESACTIVADAS' in sent[-1]['text']
    assert client.post('/api/telegram/notifications/test', headers=_h(_user('jugador'))).status_code == 404


def test_forwarding_respects_account_switch_and_level(app, sent):
    svc = NotificationService()
    user = _user('admin')
    acc = _link(user)
    # nivel «important» (por defecto): una notificación normal NO llega a Telegram
    svc.notify_user(user.id, 'aviso normal', title='t', category='system', priority='normal')
    assert sent == []
    # nivel «all»: sí llega
    svc.update_preferences(user.id, {'telegram_level': 'all'})
    svc.notify_user(user.id, 'aviso normal 2', title='t', category='system', priority='normal')
    assert len(sent) == 1 and sent[0]['chat_id'] == acc.telegram_chat_id
    # cuenta silenciada: no llega aunque el nivel sea «all»
    acc.notifications_enabled = False
    db.session.commit()
    svc.notify_user(user.id, 'aviso normal 3', title='t', category='system', priority='normal')
    assert len(sent) == 1
    # interruptor maestro apagado: tampoco
    acc.notifications_enabled = True
    db.session.commit()
    svc.update_preferences(user.id, {'notifications_enabled': False})
    svc.notify_user(user.id, 'aviso normal 4', title='t', category='system', priority='high')
    assert len(sent) == 1


def test_telegram_level_is_validated(client):
    user = _user('admin')
    assert (
        client.put('/api/notifications/preferences', json={'telegram_level': 'todo'}, headers=_h(user)).status_code
        == 400
    )
    assert (
        client.put('/api/notifications/preferences', json={'telegram_level': 'all'}, headers=_h(user)).status_code
        == 200
    )
    assert client.get('/api/notifications/preferences', headers=_h(user)).get_json()['telegram_level'] == 'all'
