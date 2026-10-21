"""Audiencia por rol: un aviso técnico (latencia, servidor) no le llega a un terapeuta."""

import uuid
from types import SimpleNamespace

from app.extensions import db
from app.models import User
from app.services import audience


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@gmail.com', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def test_latency_incident_never_reaches_a_therapist(app):
    latency = SimpleNamespace(categoria='SOFTWARE', subcategoria='api_timeout')
    therapist, admin = _user('terapista'), _user('admin')
    assert audience.is_technical_incident(latency)
    assert not audience.may_receive_incident(therapist, latency)
    assert audience.may_receive_incident(admin, latency)
    operational = SimpleNamespace(categoria='OPERACIONES', subcategoria='agenda')
    assert audience.may_receive_incident(therapist, operational)


def test_responsible_therapist_gets_no_email_for_a_technical_incident(app):
    from app.services.incident_notification_service import IncidentNotificationService

    therapist = _user('terapista')
    inc = SimpleNamespace(categoria='RED', subcategoria='latencia', responsable_id=therapist.id)
    assert IncidentNotificationService._get_responsible_email(inc) is None
    inc.categoria, inc.subcategoria = 'OPERACIONES', 'agenda'
    assert IncidentNotificationService._get_responsible_email(inc) == therapist.email


def test_server_alert_notification_is_skipped_for_non_staff(app, monkeypatch):
    from app.services import notification_service as ns

    monkeypatch.setattr(ns.socketio, 'emit', lambda *a, **k: None)
    svc = ns.NotificationService()
    therapist, admin = _user('terapista'), _user('admin')
    meta = {'alertname': 'ServicioCriticoCaido'}
    assert svc.create_notification(therapist.id, 'Servidor caído', kind='server.alert', metadata_json=meta) is None
    assert svc.create_notification(admin.id, 'Servidor caído', kind='server.alert', metadata_json=meta) is not None
    # Los avisos sin regla de rol (p. ej. mensajes) siguen llegando a cualquiera.
    assert svc.create_notification(therapist.id, 'Hola', category='message') is not None


def test_operational_escalation_finds_a_therapist(app):
    from app.services.incident_escalation_service import IncidentEscalationService

    _user('terapista')
    inc = SimpleNamespace(categoria='OPERACIONES')
    target = IncidentEscalationService._get_escalation_target(inc)
    assert target is not None and target.role == 'terapista'  # antes buscaba «terapeuta» y nunca lo hallaba
