"""Pasar a un usuario a inactivo/retirado/deudor exige justificacion en TODAS las vias de
escritura (modal, edicion, toggle-status y la tool del asistente) y deja rastro en el
historial. Antes update-user y toggle-status lo cambiaban sin motivo (y toggle sin historial)."""

import uuid

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.user_status_log import UserStatusLog
from app.services import tools_registry as tr
from app.services.admin_service import AdminService

RISKY = ['inactive', 'retired', 'debtor']


def _user(session, role='jugador', **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@st.test', password='x', role=role, **kw)
    session.add(u)
    session.commit()
    return u


def _call(client, user, path, **kw):
    token = create_access_token(identity=str(user.id))
    return client.post(path, headers={'Authorization': f'Bearer {token}'}, **kw)


def _logs(user_id):
    db.session.expire_all()
    return UserStatusLog.query.filter_by(user_id=user_id).all()


# ---------------------------------------------------------------- servicio
@pytest.mark.parametrize('status', RISKY)
def test_change_user_status_requires_justification(session, status):
    u = _user(session)
    ok, msg = AdminService().change_user_status(u.id, status, '   ', changed_by_id=None)
    assert ok is False and 'justificación' in msg.lower()
    db.session.expire_all()
    assert (db.session.get(User, u.id).account_status or 'active') == 'active' and _logs(u.id) == []


@pytest.mark.parametrize('status', RISKY)
def test_change_user_status_with_justification_logs(session, status):
    u = _user(session)
    ok, _ = AdminService().change_user_status(u.id, status, 'Dejo de asistir', changed_by_id=None)
    assert ok
    assert [(row.new_status, row.justification) for row in _logs(u.id)] == [(status, 'Dejo de asistir')]


def test_reactivating_does_not_require_justification(session):
    u = _user(session, account_status='retired')
    ok, _ = AdminService().change_user_status(u.id, 'active', '', changed_by_id=None)
    assert ok


@pytest.mark.parametrize('status', RISKY)
def test_update_user_cannot_change_status_without_justification(session, status):
    u = _user(session)
    ok, msg = AdminService().update_user({'id': u.id, 'username': 'cambio', 'account_status': status})
    assert ok is False and 'justificación' in msg.lower()
    db.session.expire_all()
    fresh = db.session.get(User, u.id)
    assert (fresh.account_status or 'active') == 'active' and fresh.username != 'cambio'


def test_update_user_with_justification_logs(session):
    u = _user(session)
    ok, _ = AdminService().update_user({'id': u.id, 'account_status': 'debtor', 'justification': 'Debe 2 meses'})
    assert ok and [row.justification for row in _logs(u.id)] == ['Debe 2 meses']


def test_update_user_without_status_change_needs_no_justification(session):
    u = _user(session)
    ok, _ = AdminService().update_user({'id': u.id, 'username': 'nuevo nombre'})
    assert ok


# --------------------------------------------------------------------- HTTP
def test_update_user_endpoint_rejects_risky_status_without_motive(client, session):
    admin, u = _user(session, 'admin'), _user(session)
    r = _call(client, admin, '/api/admin/update-user', json={'id': u.id, 'account_status': 'retired'})
    assert r.status_code == 400


@pytest.mark.parametrize('status', RISKY)
def test_toggle_status_requires_justification_and_logs(client, session, status):
    admin, u = _user(session, 'admin'), _user(session)
    assert _call(client, admin, f'/admin/api/users/{u.id}/toggle-status', json={'status': status}).status_code == 400
    ok = _call(
        client, admin, f'/admin/api/users/{u.id}/toggle-status', json={'status': status, 'justification': 'motivo'}
    )
    assert ok.status_code == 200, ok.get_data(as_text=True)
    assert [row.new_status for row in _logs(u.id)] == [status]
    db.session.expire_all()
    assert db.session.get(User, u.id).is_active is False


def test_toggle_to_active_needs_no_justification(client, session):
    admin, u = _user(session, 'admin'), _user(session, account_status='retired', is_active=False)
    r = _call(client, admin, f'/admin/api/users/{u.id}/toggle-status', json={'status': 'active'})
    assert r.status_code == 200
    db.session.expire_all()
    assert db.session.get(User, u.id).is_active is True


# ------------------------------------------------------------ tool del asistente
def test_assistant_tool_demands_and_forwards_justification(monkeypatch):
    sent = {}

    class R:
        status_code = 200

        def get_json(self):
            return {'message': 'ok', 'old_status': 'active'}

    monkeypatch.setattr(tr, '_api_post', lambda path, json=None, **k: sent.update(path=path, json=json) or R())
    assert (
        'justific'
        in tr.execute_tool('toggle_user_status', {'user_id': 1, 'status': 'retired'}, user_id=1, role='admin')[
            'error'
        ].lower()
    )
    assert sent == {}
    out = tr.execute_tool(
        'toggle_user_status', {'user_id': 1, 'status': 'retired', 'justification': 'Se mudó'}, user_id=1, role='admin'
    )
    assert out.get('success') and sent['json']['justification'] == 'Se mudó'
