"""Calendario global de sesiones (admin): listado acotado, creación en lote sin choques, edición con hora en UTC."""

import io
import json
import uuid
from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.models import User
from app.models.appointment import Appointment


def _user(session, role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@adm.test', password='x', role=role, **kw)
    session.add(u)
    session.flush()
    return u


@pytest.fixture
def world(session):
    admin = _user(session, 'admin', timezone='America/Lima')
    supervisor = _user(session, 'supervisor', timezone='America/Lima')
    ter, ter2 = _user(session, 'terapista'), _user(session, 'terapista')
    pat, pat2 = _user(session, 'jugador'), _user(session, 'jugador')
    session.commit()
    return dict(admin=admin, supervisor=supervisor, ter=ter, ter2=ter2, pat=pat, pat2=pat2)


def _call(client, user, method, path, **kw):
    token = create_access_token(identity=str(user.id))
    client.set_cookie('localhost', 'access_token', token)
    return getattr(client, method)(path, headers={'Authorization': f'Bearer {token}'}, **kw)


def _future_weekday(days_ahead=20):
    d = datetime.utcnow().date() + timedelta(days=days_ahead)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _batch(client, world, **over):
    day = _future_weekday()
    body = {
        'therapist_id': world['ter'].id,
        'patient_id': world['pat'].id,
        'dates': [day.isoformat()],
        'start_time': '10:00',
        'end_time': '11:00',
        'sede': 'Piura',
        'session_type': 'individual',
        'title_prefix': 'Lenguaje',
    }
    body.update(over)
    return _call(client, world['admin'], 'post', '/admin/api/sessions/batch', json=body), day


def _list(client, world, day, **params):
    # Los commits de las rutas persisten entre tests: se acota SIEMPRE a los usuarios de este test.
    scope = {} if ('therapist_id' in params or 'patient_id' in params) else {'therapist_id': world['ter'].id}
    q = '&'.join(f'{k}={v}' for k, v in {'start': day.isoformat(), 'end': day.isoformat(), **scope, **params}.items())
    return _call(client, world['admin'], 'get', f'/admin/api/sessions?{q}')


# ---------------------------------------------------------------- listado
def test_list_requires_a_valid_bounded_range(client, world):
    r = _call(client, world['admin'], 'get', '/admin/api/sessions?start=hoy&end=mañana')
    assert r.status_code == 400
    r = _call(client, world['admin'], 'get', '/admin/api/sessions?start=2026-01-01')
    assert r.status_code == 400
    r = _call(client, world['admin'], 'get', '/admin/api/sessions?start=2026-01-01&end=2027-12-31')
    assert r.status_code == 400
    r = _call(client, world['admin'], 'get', '/admin/api/sessions?start=2026-02-01&end=2026-01-01')
    assert r.status_code == 400


def test_list_filters_by_patient_and_therapist(client, world):
    day = _future_weekday()
    assert _batch(client, world)[0].status_code == 200
    r, _ = _batch(
        client, world, therapist_id=world['ter2'].id, patient_id=world['pat2'].id, start_time='15:00', end_time='16:00'
    )
    assert r.status_code == 200
    both = [e for t in (world['ter'], world['ter2']) for e in _list(client, world, day, therapist_id=t.id).get_json()]
    assert len(both) == 2
    only_pat = _list(client, world, day, patient_id=world['pat2'].id).get_json()
    assert [e['extendedProps']['patient_id'] for e in only_pat] == [world['pat2'].id]
    only_ter = _list(client, world, day, therapist_id=world['ter'].id).get_json()
    assert [e['extendedProps']['therapist_id'] for e in only_ter] == [world['ter'].id]


# ---------------------------------------------------------------- creación
def test_batch_validates_roles_and_payload(client, world):
    r, _ = _batch(client, world, therapist_id=world['pat'].id)  # un paciente no es terapeuta
    assert r.status_code == 400
    r, _ = _batch(client, world, patient_id=world['ter'].id)
    assert r.status_code == 400
    r, _ = _batch(client, world, start_time='25:00')
    assert r.status_code == 400
    r, _ = _batch(client, world, dates=['no-es-fecha'])
    assert r.status_code == 400
    r = _call(client, world['admin'], 'post', '/admin/api/sessions/batch', data='no json', content_type='text/plain')
    assert r.status_code == 400


def test_batch_persists_notes_and_day_notes(client, world, session):
    day = _future_weekday()
    day2 = day + timedelta(days=1)
    while day2.weekday() >= 5:
        day2 += timedelta(days=1)
    r, _ = _batch(
        client,
        world,
        dates=[day.isoformat(), day2.isoformat()],
        notes='General',
        day_notes={day2.isoformat(): 'Solo este día'},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    ids = r.get_json()['session_ids']
    notes = {a.start_time.date(): a.notes for a in Appointment.query.filter(Appointment.id.in_(ids)).all()}
    assert 'General' in notes.values() and 'Solo este día' in notes.values()


def test_batch_skips_conflicts_and_reports_them(client, world):
    assert _batch(client, world)[0].status_code == 200
    # mismo terapeuta, otro paciente, mismo horario → choca
    r, _ = _batch(client, world, patient_id=world['pat2'].id)
    assert r.status_code == 409
    assert r.get_json()['conflicts'][0]['reason'].startswith('El terapeuta')
    # mismo paciente con otro terapeuta, mismo horario → choca
    r, _ = _batch(client, world, therapist_id=world['ter2'].id)
    assert r.status_code == 409
    assert r.get_json()['conflicts'][0]['reason'].startswith('El paciente')
    # horario distinto → ok
    r, _ = _batch(client, world, start_time='11:00', end_time='12:00')
    assert r.status_code == 200


# ---------------------------------------------------------------- edición
def test_edit_keeps_the_displayed_time(client, world):
    """Regresión: PUT guardaba la hora local sin convertir a UTC y la sesión se corría 5 h."""
    r, day = _batch(client, world)
    sid = r.get_json()['session_ids'][0]
    before = _list(client, world, day).get_json()[0]['start']
    r = _call(
        client,
        world['admin'],
        'put',
        f'/admin/api/sessions/{sid}',
        json={'start_time': f'{day.isoformat()}T10:00', 'end_time': f'{day.isoformat()}T11:00', 'title': 'Editada'},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    after = _list(client, world, day).get_json()[0]
    assert after['start'] == before and after['title'] == 'Editada'


def test_move_to_another_day_keeps_clock_time(client, world):
    r, day = _batch(client, world)
    sid = r.get_json()['session_ids'][0]
    new_day = day + timedelta(days=1)
    r = _call(
        client,
        world['admin'],
        'put',
        f'/admin/api/sessions/{sid}',
        json={'start_time': f'{new_day.isoformat()}T10:00', 'end_time': f'{new_day.isoformat()}T11:00'},
    )
    assert r.status_code == 200
    moved = _list(client, world, new_day).get_json()[0]
    assert moved['start'].endswith('10:00:00-05:00') or 'T10:00:00' in moved['start']


def test_edit_validates_status_and_times_and_conflicts(client, world):
    r, day = _batch(client, world)
    sid = r.get_json()['session_ids'][0]
    put = lambda body: _call(client, world['admin'], 'put', f'/admin/api/sessions/{sid}', json=body)  # noqa: E731
    assert put({'status': 'borrada'}).status_code == 400
    assert put({'start_time': f'{day}T12:00', 'end_time': f'{day}T11:00'}).status_code == 400
    assert put({'start_time': 'mañana'}).status_code == 400
    # otra sesión del mismo paciente a las 14:00: mover esta encima choca
    r2, _ = _batch(client, world, start_time='14:00', end_time='15:00')
    assert r2.status_code == 200
    clash = put({'start_time': f'{day}T14:30', 'end_time': f'{day}T15:30'})
    assert clash.status_code == 409 and clash.get_json()['conflict'] is True
    assert put({'start_time': f'{day}T14:30', 'end_time': f'{day}T15:30', 'force': True}).status_code == 200


def test_supervisor_can_edit_but_not_create(client, world):
    r, day = _batch(client, world)
    sid = r.get_json()['session_ids'][0]
    ok = _call(client, world['supervisor'], 'put', f'/admin/api/sessions/{sid}', json={'notes': 'visto'})
    assert ok.status_code == 200
    body = {
        'therapist_id': world['ter'].id,
        'patient_id': world['pat'].id,
        'dates': [day.isoformat()],
        'start_time': '08:00',
        'end_time': '09:00',
    }
    assert _call(client, world['supervisor'], 'post', '/admin/api/sessions/batch', json=body).status_code == 403


# ---------------------------------------------------------------- programa en lote
def _docx_bytes():
    from docx import Document

    buf = io.BytesIO()
    doc = Document()
    doc.add_paragraph('Objetivo: trabajar fonemas /r/ y /s/')
    doc.save(buf)
    buf.seek(0)
    return buf


def test_bulk_program_assigns_one_document_to_many_sessions(client, world):
    from app.models import SessionAudit

    r, day = _batch(client, world, dates=[day.isoformat() for day in [_future_weekday(20), _future_weekday(27)]])
    ids = r.get_json()['session_ids']
    resp = _call(
        client,
        world['admin'],
        'post',
        '/admin/api/sessions/bulk-program',
        data={'program_file': (_docx_bytes(), 'programa.docx'), 'session_ids': json.dumps(ids + [999999])},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body['updated'] == len(ids) and body['missing'] == [999999]
    assert SessionAudit.query.filter(SessionAudit.appointment_id.in_(ids)).count() == len(ids)


def test_bulk_program_rejects_wrong_file_and_empty_selection(client, world):
    bad = _call(
        client,
        world['admin'],
        'post',
        '/admin/api/sessions/bulk-program',
        data={'program_file': (io.BytesIO(b'x'), 'programa.pdf'), 'session_ids': '[1]'},
        content_type='multipart/form-data',
    )
    assert bad.status_code == 400
    empty = _call(
        client,
        world['admin'],
        'post',
        '/admin/api/sessions/bulk-program',
        data={'program_file': (_docx_bytes(), 'programa.docx'), 'session_ids': '[]'},
        content_type='multipart/form-data',
    )
    assert empty.status_code == 400
