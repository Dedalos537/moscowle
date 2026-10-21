"""Correos de incidencias: preferencia por usuario, sin duplicar alertas automáticas y banners que se retiran."""

import uuid
from datetime import datetime, timedelta

from app.extensions import db
from app.models import User
from app.models.incidente import Incidente
from app.models.notification import UserNotificationPreference as Pref
from app.models.notification_group import NotificationGroup, NotificationItem
from app.services import incident_notification_service as ins
from app.services.incident_detection_service import IncidentDetectionService


def _admin(level=None):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'adm{tag}', email=f'{tag}@gmail.com', password='x', role='admin')
    db.session.add(u)
    db.session.commit()
    if level:
        db.session.add(Pref(user_id=u.id, incident_email=level))
        db.session.commit()
    return u


def _inc(evidencia='MANUAL', titulo=None, estado='NUEVO'):
    inc = Incidente(
        titulo=titulo or f'Caso {uuid.uuid4().hex[:6]}',
        descripcion='x',
        user_id=1,
        categoria='SOFTWARE',
        estado=estado,
        evidencia_original='x',
        evidencia_tipo=evidencia,
        fecha_creacion=datetime.utcnow(),
        fecha_limite_sla=datetime.utcnow() + timedelta(hours=4),
    )
    db.session.add(inc)
    db.session.commit()
    return inc


def test_levels_decide_who_gets_which_email(app):
    auto, manual = _inc('MONITORING'), _inc('MANUAL')
    off, important, every = _admin('off'), _admin('important'), _admin('all')
    assert not ins.wants_incident_email(off, 'new', manual)
    assert ins.wants_incident_email(important, 'new', manual)
    assert not ins.wants_incident_email(important, 'new', auto)  # latencia y demás: solo en la campana
    assert not ins.wants_incident_email(important, 'escalation', auto)
    assert ins.wants_incident_email(every, 'escalation', auto)
    assert ins.wants_incident_email(_admin(), 'new', manual)  # sin preferencia guardada: «solo importantes»


def test_admin_recipients_respect_preferences(app, monkeypatch):
    off, every = _admin('off'), _admin('all')
    emails = ins.IncidentNotificationService._get_admin_emails('new', _inc('MONITORING'))
    assert every.email in emails and off.email not in emails


def test_open_automatic_incident_is_not_duplicated_when_escalated(app, monkeypatch):
    sent = []
    monkeypatch.setattr(
        ins.IncidentNotificationService, 'notify_new_incident', classmethod(lambda cls, i: sent.append(i))
    )
    titulo = f'Latencia API elevada {uuid.uuid4().hex[:4]}'
    first = IncidentDetectionService._create_incident(
        titulo=titulo, descripcion='a', categoria='SOFTWARE', evidencia_tipo='MONITORING', evidencia_original='p95'
    )
    first.estado = 'PENDIENTE_PROVEEDOR'  # escalada: antes la siguiente revisión creaba otra
    db.session.commit()
    again = IncidentDetectionService._create_incident(
        titulo=titulo, descripcion='b', categoria='SOFTWARE', evidencia_tipo='MONITORING', evidencia_original='p95'
    )
    assert again.id_incidente == first.id_incidente and again.descripcion == 'b'
    assert len(sent) == 1


def test_recently_resolved_automatic_incident_is_not_reopened(app, monkeypatch):
    monkeypatch.setattr(ins.IncidentNotificationService, 'notify_new_incident', classmethod(lambda cls, i: None))
    titulo = f'Latencia API elevada {uuid.uuid4().hex[:4]}'
    first = IncidentDetectionService._create_incident(
        titulo=titulo, descripcion='a', categoria='SOFTWARE', evidencia_tipo='MONITORING', evidencia_original='p95'
    )
    first.estado, first.fecha_resolucion = 'RESUELTO', datetime.utcnow()
    db.session.commit()
    again = IncidentDetectionService._create_incident(
        titulo=titulo, descripcion='a', categoria='SOFTWARE', evidencia_tipo='MONITORING', evidencia_original='p95'
    )
    assert again.id_incidente == first.id_incidente
    assert Incidente.query.filter_by(titulo=titulo).count() == 1


def test_resolving_clears_the_banner(app, monkeypatch):
    admin = _admin()
    inc = _inc('MONITORING')
    g = NotificationGroup(
        user_id=admin.id,
        group_key=f'alert:{inc.id_incidente}',
        category='alert',
        priority='urgent',
        title='Alertas Urgentes',
        count=1,
    )
    db.session.add(g)
    db.session.commit()
    db.session.add(
        NotificationItem(
            group_id=g.id, user_id=admin.id, message='Escalado', link=f'/admin/incidents/{inc.id_incidente}'
        )
    )
    db.session.commit()
    emitted = []
    monkeypatch.setattr('app.extensions.socketio.emit', lambda ev, data, room=None: emitted.append((ev, data, room)))

    ins.IncidentNotificationService.clear_resolved_alerts()
    assert db.session.get(NotificationGroup, g.id).is_read is False  # sigue abierta: el aviso se queda

    inc.estado = 'RESUELTO'
    db.session.commit()
    ins.IncidentNotificationService.clear_resolved_alerts()
    assert db.session.get(NotificationGroup, g.id).is_read is True
    assert ('notification:dismiss', g.id, f'user_{admin.id}') in [(e, d['ids'][0], r) for e, d, r in emitted]
