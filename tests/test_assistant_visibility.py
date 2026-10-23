"""Botón flotante del asistente: visible por tipo de usuario, lo decide el admin."""

import uuid

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.system_setting import SystemSetting


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@gmail.com', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def _reset():
    SystemSetting.query.filter(SystemSetting.key.like('assistant.visible.%')).delete(synchronize_session=False)
    db.session.commit()


def test_defaults_admin_on_others_off(client, app):
    _reset()
    assert client.get('/api/assistant/visibility', headers=_h(_user('admin'))).get_json()['visible'] is True
    assert client.get('/api/assistant/visibility', headers=_h(_user('terapista'))).get_json()['visible'] is False
    assert client.get('/api/assistant/visibility', headers=_h(_user('jugador'))).get_json()['visible'] is False


def test_only_admin_changes_it_and_it_applies(client, app):
    _reset()
    ther = _user('terapista')
    assert client.put('/api/assistant/visibility', json={'terapista': True}, headers=_h(ther)).status_code == 403
    admin = _user('admin')
    res = client.put(
        '/api/assistant/visibility', json={'terapista': True, 'admin': False}, headers=_h(admin)
    ).get_json()
    assert res['terapista'] is True and res['admin'] is False and res['visible'] is False
    assert client.get('/api/assistant/visibility', headers=_h(ther)).get_json()['visible'] is True
    # supervisor sigue al admin
    assert client.get('/api/assistant/visibility', headers=_h(_user('supervisor'))).get_json()['visible'] is False
    _reset()


def test_chat_refuses_roles_with_assistant_off(client, app):
    _reset()
    res = client.post('/mcp/chat', json={'message': 'hola'}, headers=_h(_user('jugador')))
    assert res.status_code == 403
