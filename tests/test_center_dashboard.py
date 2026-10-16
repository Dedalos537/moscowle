"""Dashboard del centro: cifras reales, señales de abandono concretas, filtro por sede y permisos."""

import uuid
from datetime import date, datetime

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Appointment, Payment, Sede, User
from app.models.contract import Contract, Installment
from app.models.user_status_log import UserStatusLog
from app.services import center_dashboard as cd

# Fecha fija en el pasado: «ahora» para el cálculo es el cierre de ese día (no depende del reloj real).
TODAY = date(2026, 9, 20)


def _sede():
    s = Sede(name=f'Sede {uuid.uuid4().hex[:6]}', address='Av. Prueba 1')
    db.session.add(s)
    db.session.commit()
    return s


def _user(role, sede=None, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@cd.test', password='x', role=role, **kw)
    if sede is not None:
        u.sede_id = sede.id
    db.session.add(u)
    db.session.commit()
    return u


def _appt(t, p, when, status='completed', attendance='present'):
    db.session.add(
        Appointment(
            therapist_id=t.id, patient_id=p.id, title='Terapia', start_time=when, status=status, attendance=attendance
        )
    )


def _risk(data, patient):
    return next((r for r in data['risks']['items'] if r['patient']['id'] == patient.id), None)


def test_risks_explain_why_each_patient_may_leave(app):
    norte = _sede()
    t = _user('terapista')
    t.assigned_sedes.append(norte)
    debtor = _user('jugador', norte)
    absent = _user('jugador', norte)
    fine = _user('jugador', norte)
    # Faltó a sus dos últimas sesiones.
    _appt(t, absent, datetime(2026, 9, 10, 15), attendance='absent')
    _appt(t, absent, datetime(2026, 9, 17, 15), status='scheduled', attendance='absent')
    # Al día, con sesión reciente y próxima agendada.
    _appt(t, fine, datetime(2026, 9, 15, 15))
    _appt(t, fine, datetime(2026, 9, 22, 15), status='scheduled', attendance='pending')
    _appt(t, debtor, datetime(2026, 9, 14, 15))
    _appt(t, debtor, datetime(2026, 9, 21, 15), status='scheduled', attendance='pending')
    c = Contract(patient_id=debtor.id, total_amount=300, installment_count=2, installment_amount=150)
    db.session.add(c)
    db.session.flush()
    db.session.add_all(
        [
            Installment(contract_id=c.id, number=1, due_date=date(2026, 9, 5), amount=150, paid_amount=0),
            Installment(contract_id=c.id, number=2, due_date=TODAY, amount=150, paid_amount=0),
            Payment(patient_id=fine.id, amount=120, date=datetime(2026, 9, 15, 16), method='yape', status='completed'),
        ]
    )
    db.session.commit()

    data = cd.dashboard('month', norte.id, today=TODAY)

    d = _risk(data, debtor)
    assert d and d['overdue'] == 150 and d['reasons'][0]['kind'] == 'debt' and 'S/ 150.00' in d['reasons'][0]['detail']
    a = _risk(data, absent)
    assert a and any(r['kind'] == 'absences' for r in a['reasons'])
    assert _risk(data, fine) is None
    # El cobro de hoy aparece en «Hoy» con su monto.
    due = {p['patient']['id']: p['amount'] for p in data['today']['payments_due']['items']}
    assert due.get(debtor.id) == 150
    pulse = {k['key']: k for k in data['pulse']}
    assert pulse['revenue']['value'] == 120 and len(pulse['revenue']['trend']) == 6
    assert data['team'][0]['id'] == t.id and data['team'][0]['sessions_done'] >= 2
    assert data['sedes'] == []  # al mirar una sede no se compara con las demás


def test_flow_counts_new_and_departed_patients(app):
    sur = _sede()
    left = _user('jugador', sur)
    left.created_at = datetime(2026, 7, 3, 12)
    _user('jugador', sur).created_at = datetime(2026, 9, 2, 12)
    db.session.add(
        UserStatusLog(user_id=left.id, old_status='active', new_status='retired', changed_at=datetime(2026, 9, 9, 12))
    )
    db.session.commit()
    flow = {m['month']: m for m in cd.dashboard('month', sur.id, today=TODAY)['flow']}
    sep = flow['2026-09-01']
    assert sep['new'] >= 1 and sep['left'] == 1


def test_center_view_lists_sedes_and_requires_staff(app, client):
    _sede()
    data = cd.dashboard('month', None, today=TODAY)
    assert data['sedes'] and {'revenue', 'attendance'} <= set(data['sedes'][0]['kpis'])
    patient = _user('jugador')
    r = client.get(
        '/api/admin/dashboard', headers={'Authorization': 'Bearer ' + create_access_token(identity=str(patient.id))}
    )
    assert r.status_code == 403
    admin = _user('admin')
    r = client.get(
        '/api/admin/dashboard?period=quarter',
        headers={'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))},
    )
    assert r.status_code == 200 and r.get_json()['period'] == 'quarter'
