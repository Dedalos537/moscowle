"""Recordatorios de sesion: solo se dan por enviados si algun canal los entrego.
Antes reminder_d1_sent/d0_sent se marcaban igual aunque WhatsApp y SMS fallaran
(puente caido, sin proveedor) y el recordatorio se perdia sin reintento."""

import random
import uuid
from datetime import datetime, time, timedelta

import pytest

from app.extensions import db
from app.models import Appointment, User
from app.services.session_reminder_service import LIMA_TZ, SessionReminderService


class _Messaging:
    def __init__(self, whatsapp=False, sms=False):
        self.whatsapp, self.sms, self.calls = whatsapp, sms, []

    def is_available(self):
        return True

    def send_whatsapp_message(self, phone, body):
        self.calls.append(('wa', phone))
        return self.whatsapp

    def send_sms_message(self, phone, body):
        self.calls.append(('sms', phone))
        return {'ok': self.sms}


def _tomorrow_appointment(session):
    tag = uuid.uuid4().hex[:8]
    therapist = User(username=f't{tag}', email=f't{tag}@rem.test', password='x', role='terapista')
    phone = '9' + ''.join(random.choices('0123456789', k=8))
    patient = User(username=f'p{tag}', email=f'p{tag}@rem.test', password='x', role='jugador', phone=phone)
    session.add_all([therapist, patient])
    session.flush()
    tomorrow = datetime.now(LIMA_TZ).date() + timedelta(days=1)
    appt = Appointment(
        therapist_id=therapist.id,
        patient_id=patient.id,
        start_time=datetime.combine(tomorrow, time(15, 0)),
        status='scheduled',
    )
    session.add(appt)
    session.commit()
    appt.test_phone = phone
    return appt


def _run(messaging):
    svc = SessionReminderService()
    svc.messaging = messaging
    return svc.run()


@pytest.mark.parametrize(
    'whatsapp,sms,expected',
    [(False, False, False), (True, False, True), (False, True, True), (True, True, True)],
)
def test_reminder_marked_sent_only_if_a_channel_delivered(session, whatsapp, sms, expected):
    appt = _tomorrow_appointment(session)
    _run(_Messaging(whatsapp=whatsapp, sms=sms))
    db.session.expire_all()
    assert bool(Appointment.query.get(appt.id).reminder_d1_sent) is expected


def _sent_to(messaging, phone):
    return [c for c in messaging.calls if c[0] == 'wa' and phone in c[1]]


def test_failed_reminder_is_retried_on_next_run(session):
    appt = _tomorrow_appointment(session)
    _run(_Messaging())  # todo falla: queda pendiente
    retry = _Messaging(whatsapp=True)
    _run(retry)
    db.session.expire_all()
    assert Appointment.query.get(appt.id).reminder_d1_sent is True
    assert len(_sent_to(retry, appt.test_phone)) == 1


def test_delivered_reminder_is_not_resent(session):
    appt = _tomorrow_appointment(session)
    _run(_Messaging(whatsapp=True))
    again = _Messaging(whatsapp=True)
    _run(again)
    assert _sent_to(again, appt.test_phone) == []
