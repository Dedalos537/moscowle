"""Correos: solo a direcciones reales (apoderado o propia), sin contraseñas escritas y sin envíos rotos."""

import uuid
from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import bcrypt, db
from app.models import Appointment, User
from app.services import email_service
from app.services.email_service import EmailService, is_real_email, recipient_for


def _user(role='jugador', email=None, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(
        username=f'{role[:3]}{tag}',
        email=email or f'{tag}@correo.pe',
        password=bcrypt.generate_password_hash('x' * 10).decode('utf-8'),
        role=role,
        **kw,
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def outbox(app, monkeypatch):
    """Activa el correo y captura lo que se enviaría (sin tocar Gmail)."""
    sent = []
    monkeypatch.setitem(app.config, 'MAIL_USERNAME', 'avisos@centro.pe')
    monkeypatch.setitem(app.config, 'MAIL_PASSWORD', 'x')
    monkeypatch.setattr(email_service.mail, 'send', lambda msg: sent.append(msg))
    return sent


def test_generated_addresses_are_not_real():
    assert is_real_email('mama@gmail.com')
    for fake in (
        'noemail_ab12cd34@local',
        'temp_123@algo.pe',
        'x@localhost',
        'a@servidor.local',
        '',
        None,
        'sin-arroba',
    ):
        assert not is_real_email(fake), fake


def test_patient_mail_goes_to_the_guardian_then_to_a_real_own_email(app):
    with_guardian = _user(email=f'noemail_{uuid.uuid4().hex[:8]}@local', guardian_contact='papa@gmail.com')
    own_only = _user(email=f'{uuid.uuid4().hex[:6]}@hotmail.com')
    nothing = _user(email=f'noemail_{uuid.uuid4().hex[:8]}@local')
    assert recipient_for(with_guardian) == 'papa@gmail.com'
    assert recipient_for(own_only) == own_only.email
    assert recipient_for(nothing) is None  # solo aviso en la app
    therapist = _user('terapista', guardian_contact='otro@gmail.com')
    assert recipient_for(therapist) == therapist.email  # el apoderado es solo para pacientes


def test_nothing_is_sent_to_a_generated_address(app, outbox):
    ok = EmailService.send_notification_email('Hola', [f'noemail_{uuid.uuid4().hex[:8]}@local'], body='x')
    assert ok is False and outbox == []
    real = _user(email=f'{uuid.uuid4().hex[:6]}@gmail.com')
    assert EmailService.send_notification_email('Hola', [real.email], body='x') is True and len(outbox) == 1


def test_send_email_now_exists_for_the_three_callers(app, outbox):
    """Recordatorio manual, renovación y cambio por admin llamaban a send_email, que no existía."""
    to = f'{uuid.uuid4().hex[:6]}@gmail.com'
    assert EmailService.send_email(to, 'Recordatorio', 'Cuerpo') is True
    assert EmailService.send_email(subject='Renovación', recipients=[to], text_body='Cuerpo') is True
    assert [m.subject for m in outbox] == ['Recordatorio', 'Renovación']


def test_welcome_and_password_change_never_include_the_password(app, outbox):
    u = _user(email=f'{uuid.uuid4().hex[:6]}@gmail.com', login_code='PCJP' + uuid.uuid4().hex[:4].upper())
    EmailService.send_welcome_email(u.email, 'Secreta#2026', u.username)
    EmailService.send_password_change_email(u.email, 'Otra#2026', u.username)
    bodies = [m.body for m in outbox]
    assert len(bodies) == 2 and all('Secreta#2026' not in b and 'Otra#2026' not in b for b in bodies)
    assert u.login_code in bodies[0] and '/auth/set-password?t=' in bodies[0]


def test_set_password_link_works_once(app, client):
    from app.utils.email_tokens import make_set_password_token

    u = _user(email=f'{uuid.uuid4().hex[:6]}@gmail.com')
    token = make_set_password_token(u)
    assert client.get('/api/auth/set-password', query_string={'t': token}).get_json()['success'] is True
    assert client.post('/api/auth/set-password', json={'token': token, 'new_password': 'corta'}).status_code == 400
    r = client.post('/api/auth/set-password', json={'token': token, 'new_password': 'NuevaClave2026'})
    assert r.status_code == 200
    db.session.refresh(u)
    assert bcrypt.check_password_hash(u.password, 'NuevaClave2026')
    again = client.post('/api/auth/set-password', json={'token': token, 'new_password': 'OtraClave2026'})
    assert again.status_code == 400  # un solo uso
    assert client.get('/api/auth/set-password', query_string={'t': 'basura'}).status_code == 400


def test_batch_sessions_send_one_summary_per_patient(app, outbox):
    from app.routes.admin.sessions import _email_session_summary

    therapist = _user('terapista')
    patient = _user(guardian_contact='mama@gmail.com')
    no_mail = _user(email=f'noemail_{uuid.uuid4().hex[:8]}@local')
    start = datetime.utcnow() + timedelta(days=2)
    ids = []
    for p in (patient, patient, patient, no_mail):
        a = Appointment(
            therapist_id=therapist.id, patient_id=p.id, title='Terapia', start_time=start, status='scheduled'
        )
        db.session.add(a)
        db.session.flush()
        ids.append(a.id)
        start += timedelta(days=2)
    db.session.commit()
    assert _email_session_summary(ids) == 1  # el paciente sin correo real no recibe nada
    assert len(outbox) == 1 and outbox[0].recipients == ['mama@gmail.com']
    assert outbox[0].body.count('• ') == 3 and 'Se programaron 3' in outbox[0].subject


def test_manual_debt_reminder_reports_when_there_is_no_real_email(app, client, monkeypatch):
    """Antes decía «Recordatorio enviado» aunque el correo nunca salía (send_email no existía)."""
    from app.services.financial_service import FinancialService

    admin = _user('admin')
    patient = _user(email=f'noemail_{uuid.uuid4().hex[:8]}@local')
    monkeypatch.setattr(
        FinancialService,
        'get_patient_overdue_info',
        lambda self, pid: {'name': patient.username, 'amount': 150.0, 'days_overdue': 5, 'due_date': None},
    )
    headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
    r = client.post(
        '/api/admin/send-payment-reminder',
        json={'patient_id': patient.id, 'patient_email': patient.email, 'channel': 'email'},
        headers=headers,
    )
    assert r.status_code == 400 and 'correo real' in r.get_data(as_text=True)
