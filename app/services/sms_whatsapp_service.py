import logging
import os
import threading
from datetime import datetime

from flask import current_app

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client

    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.debug('Twilio not installed')

try:
    import pywhatkit

    PYWHATKIT_AVAILABLE = True
    logger.info(' pywhatkit available for automated WhatsApp messaging')
except ImportError:
    PYWHATKIT_AVAILABLE = False
    logger.debug('pywhatkit not installed')


class SMSWhatsAppService:
    """Manda SMS y WhatsApp. Prioridad: pywhatkit > Twilio"""

    DEFAULT_NOTIFICATION_NUMBER = os.environ.get('TWILIO_NOTIFICATION_PHONE')
    if not DEFAULT_NOTIFICATION_NUMBER:
        DEFAULT_NOTIFICATION_NUMBER = os.environ.get('NOTIFICATION_SMS_DESTINATION')
    if not DEFAULT_NOTIFICATION_NUMBER:
        DEFAULT_NOTIFICATION_NUMBER = '+51921507470'

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_phone = os.getenv('TWILIO_PHONE_NUMBER')
        self.whatsapp_from = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155552671')

        self.twilio_client = None
        if TWILIO_AVAILABLE and self.account_sid and self.auth_token:
            try:
                self.twilio_client = Client(self.account_sid, self.auth_token)
                self.twilio_available = True
                logger.info(' Twilio initialized')
            except Exception as e:
                logger.warning(f'  Twilio initialization failed: {e}')
                self.twilio_available = False
        else:
            self.twilio_available = False

        self.pywhatkit_available = PYWHATKIT_AVAILABLE

        if not self.is_available():
            logger.warning('  No messaging service available (install pywhatkit or configure Twilio)')

    def is_available(self):
        """Verifica disponibilidad de servicio de mensajería"""
        return self.pywhatkit_available or self.twilio_available

    def _send_whatsapp_pywhatkit(self, phone_number, message_text):
        """Enviar WhatsApp vía pywhatkit en segundo plano"""
        try:
            clean_phone = ''.join(filter(str.isdigit, phone_number))

            now = datetime.now()
            send_hour = now.hour
            send_minute = now.minute + 1

            if send_minute >= 60:
                send_minute -= 60
                send_hour += 1
                if send_hour >= 24:
                    send_hour = 0

            current_app.logger.info(f' Scheduling WhatsApp to +{clean_phone} at {send_hour:02d}:{send_minute:02d}')
            current_app.logger.info(f' Message preview: {message_text[:60]}...')

            pywhatkit.sendwhatmsg(
                phone_number=f'+{clean_phone}',
                message=message_text,
                time_hour=send_hour,
                time_min=send_minute,
                wait_time=15,
                tab_close=True,
            )

            current_app.logger.info(f' WhatsApp queued to +{clean_phone}')
            return True

        except Exception as e:
            current_app.logger.error(f' pywhatkit error: {e}')
            return False

    def send_whatsapp_message(self, phone_number, message_body):
        """WhatsApp genérico (pywhatkit > Twilio) para recordatorios/información."""
        if self.pywhatkit_available:
            thread = threading.Thread(
                target=self._send_whatsapp_pywhatkit, args=(phone_number, message_body), daemon=True
            )
            thread.start()
            current_app.logger.info(' WhatsApp (generic) via pywhatkit scheduled (background thread)')
            return True

        if self.twilio_available:
            try:
                if not phone_number.startswith('+'):
                    phone_number = f'+{phone_number}'
                message = self.twilio_client.messages.create(
                    body=message_body, from_=self.whatsapp_from, to=f'whatsapp:{phone_number}'
                )
                current_app.logger.info(f' WhatsApp (Twilio) sent to {phone_number}: {message.sid}')
                return True
            except Exception as e:
                current_app.logger.error(f' Error sending WhatsApp via Twilio: {e}')
                return False

        logger.warning(' WhatsApp: Neither pywhatkit nor Twilio available')
        return False

    def send_sms_message(self, phone_number, message_body):
        """SMS genérico vía Twilio."""
        if not self.twilio_available:
            logger.warning(' SMS: Twilio not available')
            return False
        try:
            if not phone_number.startswith('+'):
                phone_number = f'+{phone_number}'
            message = self.twilio_client.messages.create(body=message_body, from_=self.from_phone, to=phone_number)
            current_app.logger.info(f' SMS sent to {phone_number}: {message.sid}')
            return True
        except Exception as e:
            current_app.logger.error(f' Error sending SMS: {e}')
            return False

    def _get_notification_destination(self):
        """OCP: número destino configurable (Centro de Operaciones > env > default)."""
        return (
            current_app.config.get('NOTIFICATION_SMS_DESTINATION')
            or os.environ.get('NOTIFICATION_SMS_DESTINATION')
            or self.DEFAULT_NOTIFICATION_NUMBER
        )

    def _get_sms_template_body(self, patient_name, amount, due_date_str, days_overdue):
        """OCP: plantilla SMS configurable con fallback al texto por defecto."""
        template_sms = current_app.config.get('NOTIFICATION_SMS_TEMPLATE') or os.environ.get(
            'NOTIFICATION_SMS_TEMPLATE'
        )
        if template_sms:
            return template_sms.format(
                patient_name=patient_name, amount=amount, due_date_str=due_date_str, days_overdue=days_overdue
            )
        return f"""Hola {patient_name},

Recordatorio: Tienes una deuda pendiente con Centro de Terapias.

Detalles:
- Monto: S/ {amount:.2f}
- Vencimiento: {due_date_str}
- Atraso: {days_overdue} días

Por favor realiza el pago. Gracias."""

    def _get_whatsapp_template_body(self, patient_name, amount, due_date_str, days_overdue):
        """OCP: plantilla WhatsApp configurable con fallback al texto por defecto."""
        template_wa = current_app.config.get('NOTIFICATION_WHATSAPP_TEMPLATE') or os.environ.get(
            'NOTIFICATION_WHATSAPP_TEMPLATE'
        )
        if template_wa:
            return template_wa.format(
                patient_name=patient_name, amount=amount, due_date_str=due_date_str, days_overdue=days_overdue
            )
        return f"""¡Hola {patient_name}!

Recordatorio de pago pendiente

Detalles:
- Monto: S/ {amount:.2f}
- Vencimiento: {due_date_str}
- Atraso: {days_overdue} días

Por favor realiza el pago cuanto antes.

¿Preguntas? Contáctanos.
Centro de Terapias"""

    def send_payment_reminder_sms(self, phone_number, patient_name, amount, due_date, days_overdue):
        """Recordatorio de pago por SMS (número destino y plantilla configurables vía OCP)."""
        if not self.twilio_available:
            logger.warning(' SMS: Twilio not available')
            return False

        try:
            due_date_str = due_date.strftime('%d/%m/%Y') if due_date else 'N/A'
            message_body = self._get_sms_template_body(patient_name, amount, due_date_str, days_overdue)

            destination = self._get_notification_destination()
            target = phone_number or destination

            if not target.startswith('+'):
                target = f'+{target}'

            message = self.twilio_client.messages.create(body=message_body, from_=self.from_phone, to=target)

            current_app.logger.info(f' SMS sent to {target}: {message.sid}')
            return True
        except Exception as e:
            current_app.logger.error(f' Error sending SMS: {e}')
            return False

    def send_payment_reminder_whatsapp(self, phone_number, patient_name, amount, due_date, days_overdue):
        """Recordatorio de pago por WhatsApp (plantilla configurable vía OCP)."""
        due_date_str = due_date.strftime('%d/%m/%Y') if due_date else 'N/A'

        message_body = self._get_whatsapp_template_body(patient_name, amount, due_date_str, days_overdue)

        if self.pywhatkit_available:
            thread = threading.Thread(
                target=self._send_whatsapp_pywhatkit, args=(phone_number, message_body), daemon=True
            )
            thread.start()
            current_app.logger.info(' WhatsApp reminder via pywhatkit scheduled (background thread)')
            return True

        if self.twilio_available:
            try:
                if not phone_number.startswith('+'):
                    phone_number = f'+{phone_number}'

                whatsapp_to = f'whatsapp:{phone_number}'

                message = self.twilio_client.messages.create(
                    body=message_body, from_=self.whatsapp_from, to=whatsapp_to
                )

                current_app.logger.info(f' WhatsApp (Twilio) sent to {phone_number}: {message.sid}')
                return True
            except Exception as e:
                current_app.logger.error(f' Error sending WhatsApp via Twilio: {e}')
                return False

        logger.warning(' WhatsApp: Neither pywhatkit nor Twilio available')
        return False

    def send_payment_confirmation_sms(self, phone_number, patient_name, amount, method):
        """Confirmación de pago por SMS"""
        if not self.twilio_available:
            return False

        try:
            message_body = f"""Pago confirmado

Hola {patient_name},

Tu pago de S/ {amount:.2f} fue registrado correctamente.
Metodo: {method.upper()}

Gracias por tu pago.
Centro de Terapias"""

            if not phone_number.startswith('+'):
                phone_number = f'+{phone_number}'

            self.twilio_client.messages.create(body=message_body, from_=self.from_phone, to=phone_number)

            current_app.logger.info(f' Payment confirmation SMS sent to {phone_number}')
            return True
        except Exception as e:
            current_app.logger.error(f' Error sending payment confirmation SMS: {e}')
            return False

    def send_payment_confirmation_whatsapp(self, phone_number, patient_name, amount, method):
        """Confirmación de pago por WhatsApp (pywhatkit > Twilio)"""
        message_body = f"""Pago confirmado

Hola {patient_name},

Tu pago de S/ {amount:.2f} fue registrado correctamente.
Metodo: {method.upper()}

Gracias por tu pago.
Centro de Terapias"""

        if self.pywhatkit_available:
            thread = threading.Thread(
                target=self._send_whatsapp_pywhatkit, args=(phone_number, message_body), daemon=True
            )
            thread.start()
            current_app.logger.info(' WhatsApp confirmation via pywhatkit scheduled (background thread)')
            return True

        if self.twilio_available:
            try:
                if not phone_number.startswith('+'):
                    phone_number = f'+{phone_number}'

                whatsapp_to = f'whatsapp:{phone_number}'

                message = self.twilio_client.messages.create(
                    body=message_body, from_=self.whatsapp_from, to=whatsapp_to
                )

                current_app.logger.info(f' WhatsApp (Twilio) sent to {phone_number}: {message.sid}')
                return True
            except Exception as e:
                current_app.logger.error(f' Error sending WhatsApp via Twilio: {e}')
                return False

        logger.warning(' WhatsApp: Neither pywhatkit nor Twilio available')
        return False
