import json
from datetime import UTC, datetime

from app.extensions import bcrypt
from app.models import Appointment, SessionMetrics, User


def test_save_game_mario_payload_e2e(app, client, session, db):
    from app.extensions import db as _db

    tera = User(
        username='tera_m',
        email='tera_m@test.com',
        password=bcrypt.generate_password_hash('pass1234').decode('utf-8'),
        role='terapista',
    )
    pac = User(
        username='paci_m',
        email='paci_m@test.com',
        password=bcrypt.generate_password_hash('pass1234').decode('utf-8'),
        role='jugador',
    )
    _db.session.add_all([tera, pac])
    _db.session.commit()

    r = client.post('/api/login', json={'email': 'paci_m@test.com', 'password': 'pass1234'})
    assert r.status_code == 200, r.data[:200]

    appt = Appointment(
        patient_id=pac.id,
        therapist_id=tera.id,
        games='["Mario Forever"]',
        status='pending',
        start_time=datetime.now(UTC),
    )
    _db.session.add(appt)
    _db.session.commit()

    payload = {
        'game_name': 'Mario Forever',
        'session_id': appt.id,
        'accuracy': 33,
        'avg_time': 22,
        'level_reached': 1,
        'deaths': 2,
        'coins': 5,
        'score': 8800,
        'duration_s': 67,
        'details': {
            'launcher': 'mario_forever',
            'coins_total': 15,
            'coins': 5,
            'level': 1,
            'finished': True,
            'duration_s': 67,
        },
    }
    r = client.post('/api/save_game', json=payload)
    assert r.status_code == 200, r.data[:200]
    body = r.get_json()
    assert body['status'] == 'ok'

    m = SessionMetrics.query.filter_by(session_id=appt.id).first()
    assert m is not None
    assert m.game_name == 'Mario Forever'
    assert m.accurracy == 33
    assert m.avg_time == 22
    assert m.details is not None
    det = json.loads(m.details)
    assert det['level_reached'] == 1
    assert det['deaths'] == 2
    assert det['coins'] == 5
    assert det['score'] == 8800
    assert det['duration_s'] == 67

    reappt = Appointment.query.get(appt.id)
    assert reappt.status == 'completed'
    assert reappt.end_time is not None
