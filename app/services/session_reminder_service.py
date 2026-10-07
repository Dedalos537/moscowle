import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app

from app.extensions import db
from app.models import Appointment, User
from app.services import automation_settings
from app.services.messaging import MessagingService
from app.services.sms_whatsapp_service import SMSWhatsAppService

logger = logging.getLogger(__name__)

LIMA_TZ = ZoneInfo('America/Lima')


class _BridgeMessenger:
    """Canales reales del centro: WhatsApp por el puente (Baileys, el número vinculado por QR) y SMS por el gateway.

    Antes el recordatorio de WhatsApp usaba pywhatkit/Twilio, que en el servidor no existen, así que nunca salía por el
    número que el centro vinculó. Si el puente no está conectado se intenta el proveedor anterior como respaldo.
    """

    def __init__(self):
        self._sms = SMSWhatsAppService()

    def is_available(self):
        from app.services.whatsapp_service import whatsapp_service

        return bool(whatsapp_service.status().get('connected')) or self._sms.is_available()

    def send_whatsapp_message(self, phone, body):
        from app.services.whatsapp_service import whatsapp_service

        try:
            whatsapp_service.send_message(phone, body)
            return True
        except Exception as exc:
            logger.warning('WhatsApp (puente) no envió el recordatorio: %s', exc)
        return self._sms.send_whatsapp_message(phone, body)

    def send_sms_message(self, phone, body):
        return self._sms.send_sms_message(phone, body)

    def send_email(self, patient, subject, body):
        return MessagingService.send_email(patient, subject, body)


class SessionReminderService:
    """Recordatorios de sesión: D-1, D-0 (WhatsApp + SMS al apoderado) y aviso de renovación."""

    def __init__(self):
        self.messaging = _BridgeMessenger()

    def _recipient_phone(self, patient):
        # Mismo criterio que el CRM: el apoderado solo si trae un telefono,
        # porque guardian_contact puede traer un correo. Si no, el del
        # paciente.
        return MessagingService.resolve_phone(patient)

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

        counts = {'sent_whatsapp': 0, 'sent_sms': 0, 'sent_email': 0, 'renewals': 0}
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
            # Interruptor global / modo prueba: si no se puede avisar a este paciente, no se marca nada como enviado.
            if not any(
                automation_settings.allows(patient.id, 'sessions', ch)[0] for ch in ('whatsapp', 'sms', 'email')
            ):
                continue

            # Se marca como enviado SOLO si algun canal lo entrego: antes se marcaba
            # igual con el puente caido o sin proveedor y el recordatorio se perdia.
            if (
                local_date == tomorrow_local
                and not appt.reminder_d1_sent
                and self._send_reminder(phone, patient, appt, 'Mañana', counts)
            ):
                appt.reminder_d1_sent = True

            if (
                local_date == today_local
                and not appt.reminder_d0_sent
                and self._send_reminder(phone, patient, appt, 'Hoy', counts)
            ):
                appt.reminder_d0_sent = True

        self._send_renewal_notices(by_patient, counts)

        db.session.commit()
        return counts

    def _send_reminder(self, phone, patient, appt, prefix, counts):
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
        return self._dispatch(phone, body, counts, patient.id)

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
            if self._dispatch(phone, body, counts, patient.id, kind='sessions'):
                patient.renewal_notified_count = 2

    def _dispatch(self, phone, body, counts, patient_id=None, kind='sessions'):
        """Envia por WhatsApp y SMS. Devuelve True si ALGUN canal lo entrego.

        Cada canal pasa por `automation_settings.allows`: interruptor global, modo prueba (un solo paciente) y
        apagado por canal. Con `patient_id=None` (uso antiguo) no se filtra.
        """
        delivered = False
        wa_ok = patient_id is None or automation_settings.allows(patient_id, kind, 'whatsapp')[0]
        sms_ok_allowed = patient_id is None or automation_settings.allows(patient_id, kind, 'sms')[0]
        if wa_ok and self.messaging.send_whatsapp_message(phone, body):
            counts['sent_whatsapp'] += 1
            delivered = True
        if sms_ok_allowed:
            # send_sms_message devuelve un dict desde que trae el id del proveedor.
            sms = self.messaging.send_sms_message(phone, body)
            if sms.get('ok') if isinstance(sms, dict) else bool(sms):
                counts['sent_sms'] += 1
                delivered = True
        send_email = getattr(self.messaging, 'send_email', None)
        if send_email and patient_id is not None and automation_settings.allows(patient_id, kind, 'email')[0]:
            patient = db.session.get(User, patient_id)
            subject = (
                'Recordatorio de sesión · Centro Juan Pablo II'
                if kind == 'sessions'
                else 'Aviso · Centro Juan Pablo II'
            )
            if patient and send_email(patient, subject, body):
                counts['sent_email'] = counts.get('sent_email', 0) + 1
                delivered = True
        return delivered
