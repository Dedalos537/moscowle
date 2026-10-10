"""Flujo de sesiones del terapista: lo que la pantalla de Sesiones lee y escribe."""

import uuid
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Appointment, User
from app.utils import get_user_today_utc_range


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@ts.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def _auth(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def test_stats_count_shared_patients_and_all_of_today(client, app):
    therapist, other = _user('terapista'), _user('terapista')
    shared, own = _user('jugador'), _user('jugador')
    # Paciente compartido: su assigned_therapist_id apunta al otro terapeuta, pero el vínculo N:M incluye a ambos.
    shared.assigned_therapist_id = other.id
    shared.therapists.extend([other, therapist])
    own.therapists.append(therapist)
    start, _ = get_user_today_utc_range(therapist)
    for hours, status in ((1, 'completed'), (2, 'scheduled'), (3, 'cancelled')):
        db.session.add(
            Appointment(
                therapist_id=therapist.id, patient_id=own.id, start_time=start + timedelta(hours=hours), status=status
            )
        )
    db.session.commit()

    r = client.get('/therapist/api/dashboard-stats', headers=_auth(therapist))
    assert r.status_code == 200
    body = r.get_json()
    assert body['active_patients'] == 2
    assert body['sessions_today'] == 2  # realizada + programada; la cancelada no cuenta


def test_quick_complete_records_attendance_and_who_changed_it(client, app):
    therapist, patient = _user('terapista'), _user('jugador')
    appt = Appointment(therapist_id=therapist.id, patient_id=patient.id, start_time=datetime(2026, 10, 6, 15))
    db.session.add(appt)
    db.session.commit()

    r = client.put(
        f'/api/sessions/{appt.id}', json={'status': 'completed', 'attendance': 'present'}, headers=_auth(therapist)
    )
    assert r.status_code == 200, r.get_json()
    db.session.refresh(appt)
    db.session.refresh(patient)
    assert appt.status == 'completed' and appt.attendance == 'present'
    assert appt.status_changed_at is not None and appt.status_changed_by == therapist.id
    assert patient.sessions_attended == 1


def test_naive_times_from_the_edit_form_are_lima_time(client, app):
    therapist, patient = _user('terapista'), _user('jugador')
    appt = Appointment(therapist_id=therapist.id, patient_id=patient.id, start_time=datetime(2026, 10, 6, 15))
    db.session.add(appt)
    db.session.commit()
    r = client.put(
        f'/api/sessions/{appt.id}',
        json={'start_time': '2026-10-07T10:00', 'end_time': '2026-10-07T11:00'},
        headers=_auth(therapist),
    )
    assert r.status_code == 200, r.get_json()
    db.session.refresh(appt)
    assert appt.start_time == datetime(2026, 10, 7, 15, 0)  # 10:00 Lima = 15:00 UTC


def test_weekly_report_without_week_returns_the_latest(client, app):
    therapist, patient = _user('terapista'), _user('jugador')
    patient.therapists.append(therapist)
    db.session.add(Appointment(therapist_id=therapist.id, patient_id=patient.id, start_time=datetime(2026, 10, 6, 15)))
    db.session.commit()
    h = _auth(therapist)
    r = client.post(
        '/api/reports/generate-weekly', json={'patient_id': patient.id, 'week_start': '2026-10-05'}, headers=h
    )
    assert r.status_code == 200, r.get_json()
    r = client.get(f'/api/reports/weekly/{patient.id}', headers=h)
    assert r.get_json()['exists'] is True and r.get_json()['report']['week_start'] == '2026-10-05'


def test_insights_report_uses_real_numbers(client, app):
    from app.models.appointment import SessionMetrics

    therapist, other = _user('terapista'), _user('terapista')
    a, b = _user('jugador'), _user('jugador')
    a.therapists.append(therapist)
    b.therapists.append(therapist)
    # Semana del 5 oct (Lima): 2 realizadas (1 presente, 1 ausente), 1 cancelada; otra del colega no cuenta.
    db.session.add_all(
        [
            Appointment(
                therapist_id=therapist.id,
                patient_id=a.id,
                start_time=datetime(2026, 10, 6, 15),
                end_time=datetime(2026, 10, 6, 15, 45),
                status='completed',
                attendance='present',
            ),
            Appointment(
                therapist_id=therapist.id,
                patient_id=b.id,
                start_time=datetime(2026, 10, 7, 15),
                end_time=datetime(2026, 10, 7, 16, 15),
                status='completed',
                attendance='absent',
            ),
            Appointment(
                therapist_id=therapist.id, patient_id=b.id, start_time=datetime(2026, 10, 8, 15), status='cancelled'
            ),
            Appointment(
                therapist_id=other.id, patient_id=a.id, start_time=datetime(2026, 10, 8, 16), status='completed'
            ),
        ]
    )
    # Precisión de A en descenso (90, 88 -> 50, 40) y la IA sugiere apoyo al final; 0.8 se lee como 80 %.
    for day, acc, pred in ((5, 90, 1), (6, 88, 0), (7, 50, 2), (8, 40, 2)):
        db.session.add(
            SessionMetrics(
                user_id=a.id,
                game_name='Memoria',
                accurracy=acc,
                avg_time=3,
                prediction=pred,
                date=datetime(2026, 10, day, 16),
            )
        )
    db.session.add(
        SessionMetrics(
            user_id=b.id, game_name='Colores', accurracy=0.8, avg_time=2, prediction=1, date=datetime(2026, 10, 6, 16)
        )
    )
    db.session.commit()

    r = client.get('/therapist/api/insights?from=2026-10-05&to=2026-10-11', headers=_auth(therapist))
    assert r.status_code == 200, r.get_json()
    d = r.get_json()['data']
    k = d['kpis']
    assert k['sessions_done'] == 2 and k['cancelled'] == 1 and k['attendance'] == 50.0
    assert k['avg_minutes'] == 60  # (45 + 75) / 2
    assert k['games_played'] == 5 and k['accuracy'] == 69.6  # (90+88+50+40+80)/5
    assert d['weekly'] == [
        {
            'week': '2026-10-05',
            'sessions_done': 2,
            'sessions_scheduled': 2,
            'attendance': 50.0,
            'accuracy': 69.6,
            'games': 5,
        }
    ]
    pa = next(p for p in d['patients'] if p['id'] == a.id)
    assert pa['trend'] == -44.0 and pa['recommendation'] == 'apoyo'
    assert 'precisión en descenso' in pa['attention'] and 'la IA sugiere apoyo' in pa['attention']
    assert d['patients'][0]['id'] == a.id  # los que requieren atención van primero
    recs = {x['key']: x['count'] for x in d['ai']['recommendations']}
    assert recs == {'avanzar': 2, 'mantener': 1, 'apoyo': 2}
    assert {g['game'] for g in d['ai']['by_game']} == {'Memoria', 'Colores'}
    assert 'model_confidence' not in d['ai']  # nada inventado


def test_dashboard_announces_the_next_session_when_today_is_free(client, app):
    therapist, patient = _user('terapista'), _user('jugador')
    db.session.add(
        Appointment(
            therapist_id=therapist.id,
            patient_id=patient.id,
            title='Lenguaje',
            start_time=datetime.utcnow() + timedelta(days=3),
            status='scheduled',
        )
    )
    db.session.commit()
    r = client.get('/api/therapist/dashboard', headers=_auth(therapist))
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    data = body.get('data', body)
    assert data['next_session'] is None or data['next_session']['title'] == 'Lenguaje'
    if data['next_session'] is None:
        assert data['upcoming']['patient'] == patient.username and data['upcoming']['start']
