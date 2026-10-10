"""Balanced Scorecard de sedes: cada cifra sale de registros reales y de la sede correcta."""

import uuid
from datetime import date, datetime

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Appointment, Payment, Sede, User
from app.models.contract import Contract, Installment
from app.services import sede_scorecard as bsc

TODAY = date(2026, 10, 20)


def _user(role, sede=None):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@bsc.test', password='x', role=role)
    if sede is not None:
        u.sede_id = sede.id
    db.session.add(u)
    db.session.commit()
    return u


def _sede():
    s = Sede(name=f'Sede {uuid.uuid4().hex[:6]}', address='Av. Prueba 123')
    db.session.add(s)
    db.session.commit()
    return s


def _appt(therapist, patient, when, status='completed', attendance='present'):
    db.session.add(
        Appointment(
            therapist_id=therapist.id,
            patient_id=patient.id,
            title='Terapia',
            start_time=when,
            status=status,
            attendance=attendance,
        )
    )


def _card(sede_id, period='month'):
    data = bsc.scorecard(period, today=TODAY)
    card = next(s for s in data['sedes'] if s['id'] == sede_id)
    return data, {k['key']: k for k in card['kpis']}, card


def test_period_bounds_compare_the_same_elapsed_stretch():
    (first, last), (pfirst, plast) = bsc.period_bounds('month', TODAY)
    assert (first, last) == (date(2026, 10, 1), TODAY)
    assert (pfirst, plast) == (date(2026, 9, 1), date(2026, 9, 20))
    (qfirst, _), (pqfirst, _) = bsc.period_bounds('quarter', TODAY)
    assert qfirst == date(2026, 10, 1) and pqfirst == date(2026, 7, 1)


def test_kpis_come_from_the_patients_of_each_sede(app):
    norte, sur = _sede(), _sede()
    therapist = _user('terapista')
    therapist.assigned_sedes.append(norte)
    a, b = _user('jugador', norte), _user('jugador', norte)
    other = _user('jugador', sur)

    # Octubre (periodo actual): 3 realizadas, 1 cancelada, 1 ausencia.
    _appt(therapist, a, datetime(2026, 10, 5, 15))
    _appt(therapist, a, datetime(2026, 10, 12, 15), attendance='absent')
    _appt(therapist, b, datetime(2026, 10, 6, 15))
    _appt(therapist, b, datetime(2026, 10, 7, 15), status='cancelled', attendance='pending')
    # Septiembre (anterior): solo A se atendió -> continuidad 100 %.
    _appt(therapist, a, datetime(2026, 9, 8, 15))
    # Otra sede: no debe sumar.
    _appt(therapist, other, datetime(2026, 10, 5, 16))
    db.session.add_all(
        [
            Payment(patient_id=a.id, amount=150, date=datetime(2026, 10, 5, 16), method='yape', status='completed'),
            Payment(patient_id=b.id, amount=90, date=datetime(2026, 10, 6, 16), method='yape', status='pending'),
            Payment(patient_id=other.id, amount=999, date=datetime(2026, 10, 6, 16), method='yape'),
        ]
    )
    contract = Contract(patient_id=b.id, name='Plan', total_amount=400, installment_amount=200)
    db.session.add(contract)
    db.session.flush()
    db.session.add_all(
        [
            Installment(contract_id=contract.id, number=1, due_date=date(2026, 10, 10), amount=200, paid_amount=100),
            Installment(contract_id=contract.id, number=2, due_date=date(2026, 11, 10), amount=200),
        ]
    )
    db.session.commit()

    data, k, card = _card(norte.id)
    assert data['range'] == {'from': '2026-10-01', 'to': '2026-10-20'}
    assert k['revenue']['value'] == 150  # solo pagos confirmados de pacientes de la sede
    assert k['sessions_done']['value'] == 3
    assert k['cancel_rate']['value'] == 25.0
    assert k['attendance']['value'] == 66.7  # 2 presentes de 3 con asistencia marcada
    assert k['active_patients']['value'] == 2
    assert k['retention']['value'] == 100.0
    assert k['collection']['value'] == 50.0  # vencían 200, se pagaron 100
    assert k['overdue']['value'] == 100.0  # la cuota de noviembre aún no vence
    assert k['ticket']['value'] == 50.0
    assert k['therapists']['value'] == 1 and k['load']['value'] == 2.0
    assert k['accuracy']['value'] is None and k['accuracy']['status'] == 'none'  # sin datos, no un 0
    assert k['sessions_done']['previous'] == 1
    assert len(k['revenue']['trend']) == 6 and k['revenue']['trend'][-1] == 150
    assert k['collection']['status'] == 'bad' and k['cancel_rate']['status'] == 'bad'
    assert {p['key'] for p in card['perspectives']} == {'financial', 'patients', 'process', 'growth'}

    _, k_sur, _ = _card(sur.id)
    assert k_sur['revenue']['value'] == 999 and k_sur['sessions_done']['value'] == 1


def test_targets_are_saved_and_change_the_traffic_light(app):
    sede = _sede()
    therapist = _user('terapista')
    p = _user('jugador', sede)
    for day in (5, 6, 7, 8):
        _appt(therapist, p, datetime(2026, 10, day, 15), status='cancelled' if day == 8 else 'completed')
    db.session.commit()
    _, k, _ = _card(sede.id)
    assert k['cancel_rate']['value'] == 25.0 and k['cancel_rate']['status'] == 'bad'

    bsc.save_targets({'cancel_rate': 30})
    _, k, _ = _card(sede.id)
    assert k['cancel_rate']['target'] == 30 and k['cancel_rate']['status'] == 'good'

    try:
        bsc.save_targets({'attendance': 140})
        raise AssertionError('debió rechazar un porcentaje mayor a 100')
    except ValueError:
        db.session.rollback()


def test_endpoint_requires_admin_and_returns_the_scorecard(client, app):
    admin, patient = _user('admin'), _user('jugador')
    h = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
    r = client.get('/api/admin/sedes/scorecard?period=quarter', headers=h)
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body['success'] and body['period'] == 'quarter' and len(body['perspectives']) == 4

    hp = {'Authorization': 'Bearer ' + create_access_token(identity=str(patient.id))}
    assert client.get('/api/admin/sedes/scorecard', headers=hp).status_code == 403
    r = client.put('/api/admin/sedes/scorecard/targets', json={'targets': {'attendance': 90}}, headers=h)
    assert r.status_code == 200 and r.get_json()['targets']['attendance'] == 90
