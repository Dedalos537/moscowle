"""Solicitudes de terapeutas: sesiones, pacientes y grupos que la coordinación aprueba o rechaza."""

import uuid

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Appointment, User
from app.models.notification_group import NotificationItem
from app.models.patient_group import PatientGroup


def _user(role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@ar.test', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def _links(u):
    return [n.link for n in NotificationItem.query.filter_by(user_id=u.id).all()]


SESSIONS = {
    'title_prefix': 'Lenguaje',
    'session_type': 'individual',
    'dates': ['2026-12-01', '2026-12-02', '2026-12-03'],
    'start_time': '10:00',
    'end_time': '11:00',
    'notes': 'Reforzar /r/',
    'day_notes': {'2026-12-01': 'Traer cuaderno'},
}


def test_sessions_request_is_created_by_the_approval(client, app):
    admin, therapist, mine, other = _user('admin'), _user('terapista'), _user('jugador'), _user('jugador')
    mine.therapists.append(therapist)
    db.session.commit()

    # No puede pedir para un paciente ajeno.
    r = client.post(
        '/api/requests',
        json={'kind': 'sessions', 'payload': {**SESSIONS, 'patient_id': other.id}},
        headers=_h(therapist),
    )
    assert r.status_code == 400

    r = client.post(
        '/api/requests',
        json={'kind': 'sessions', 'payload': {**SESSIONS, 'patient_id': mine.id}},
        headers=_h(therapist),
    )
    assert r.status_code == 201, r.get_json()
    req = r.get_json()['request']
    assert req['status'] == 'pending' and '3 sesiones' in req['summary']
    assert f'/admin/requests?id={req["id"]}' in _links(admin)
    assert Appointment.query.filter_by(patient_id=mine.id).count() == 0  # nada se crea hasta aprobar

    # El terapeuta no puede aprobar.
    assert client.post(f'/api/requests/{req["id"]}/approve', headers=_h(therapist)).status_code == 403
    r = client.post(f'/api/requests/{req["id"]}/approve', json={}, headers=_h(admin))
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['request']['result']['created'] == 3
    appts = Appointment.query.filter_by(patient_id=mine.id, therapist_id=therapist.id).all()
    assert len(appts) == 3 and any(a.notes == 'Traer cuaderno' for a in appts)
    assert f'/therapist/requests?id={req["id"]}' in _links(therapist)
    # Ya resuelta: no se aprueba dos veces.
    assert client.post(f'/api/requests/{req["id"]}/approve', json={}, headers=_h(admin)).status_code == 400


def test_patient_and_group_requests(client, app):
    admin, therapist, p1 = _user('admin'), _user('terapista'), _user('jugador')
    p1.therapists.append(therapist)
    db.session.commit()
    name = 'Paciente ' + uuid.uuid4().hex[:6]
    r = client.post(
        '/api/requests',
        json={'kind': 'patient', 'payload': {'username': name, 'guardian_name': 'Rosa', 'phone': '999111222'}},
        headers=_h(therapist),
    )
    assert r.status_code == 201, r.get_json()
    rid = r.get_json()['request']['id']
    r = client.post(f'/api/requests/{rid}/approve', json={}, headers=_h(admin))
    assert r.status_code == 200, r.get_json()
    new = db.session.get(User, r.get_json()['request']['result']['user_id'])
    assert new.username == name and new.role == 'jugador' and therapist in new.therapists

    r = client.post(
        '/api/requests',
        json={
            'kind': 'group',
            'payload': {
                'name': 'Grupo martes',
                'member_ids': [p1.id, new.id],
                'start_time': '15:00',
                'end_time': '16:00',
            },
        },
        headers=_h(therapist),
    )
    assert r.status_code == 201, r.get_json()
    rid = r.get_json()['request']['id']
    # Rechazar exige motivo.
    assert client.post(f'/api/requests/{rid}/reject', json={}, headers=_h(admin)).status_code == 400
    r = client.post(f'/api/requests/{rid}/approve', json={}, headers=_h(admin))
    assert r.status_code == 200, r.get_json()
    group = db.session.get(PatientGroup, r.get_json()['request']['result']['group_id'])
    assert {m.id for m in group.members} == {p1.id, new.id} and group.therapist_id == therapist.id


def test_reject_notifies_with_reason_and_failed_approval_stays_pending(client, app):
    admin, therapist, p = _user('admin'), _user('terapista'), _user('jugador')
    p.therapists.append(therapist)
    db.session.commit()
    r = client.post(
        '/api/requests',
        json={'kind': 'sessions', 'payload': {**SESSIONS, 'patient_id': p.id, 'dates': ['2026-12-08']}},
        headers=_h(therapist),
    )
    rid = r.get_json()['request']['id']
    r = client.post(f'/api/requests/{rid}/reject', json={'note': 'Ese día no hay consultorio'}, headers=_h(admin))
    assert r.status_code == 200 and r.get_json()['request']['status'] == 'rejected'
    mine = client.get('/api/requests/mine', headers=_h(therapist)).get_json()['requests']
    assert mine[0]['review_note'] == 'Ese día no hay consultorio'

    # Si el paciente pasa a inactivo antes de aprobar, la aprobación falla con el motivo y queda pendiente.
    r = client.post(
        '/api/requests',
        json={'kind': 'sessions', 'payload': {**SESSIONS, 'patient_id': p.id, 'dates': ['2026-12-09']}},
        headers=_h(therapist),
    )
    rid = r.get_json()['request']['id']
    p.is_active, p.account_status = False, 'inactive'
    db.session.commit()
    r = client.post(f'/api/requests/{rid}/approve', json={}, headers=_h(admin))
    assert r.status_code == 400 and 'inactivo' in r.get_json()['error']
    pending = client.get('/api/requests?status=pending', headers=_h(admin)).get_json()['requests']
    row = next(x for x in pending if x['id'] == rid)
    assert row['last_error'] and row['status'] == 'pending'
