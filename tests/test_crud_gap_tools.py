"""Tools que cerraban el CRUD del asistente: editar/eliminar gasto, editar
usuario y reprogramar sesion. Todas son de escritura (piden confirmacion)."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models import User
from app.models.appointment import Appointment
from app.models.payment import Expense
from app.services import tools_registry as tr
from app.services.tools_registry import CORE_TOOL_NAMES, SAFE_WRITE_TOOLS, TOOL_REGISTRY, execute_tool

NEW_TOOLS = {
    'update_expense': {'admin'},
    'delete_expense': {'admin'},
    'update_user': {'admin'},
    'reschedule_session': {'admin', 'supervisor', 'terapista'},
}


def _uid():
    return uuid.uuid4().hex[:8]


def _user(session, role='jugador', **kw):
    u = User(username=f'u{_uid()}', email=f'{_uid()}@crud.test', password='x', role=role, **kw)
    session.add(u)
    session.flush()
    return u


@pytest.mark.parametrize('name,roles', NEW_TOOLS.items())
def test_registered_as_gated_write_core_tool(name, roles):
    entry = TOOL_REGISTRY[name]
    assert entry['category'] == 'write'
    assert name in CORE_TOOL_NAMES
    assert name not in SAFE_WRITE_TOOLS  # exige confirmacion
    assert set(entry['roles']) == roles


# ---------------- gastos ----------------
@pytest.fixture
def expense(session):
    e = Expense(category='operational', amount=100.0, date=datetime.utcnow(), description='luz')
    session.add(e)
    session.commit()
    return e


def test_update_expense_changes_fields(session, expense):
    out = execute_tool(
        'update_expense', {'expense_id': expense.id, 'amount': 150.5, 'category': 'bonus'}, user_id=1, role='admin'
    )
    assert out.get('success'), out
    session.refresh(expense)
    assert expense.amount == 150.5 and expense.category == 'bonus' and expense.description == 'luz'


@pytest.mark.parametrize('amount', [0, -5, 'abc'])
def test_update_expense_rejects_bad_amount(session, expense, amount):
    out = execute_tool('update_expense', {'expense_id': expense.id, 'amount': amount}, user_id=1, role='admin')
    assert 'error' in out
    session.refresh(expense)
    assert expense.amount == 100.0


def test_update_expense_requires_something_to_change(expense):
    assert 'error' in execute_tool('update_expense', {'expense_id': expense.id}, user_id=1, role='admin')


def test_update_expense_not_found():
    assert 'error' in execute_tool('update_expense', {'expense_id': 987654, 'amount': 5}, user_id=1, role='admin')


def test_delete_expense_is_soft_and_not_repeatable(session, expense):
    out = execute_tool('delete_expense', {'expense_id': expense.id}, user_id=1, role='admin')
    assert out.get('success'), out
    session.refresh(expense)
    assert expense.is_active is False
    assert 'error' in execute_tool('delete_expense', {'expense_id': expense.id}, user_id=1, role='admin')
    assert 'error' in execute_tool('update_expense', {'expense_id': expense.id, 'amount': 9}, user_id=1, role='admin')


@pytest.mark.parametrize('role', ['supervisor', 'terapista', 'jugador'])
def test_expense_tools_admin_only(expense, role):
    assert 'permisos' in execute_tool('delete_expense', {'expense_id': expense.id}, user_id=1, role=role)['error']


# ---------------- usuarios ----------------
def test_update_user_edits_allowed_fields_only(session):
    u = _user(session)
    out = execute_tool(
        'update_user', {'user_id': u.id, 'username': 'Nombre Nuevo', 'phone': '999111222'}, user_id=1, role='admin'
    )
    assert out.get('success'), out
    session.refresh(u)
    assert (u.username, u.phone, u.role) == ('Nombre Nuevo', '999111222', 'jugador')
    assert 'role' not in TOOL_REGISTRY['update_user']['parameters']['properties']
    assert 'password' not in TOOL_REGISTRY['update_user']['parameters']['properties']


def test_update_user_email_validation_and_uniqueness(session):
    a, b = _user(session), _user(session)
    assert 'error' in execute_tool('update_user', {'user_id': a.id, 'email': 'sin-arroba'}, user_id=1, role='admin')
    dup = execute_tool('update_user', {'user_id': a.id, 'email': b.email.upper()}, user_id=1, role='admin')
    assert 'error' in dup
    ok = execute_tool('update_user', {'user_id': a.id, 'email': f'{_uid()}@Nuevo.test'}, user_id=1, role='admin')
    assert ok.get('success'), ok
    session.refresh(a)
    assert a.email == a.email.lower()


def test_update_user_not_found_and_empty():
    assert 'error' in execute_tool('update_user', {'user_id': 987654, 'phone': '1'}, user_id=1, role='admin')


def test_update_user_nothing_to_change(session):
    u = _user(session)
    assert 'error' in execute_tool('update_user', {'user_id': u.id}, user_id=1, role='admin')


# ---------------- reprogramar sesion ----------------
@pytest.fixture
def appts(session):
    ter_a, ter_b = _user(session, 'terapista'), _user(session, 'terapista')
    pat_a = _user(session, assigned_therapist_id=ter_a.id)
    pat_b = _user(session, assigned_therapist_id=ter_b.id)
    when = datetime.utcnow() + timedelta(days=2)
    own = Appointment(therapist_id=ter_a.id, patient_id=pat_a.id, start_time=when)
    foreign = Appointment(therapist_id=ter_b.id, patient_id=pat_b.id, start_time=when)
    session.add_all([own, foreign])
    session.commit()
    return {'ter_a': ter_a, 'own': own, 'foreign': foreign}


class _Resp:
    status_code = 200

    def get_json(self):
        return {'id': 1}


def test_reschedule_sends_put_with_times(monkeypatch, appts):
    sent = {}

    def fake_put(endpoint, json=None, user_id=None, role=None):
        sent.update(endpoint=endpoint, json=json)
        return _Resp()

    monkeypatch.setattr(tr, '_api_put', fake_put)
    out = execute_tool(
        'reschedule_session',
        {'session_id': appts['own'].id, 'start_time': '2030-05-20 15:00', 'end_time': '2030-05-20 16:00'},
        user_id=appts['ter_a'].id,
        role='terapista',
    )
    assert out.get('success'), out
    assert sent['endpoint'] == f'/api/sessions/{appts["own"].id}'
    assert sent['json']['start_time'].startswith('2030-05-20T15:00')
    assert sent['json']['end_time'].startswith('2030-05-20T16:00')


def test_reschedule_defaults_end_to_original_duration(monkeypatch, appts):
    sent = {}
    monkeypatch.setattr(tr, '_api_put', lambda e, json=None, **k: sent.update(json=json) or _Resp())
    execute_tool(
        'reschedule_session',
        {'session_id': appts['own'].id, 'start_time': '2030-05-20T15:00:00'},
        user_id=appts['ter_a'].id,
        role='terapista',
    )
    assert 'end_time' in sent['json']


def test_reschedule_rejects_bad_datetime_without_calling_api(monkeypatch, appts):
    monkeypatch.setattr(tr, '_api_put', lambda *a, **k: pytest.fail('no debio llamar a la API'))
    out = execute_tool(
        'reschedule_session', {'session_id': appts['own'].id, 'start_time': 'mañana temprano'}, user_id=1, role='admin'
    )
    assert 'error' in out


def test_reschedule_blocked_for_foreign_session(monkeypatch, appts):
    monkeypatch.setattr(tr, '_api_put', lambda *a, **k: pytest.fail('escritura sobre sesion ajena'))
    out = execute_tool(
        'reschedule_session',
        {'session_id': appts['foreign'].id, 'start_time': '2030-05-20 15:00'},
        user_id=appts['ter_a'].id,
        role='terapista',
    )
    assert 'alcance' in out['error']
