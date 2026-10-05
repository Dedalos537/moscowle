import json
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token


def _auth_headers(user_id):
    token = create_access_token(identity=str(user_id))
    return {'Authorization': f'Bearer {token}'}


def _overview(client, admin):
    resp = client.get('/api/admin/progress-overview', headers=_auth_headers(admin.id))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    return data


def test_progress_overview_returns_real_data(client, session):
    """La base de pruebas se comparte entre tests (los commit no se revierten), asi que se usan
    correos unicos y se comprueban las DIFERENCIAS que produce este escenario, no totales absolutos."""
    import uuid

    from app.models import Appointment, SessionAudit, User

    tag = uuid.uuid4().hex[:8]
    admin = User(username=f'Admin{tag}', email=f'admin{tag}@test.com', role='admin', is_active=True, password='x')
    tera_name = f'Tera{tag}'
    terapista = User(username=tera_name, email=f't{tag}@test.com', role='terapista', is_active=True, password='x')
    paciente = User(username=f'Pac{tag}', email=f'p{tag}@test.com', role='jugador', is_active=True, password='x')
    session.add_all([admin, terapista, paciente])
    session.commit()

    before = _overview(client, admin)

    now = datetime.utcnow()
    a1 = Appointment(
        patient_id=paciente.id,
        therapist_id=terapista.id,
        title='S1',
        start_time=now - timedelta(days=2),
        status='completed',
    )
    a2 = Appointment(
        patient_id=paciente.id,
        therapist_id=terapista.id,
        title='S2',
        start_time=now - timedelta(days=1),
        status='scheduled',
    )
    session.add_all([a1, a2])
    session.flush()

    au1 = SessionAudit(
        appointment_id=a1.id,
        planned_text='## Objetivo A\n- Ejercicio de atencion',
        transcript_text='Sesion completa realizada',
        audit_status='completed',
        audit_score=85.0,
        audit_report_json=json.dumps(
            {
                'objectives': [
                    {'name': 'Objetivo A', 'classification': 'logrado'},
                    {'name': 'Ejercicio de atencion', 'classification': 'logrado'},
                ]
            }
        ),
    )
    session.add(au1)
    session.commit()

    after = _overview(client, admin)
    assert after['sessions']['completed'] == before['sessions']['completed'] + 1
    assert after['sessions']['scheduled'] == before['sessions']['scheduled'] + 1
    assert after['objectives']['achieved'] == before['objectives']['achieved'] + 2
    assert after['objectives']['total'] == before['objectives']['total'] + 2
    assert after['notes']['transcribed'] == before['notes']['transcribed'] + 1
    assert after['audited_sessions'] == before['audited_sessions'] + 1
    entries = [t for t in after['therapists'] if t['therapist_name'] == tera_name]
    assert len(entries) == 1


def test_progress_overview_forbids_terapista(client, session):
    import uuid

    from app.models import User

    tag = uuid.uuid4().hex[:8]
    terapista = User(username=f'Tera2{tag}', email=f't2{tag}@test.com', role='terapista', is_active=True, password='x')
    session.add(terapista)
    session.commit()

    resp = client.get('/api/admin/progress-overview', headers=_auth_headers(terapista.id))
    assert resp.status_code == 403
