import json
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token


def _auth_headers(user_id):
    token = create_access_token(identity=str(user_id))
    return {'Authorization': f'Bearer {token}'}


def test_progress_overview_returns_real_data(client, session):
    from app.models import Appointment, SessionAudit, User

    admin = User(username='Admin', email='admin@test.com', role='admin', is_active=True, password='x')
    terapista = User(username='Tera', email='t@test.com', role='terapista', is_active=True, password='x')
    paciente = User(username='Pac', email='p@test.com', role='jugador', is_active=True, password='x')
    session.add_all([admin, terapista, paciente])
    session.flush()

    now = datetime.utcnow()
    a1 = Appointment(patient_id=paciente.id, therapist_id=terapista.id, title='S1',
                     start_time=now - timedelta(days=2), status='completed')
    a2 = Appointment(patient_id=paciente.id, therapist_id=terapista.id, title='S2',
                     start_time=now - timedelta(days=1), status='scheduled')
    session.add_all([a1, a2])
    session.flush()

    au1 = SessionAudit(appointment_id=a1.id, planned_text='## Objetivo A\n- Ejercicio de atencion',
                       transcript_text='Sesion completa realizada', audit_status='completed', audit_score=85.0,
                       audit_report_json=json.dumps({'objectives': [
                           {'name': 'Objetivo A', 'classification': 'logrado'},
                           {'name': 'Ejercicio de atencion', 'classification': 'logrado'},
                       ]}))
    session.add(au1)
    session.commit()

    resp = client.get('/api/admin/progress-overview', headers=_auth_headers(admin.id))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['sessions']['completed'] == 1
    assert data['sessions']['scheduled'] == 1
    assert data['objectives']['achieved'] == 2
    assert data['objectives']['total'] == 2
    assert data['notes']['transcribed'] == 1
    assert data['audited_sessions'] == 1
    assert len(data['therapists']) == 1
    assert data['therapists'][0]['therapist_name'] == 'Tera'


def test_progress_overview_forbids_terapista(client, session):
    from app.models import User

    terapista = User(username='Tera2', email='t2@test.com', role='terapista', is_active=True, password='x')
    session.add(terapista)
    session.commit()

    resp = client.get('/api/admin/progress-overview', headers=_auth_headers(terapista.id))
    assert resp.status_code == 403
