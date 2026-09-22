import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app

from app.extensions import db
from app.models import Appointment, User
from app.services.sms_whatsapp_service import SMSWhatsAppService

logger = logging.getLogger(__name__)

LIMA_TZ = ZoneInfo('America/Lima')


class SessionReminderService:
    """Recordatorios de sesión: D-1, D-0 (WhatsApp + SMS al apoderado) y aviso de renovación."""

    def __init__(self):
        self.messaging = SMSWhatsAppService()

    def _recipient_phone(self, patient):
        contact = (patient.guardian_contact or '').strip() or (patient.phone or '').strip()
        return contact

    def _local_date(self, dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=LIMA_TZ)
        return dt.astimezone(LIMA_TZ).date()

    def run(self):
        if not self.messaging.is_available():
            current_app.logger.warning('Session reminders: no messaging service available')
            return {'sent_whatsapp': 0, 'sent_sms': 0, 'renewals': 0, 'error': 'no_messaging'}

        today_local = datetime.now(LIMA_TZ).date()
        tomorrow_local = today_local + timedelta(days=1)

        upcoming = (
            Appointment.query.filter(
                Appointment.status == 'scheduled',
                Appointment.start_time >= datetime.now(LIMA_TZ).astimezone().replace(tzinfo=None),
            )
            .order_by(Appointment.start_time.asc())
            .all()
        )

        counts = {'sent_whatsapp': 0, 'sent_sms': 0, 'renewals': 0}
        by_patient = {}

        for appt in upcoming:
            local_date = self._local_date(appt.start_time)
            if local_date is None:
                continue
            patient = appt.patient
            if not patient:
                continue
            phone = self._recipient_phone(patient)
            if not phone:
                continue
            by_patient.setdefault(patient.id, {'appointments': []})['appointments'].append(appt)

            if local_date == tomorrow_local and not appt.reminder_d1_sent:
                self._send_reminder(
                    phone,
                    patient,
                    appt,
                    'Mañana',
                    counts,
                )
                appt.reminder_d1_sent = True

            if local_date == today_local and not appt.reminder_d0_sent:
                self._send_reminder(
                    phone,
                    patient,
                    appt,
                    'Hoy',
                    counts,
                )
                appt.reminder_d0_sent = True

        self._send_renewal_notices(by_patient, counts)

        db.session.commit()
        return counts

    def _send_reminder(self, phone, patient, appt, prefix, counts):
        therapist = appt.therapist
        therapist_name = therapist.username if therapist else ''
        location = (appt.location or '').strip()
        start_local = self._local_date(appt.start_time)
        time_str = (
            appt.start_time.astimezone(LIMA_TZ).strftime('%H:%M')
            if appt.start_time.tzinfo
            else appt.start_time.strftime('%H:%M')
        )
        date_str = start_local.strftime('%d/%m') if start_local else ''

        body = (
            f'Hola {patient.username},\n\n'
            f'Recordatorio: tu sesión de terapia es {prefix.lower()} {date_str} a las {time_str}'
            + (f' en {location}.' if location else '.')
            + ('\n\nTe esperamos. Centro de Terapias')
        )
        self._dispatch(phone, body, counts)

    def _send_renewal_notices(self, by_patient, counts):
        today_local = datetime.now(LIMA_TZ).date()
        for pid, info in by_patient.items():
            futs = [
                a
                for a in info['appointments']
                if (self._local_date(a.start_time) or today_local) >= today_local and a.status == 'scheduled'
            ]
            remaining = len(futs)
            patient = futs[0].patient if futs else User.query.get(pid)
            if not patient or remaining != 2:
                if patient and patient.renewal_notified_count == 2:
                    patient.renewal_notified_count = None
                continue
            if patient.renewal_notified_count == 2:
                continue
            phone = self._recipient_phone(patient)
            if not phone:
                continue
            body = (
                f'Hola {patient.username},\n\n'
                f'Quedan {remaining} sesiones de tu bloque actual.\n\n'
                'Te recomendamos renovar para no interrumpir tu terapia.\n\n'
                'Centro de Terapias'
            )
            self._dispatch(phone, body, counts)
            patient.renewal_notified_count = 2

    def _dispatch(self, phone, body, counts):
        if self.messaging.send_whatsapp_message(phone, body):
            counts['sent_whatsapp'] += 1
        if self.messaging.send_sms_message(phone, body):
            counts['sent_sms'] += 1
