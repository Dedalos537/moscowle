"""Los endpoints de sesion por HTTP directo deben validar que la sesion sea del
terapeuta (admin/supervisor: cualquiera). No basta con el rol 'terapista'."""

import uuid
from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.models import User
from app.models.appointment import Appointment


def _user(session, role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'u{tag}', email=f'{tag}@own.test', password='x', role=role, **kw)
    session.add(u)
    session.flush()
    return u


@pytest.fixture
def world(session):
    ter_a, ter_b, admin = (_user(session, 'terapista'), _user(session, 'terapista'), _user(session, 'admin'))
    pat = _user(session, 'jugador')
    when = datetime.utcnow() + timedelta(days=3)

    def appt(ter):
        a = Appointment(therapist_id=ter.id, patient_id=pat.id, start_time=when, end_time=when + timedelta(hours=1))
        session.add(a)
        session.flush()
        return a

    own, foreign = appt(ter_a), appt(ter_b)
    session.commit()
    return {'ter_a': ter_a, 'admin': admin, 'own': own, 'foreign': foreign}


def _call(client, user, method, path, **kw):
    token = create_access_token(identity=str(user.id))
    client.set_cookie('localhost', 'access_token', token)
    return getattr(client, method)(path, headers={'Authorization': f'Bearer {token}'}, **kw)


CASES = [
    ('put', '/api/sessions/{id}', {'json': {'notes': 'x'}}),
    ('delete', '/api/sessions/{id}', {}),
    ('post', '/api/sessions/{id}/cancel', {'json': {}}),
    ('post', '/api/sessions/{id}/complete', {'json': {}}),
]


@pytest.mark.parametrize('method,path,kw', CASES)
def test_therapist_cannot_touch_foreign_session(client, world, method, path, kw):
    r = _call(client, world['ter_a'], method, path.format(id=world['foreign'].id), **kw)
    assert r.status_code == 403, r.get_data(as_text=True)


@pytest.mark.parametrize('method,path,kw', CASES)
def test_foreign_session_untouched_after_denial(client, world, session, method, path, kw):
    _call(client, world['ter_a'], method, path.format(id=world['foreign'].id), **kw)
    session.expire_all()
    fresh = session.get(Appointment, world['foreign'].id)
    assert fresh is not None and fresh.status == 'scheduled' and not fresh.notes


@pytest.mark.parametrize('method,path,kw', CASES[:3])
def test_therapist_can_touch_own_session(client, world, method, path, kw):
    r = _call(client, world['ter_a'], method, path.format(id=world['own'].id), **kw)
    assert r.status_code < 400, r.get_data(as_text=True)


@pytest.mark.parametrize('method,path,kw', [CASES[0], CASES[2]])
def test_admin_can_touch_any_session(client, world, method, path, kw):
    r = _call(client, world['admin'], method, path.format(id=world['foreign'].id), **kw)
    assert r.status_code < 400, r.get_data(as_text=True)


READS = ['audit', 'compare-live', 'program', 'objectives']


@pytest.mark.parametrize('suffix', READS)
def test_therapist_cannot_read_foreign_session_clinical_data(client, world, suffix):
    r = _call(client, world['ter_a'], 'get', f'/api/sessions/{world["foreign"].id}/{suffix}')
    assert r.status_code == 403, r.get_data(as_text=True)


@pytest.mark.parametrize('suffix', READS)
def test_therapist_and_admin_can_read_allowed_session(client, world, suffix):
    own = _call(client, world['ter_a'], 'get', f'/api/sessions/{world["own"].id}/{suffix}')
    adm = _call(client, world['admin'], 'get', f'/api/sessions/{world["foreign"].id}/{suffix}')
    assert own.status_code != 403 and adm.status_code != 403
