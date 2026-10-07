import logging
import os
import re
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

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.debug('requests not installed')


def to_e164(phone):
    """'+51937657870' a partir de lo que haya guardado en la base.

    La base trae el numero local ('937657870') o con guiones. El mismo
    criterio que jidOf() del puente de WhatsApp (index.js): un 0 inicial
    se cambia por 51 y si no empieza por 51 se le antepone. Devuelve ''
    si no queda nada con que trabajar.
    """
    digits = re.sub(r'\D', '', str(phone or ''))
    if not digits:
        return ''
    if digits.startswith('0'):
        digits = '51' + digits[1:]
    elif not digits.startswith('51'):
        digits = '51' + digits
    return f'+{digits}'


class SMSWhatsAppService:
    """Manda SMS y WhatsApp. SMS: gateway del celular > Twilio."""

    DEFAULT_NOTIFICATION_NUMBER = os.environ.get('TWILIO_NOTIFICATION_PHONE')
    if not DEFAULT_NOTIFICATION_NUMBER:
        DEFAULT_NOTIFICATION_NUMBER = os.environ.get('NOTIFICATION_SMS_DESTINATION')
    if not DEFAULT_NOTIFICATION_NUMBER:
        DEFAULT_NOTIFICATION_NUMBER = '+51921507470'

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_phone = os.getenv('TWILIO_PHONE_NUMBER')
        # Sin numero configurado no hay de donde salir. Antes caia al
        # +14155552671 de ejemplo de la documentacion de Twilio, que no
        # pertenece a nadie: los mensajes se perdian sin dejar rastro.
        self.whatsapp_from = os.getenv('TWILIO_WHATSAPP_NUMBER') or ''

        # Gateway que usa el celular del centro como origen. Salta primero
        # porque el remitente que ve el apoderado es el mismo numero que el
        # de WhatsApp: no depende de que un proveedor tenga un numero propio.
        self.gateway_url = (os.getenv('SMS_GATEWAY_URL') or 'https://api.sms.json.pe').rstrip('/')
        self.gateway_token = os.getenv('SMS_GATEWAY_TOKEN') or ''
        self.gateway_available = REQUESTS_AVAILABLE and bool(self.gateway_token)

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
            logger.warning('  No messaging service available (set SMS_GATEWAY_TOKEN or configure Twilio)')

    def is_available(self):
        """Verifica disponibilidad de servicio de mensajería"""
        return self.gateway_available or self.pywhatkit_available or self.twilio_available

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
        """Envia un SMS. Devuelve dict con provider_message_id si salio.

        La normalizacion a E.164 pasa aqui y no en cada proveedor: la base
        guarda el numero local ('937657870') y ni Twilio ni el gateway
        aceptan eso. Nunca lanza: quien llama solo quiere saber si salio y
        con que id.
        """
        target = to_e164(phone_number)
        if not target:
            return {'ok': False, 'error': 'El numero no es valido'}

        if self.gateway_available:
            return self._send_sms_gateway(target, message_body)

        if not self.twilio_available:
            logger.warning(' SMS: no hay proveedor configurado')
            return {'ok': False, 'error': 'SMS: no hay proveedor configurado'}

        try:
            message = self.twilio_client.messages.create(body=message_body, from_=self.from_phone, to=target)
            logger.info(' SMS (twilio) enviado a %s: %s', target, message.sid)
            return {'ok': True, 'provider_message_id': message.sid}
        except Exception as e:
            logger.error(' Error sending SMS: %s', e)
            return {'ok': False, 'error': str(e)[:250]}

    def _send_sms_gateway(self, target, message_body):
        """Salida por el celular Android vinculado al centro.

        El remitente que ve el destinatario es la linea del celular, es decir
        el mismo numero que usa WhatsApp. El gateway pide el numero con
        codigo de pais y sin '+'. El device tiene que estar en linea y con
        saldo de SMS: si no, el rechazo vuelve como error y queda en
        message_log.
        """
        try:
            resp = requests.post(
                f'{self.gateway_url}/send',
                headers={'Authorization': f'Bearer {self.gateway_token}'},
                json={'number': target.lstrip('+'), 'message': message_body},
                timeout=30,
            )
        except Exception as e:
            logger.warning(' SMS gateway sin respuesta: %s', e)
            return {'ok': False, 'error': f'Gateway sin respuesta: {e}'[:250]}

        try:
            data = resp.json()
        except Exception:
            data = {}

        if resp.status_code != 200 or not data.get('success'):
            reason = str(data.get('message') or resp.text or resp.status_code)[:200]
            logger.error(' SMS gateway rechazo (%s): %s', resp.status_code, reason)
            return {'ok': False, 'error': f'Gateway: {reason}'[:250]}

        provider_id = data.get('message_id')
        logger.info(' SMS (gateway) enviado a %s: %s', target, provider_id)
        return {'ok': True, 'provider_message_id': provider_id}

    def _get_notification_destination(self):
        """OCP: número destino configurable (Centro de Operaciones > env > default)."""
        from app.services import channel_settings

        return channel_settings.get('destination') or self.DEFAULT_NOTIFICATION_NUMBER

    def _get_sms_template_body(self, patient_name, amount, due_date_str, days_overdue):
        """OCP: plantilla SMS configurable con fallback al texto por defecto."""
        from app.services import channel_settings

        template_sms = channel_settings.get('sms_template')
        if template_sms:
            rendered = channel_settings.render(
                template_sms,
                dict(patient_name=patient_name, amount=amount, due_date_str=due_date_str, days_overdue=days_overdue),
            )
            if rendered:
                return rendered
        return f"""Hola {patient_name},

Recordatorio: Tienes una deuda pendiente con Centro de Terapias.

Detalles:
- Monto: S/ {amount:.2f}
- Vencimiento: {due_date_str}
- Atraso: {days_overdue} días

Por favor realiza el pago. Gracias."""

    def _get_whatsapp_template_body(self, patient_name, amount, due_date_str, days_overdue):
        """OCP: plantilla WhatsApp configurable con fallback al texto por defecto."""
        from app.services import channel_settings

        template_wa = channel_settings.get('whatsapp_template')
        if template_wa:
            rendered = channel_settings.render(
                template_wa,
                dict(patient_name=patient_name, amount=amount, due_date_str=due_date_str, days_overdue=days_overdue),
            )
            if rendered:
                return rendered
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
