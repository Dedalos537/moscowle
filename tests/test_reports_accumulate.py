"""«Acumular reportes»: acumula la semana elegida, en hora de Lima, para todos los pacientes con sesiones."""

import uuid
from datetime import date, datetime

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Appointment, DailyReport, User, WeeklyReport
from app.services.report_service import utc_bounds


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@acc.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def test_lima_day_bounds():
    start, end = utc_bounds(date(2026, 10, 5))
    assert start == datetime(2026, 10, 5, 5, 0) and end == datetime(2026, 10, 6, 5, 0)


def test_accumulate_creates_weekly_reports_for_the_chosen_week(client, app):
    admin, therapist, patient = _user('admin'), _user('terapista'), _user('jugador')
    # Lunes 5 oct 2026, 20:00 en Lima = martes 6 oct 01:00 UTC. El paciente NO está asociado al terapeuta.
    db.session.add(
        Appointment(
            therapist_id=therapist.id,
            patient_id=patient.id,
            title='Lenguaje',
            start_time=datetime(2026, 10, 6, 1, 0),
            end_time=datetime(2026, 10, 6, 2, 0),
            status='completed',
        )
    )
    db.session.commit()
    h = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
    r = client.post(
        '/admin/api/reports/accumulate', json={'week_start': '2026-10-07'}, headers=h
    )  # miércoles → semana del lunes 5
    body = r.get_json()
    assert r.status_code == 200 and body['week_start'] == '2026-10-05'
    assert body['weekly'] >= 1 and body['pairs'] >= 1
    assert WeeklyReport.query.filter_by(patient_id=patient.id, week_start=date(2026, 10, 5)).count() == 1
    daily = DailyReport.query.filter_by(patient_id=patient.id).all()
    assert [d.date for d in daily] == [date(2026, 10, 5)]  # día de Lima, no el día UTC


def test_accumulate_without_sessions_says_so(client, app):
    admin = _user('admin')
    h = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
    body = client.post('/admin/api/reports/accumulate', json={'week_start': '2020-01-06'}, headers=h).get_json()
    assert body['success'] and body['pairs'] == 0 and 'No hay sesiones' in body['message']


def test_strategic_report_returns_structured_metrics(client, app):
    from unittest.mock import patch

    admin = _user('admin')
    h = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
    with patch(
        'app.services.llm_automation_service.generate_weekly_report', return_value='## Recomendaciones\n- **Uno**'
    ):
        body = client.post('/admin/generate-ia-report', headers=h).get_json()
    assert body['success'] and '## Recomendaciones' in body['report']
    m = body['metrics']
    assert len(m['weekly_sessions']) == 8 and 'balance_30d' in m['financial']
    assert {'therapists', 'patients', 'total_sessions', 'sessions_this_month'} <= set(m['general'])
