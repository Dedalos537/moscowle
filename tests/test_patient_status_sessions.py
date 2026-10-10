"""Estados de pacientes coherentes y alta de sesiones en lote que no falla por un miembro inactivo."""

import uuid

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.services.admin_service import AdminService
from app.services.user_status import apply_is_active, sync_patient_statuses


def _user(role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@ps.test', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def test_status_change_keeps_is_active_in_sync(app):
    admin, p = _user('admin'), _user('jugador', is_active=False, account_status='inactive')
    svc = AdminService()
    ok, _ = svc.change_user_status(p.id, 'active', '', changed_by_id=admin.id)
    assert ok and p.account_status == 'active' and p.is_active is True
    ok, _ = svc.change_user_status(p.id, 'debtor', 'Debe octubre', changed_by_id=admin.id)
    assert ok and p.is_active is True  # el deudor sigue en atención
    ok, _ = svc.change_user_status(p.id, 'retired', 'Alta terapéutica', changed_by_id=admin.id)
    assert ok and p.is_active is False
    apply_is_active(p, True)
    assert p.account_status == 'active'


def test_startup_sync_fixes_desynced_patients(app):
    a = _user('jugador', is_active=False, account_status='active')  # se veía Activo pero era rechazado
    b = _user('jugador', is_active=True, account_status='retired')  # retirado que seguía recibiendo sesiones
    c = _user('jugador', is_active=None, account_status=None)
    sync_patient_statuses(db)
    assert a.is_active is True and b.is_active is False
    assert c.account_status == 'active' and c.is_active is True


def _batch(client, admin, therapist, **kw):
    payload = {
        'therapist_id': therapist.id,
        'title_prefix': 'Lenguaje',
        'session_type': 'grupal',
        'start_time': '09:00',
        'end_time': '10:00',
        'dates': ['2026-11-16', '2026-11-17', '2026-11-18'],
        'notes': 'Trabajar fonemas',
        'day_notes': {'2026-11-16': 'Traer cuaderno'},
        **kw,
    }
    h = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
    return client.post('/admin/api/sessions/batch', json=payload, headers=h)


def test_group_batch_skips_inactive_member_instead_of_failing(client, app):
    admin, therapist = _user('admin'), _user('terapista')
    ok1, ok2 = _user('jugador'), _user('jugador', is_active=None, account_status=None)
    gone = _user('jugador', is_active=False, account_status='inactive')
    from app.models.patient_group import PatientGroup

    group = PatientGroup(name='Grupo A', therapist_id=therapist.id)
    db.session.add(group)
    db.session.commit()
    r = _batch(client, admin, therapist, patient_ids=[ok1.id, ok2.id, gone.id], group_id=group.id)
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body['created'] == 6 and gone.username in body['message']


def test_single_inactive_patient_gets_a_clear_message(client, app):
    admin, therapist = _user('admin'), _user('terapista')
    gone = _user('jugador', is_active=True, account_status='retired')
    r = _batch(client, admin, therapist, patient_id=gone.id, session_type='individual')
    assert r.status_code == 400
    assert gone.username in r.get_json()['error'] and 'Usuarios' in r.get_json()['error']
