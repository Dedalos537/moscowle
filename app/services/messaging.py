"""Envio de mensajes a pacientes. Punto unico para WhatsApp y SMS.

Antes cada servicio de cobranza y recordatorio llamaba al proveedor por su
cuenta y ninguno miraba si el paciente queria recibir mensajes. Este modulo
concentra las tres cosas que faltaban:

  1. Que 'is_active = False' pare el envio. El usuario pidio que la cuenta
     activa/inactiva sea la que controla el contacto, asi que se respeta ahi
     y no solo en la pantalla.
  2. Un registro de todo lo que sale, con su resultado, para poder responder
     'a quien le escribimos y que le dijimos'.
  3. Un freno de ritmo. Mandar por una conexion no oficial se parece a
     spam, asi que hay tope diario, pausa entre mensajes y no se repite el
     mismo texto a la misma persona dos veces en poco tiempo.

No se manda nada sin pasar por `send_to_patient`, que es quien aplica todo.
"""

import logging
import random
import re
import time
from datetime import datetime, timedelta

from app.extensions import db
from app.models.campaign import Campaign, CampaignSend
from app.models.message_log import MessageLog
from app.models.message_template import MessageTemplate
from app.models.user import User

logger = logging.getLogger(__name__)

TIMEZONE_OFFSET = timedelta(hours=-5)  # America/Lima, sin DST

# Topes por defecto. Son conservadores a proposito: Baikelys es el metodo que
# Meta banea, y el costo de esperar es cero mientras el de que te corten el
# numero es el numero mismo.
DEFAULT_DAILY_CAPS = {'whatsapp': 150, 'sms': 500}
DEFAULT_MIN_GAP_SECONDS = 45
# Un mensaje repetido al mismo destinatario dentro de este plazo casi siempre
# es un reintento con un bug, no una campana.
REPEAT_WINDOW_HOURS = 6


class ContactRefusedError(ValueError):
    """No se puede contactar a este paciente. El motivo va en el mensaje."""


class MessagingService:
    def __init__(self, config=None, **kwargs):
        cfg = config or {}
        cfg.update({k.upper(): v for k, v in kwargs.items() if k not in ('config',)})
        self.daily_caps = {**DEFAULT_DAILY_CAPS, **(cfg.get('DAILY_CAPS') or {})}
        self.min_gap = int(cfg.get('MIN_GAP_SECONDS') or DEFAULT_MIN_GAP_SECONDS)
        self.whatsapp = kwargs.get('whatsapp') or cfg.get('WHATSAPP')
        self.sms = kwargs.get('sms') or cfg.get('SMS')
        if self.whatsapp is None:
            pass
        if self.sms is None:
            pass

    # ------------------------------------------------------------ servicios

    def _whatsapp(self):
        if self.whatsapp is None:
            from app.services.whatsapp_service import whatsapp_service

            self.whatsapp = whatsapp_service
        return self.whatsapp

    def _sms(self):
        if self.sms is None:
            from app.services.sms_whatsapp_service import SMSWhatsAppService

            self.sms = SMSWhatsAppService()
        return self.sms

    # ------------------------------------------------------------ elegibilidad

    @staticmethod
    def resolve_phone(patient):
        """Numero al que se le puede escribir.

        Se prefiere el contacto del apoderado: en terapia infantil casi
        siempre el que paga y recibe los avisos es el padre, no el nino.

        Ojo con el tipo: guardian_contact mezcla telefono y correo. Si el
        apoderado esta cargado con su correo hay que saltar al telefono del
        paciente, porque mandar un SMS a una direccion de correo es un
        error que solo se ve cuando el proveedor rechaza el envio.
        """
        guardian = (getattr(patient, 'guardian_contact', None) or '').strip()
        own = (getattr(patient, 'phone', None) or '').strip()
        return guardian if _is_phone(guardian) else own

    def check_contactable(self, patient, channel='whatsapp'):
        """Devuelve (True, None) o (False, motivo en castellano)."""
        if patient is None:
            return False, 'El paciente no existe'
        if not patient.is_active:
            return False, 'El paciente esta desactivado y no recibe avisos'
        phone = self.resolve_phone(patient)
        if not phone:
            return False, 'El paciente no tiene numero de telefono'
        # Vale para los dos canales: un SMS a un correo o a un numero de
        # tres digitos falla igual que un WhatsApp.
        if not _is_phone(phone):
            return False, 'El numero registrado no es valido'
        return True, None

    # -------------------------------------------------------------- plantillas

    def get_template(self, key, channel=None):
        t = MessageTemplate.query.filter_by(key=key).first()
        if t and t.is_active:
            return t
        if channel:
            return MessageTemplate.query.filter_by(key=key, channel=channel, is_active=True).first()
        return None

    @staticmethod
    def render(body, context):
        """Rellena {nombre} etc.

        Un {campo} que no este en el contexto se queda como esta en vez de
        reventar. Antes usaba str.format y cualquier llave sobrante
        devolvia un KeyError que se comia el envio entero.
        """

        def sub(match):
            key = match.group(1).strip()
            value = context.get(key)
            return str(value) if value not in (None, '') else match.group(0)

        return re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', sub, body or '')

    def render_template(self, key, channel, context):
        tpl = self.get_template(key, channel)
        if not tpl:
            return None
        return self.render(tpl.body, context)

    # -----------------------------------------------------------------:topes

    def _today(self):
        return datetime.utcnow() + TIMEZONE_OFFSET

    def sent_today(self, channel):
        start = (self._today() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return MessageLog.query.filter(
            MessageLog.channel == channel,
            MessageLog.status == 'sent',
            MessageLog.created_at >= start,
        ).count()

    def check_quota(self, channel):
        cap = self.daily_caps.get(channel, DEFAULT_DAILY_CAPS.get(channel, 100))
        used = self.sent_today(channel)
        if used >= cap:
            return False, f'Ya se envio el tope diario de {cap} mensajes por {channel}'
        return True, None

    def check_repeat(self, patient, message, channel):
        since = datetime.utcnow() - timedelta(hours=REPEAT_WINDOW_HOURS)
        dup = MessageLog.query.filter(
            MessageLog.patient_id == patient.id,
            MessageLog.channel == channel,
            MessageLog.message == message,
            MessageLog.status == 'sent',
            MessageLog.created_at >= since,
        ).first()
        if dup:
            return False, f'Ya se le mando este mismo mensaje hace menos de {REPEAT_WINDOW_HOURS} horas'
        return True, None

    # ----------------------------------------------------------------- envio

    def send_to_patient(
        self,
        patient_id,
        message,
        channel='whatsapp',
        sent_by_id=None,
        template_key=None,
        campaign_id=None,
        trigger='manual',
        enforce_repeat_check=True,
    ):
        """Envia a un paciente y registra el resultado.

        Devuelve dict con 'status'. Nunca lanza por fallo del proveedor: el
        fallo se registra en message_log con su motivo, que es lo que
        permite ver que paso. Si el paciente no es contactable tampoco lanza:
        devuelve 'skipped' con el motivo, que es distinto de 'fallo'.
        """
        patient = User.query.get(patient_id)
        channel = (channel or 'whatsapp').lower()

        ok, reason = self.check_contactable(patient, channel)
        if not ok:
            self._log(
                patient=patient,
                phone=None,
                channel=channel,
                message=message,
                status='skipped',
                failed_reason=reason,
                sent_by_id=sent_by_id,
                template_key=template_key,
                campaign_id=campaign_id,
                trigger=trigger,
            )
            return {'status': 'skipped', 'reason': reason, 'patient_id': patient_id}

        phone = self.resolve_phone(patient)

        if enforce_repeat_check:
            ok, reason = self.check_repeat(patient, message, channel)
            if not ok:
                return {'status': 'skipped', 'reason': reason, 'patient_id': patient_id}

        ok, reason = self.check_quota(channel)
        if not ok:
            self._log(
                patient=patient,
                phone=phone,
                channel=channel,
                message=message,
                status='skipped',
                failed_reason=reason,
                sent_by_id=sent_by_id,
                template_key=template_key,
                campaign_id=campaign_id,
                trigger=trigger,
            )
            return {'status': 'skipped', 'reason': reason, 'patient_id': patient_id}

        if channel == 'whatsapp':
            result = self._deliver_whatsapp(phone, message)
        else:
            result = self._deliver_sms(phone, message, patient)

        status = 'sent' if result.get('ok') else 'failed'
        reason = result.get('error')
        self._log(
            patient=patient,
            phone=phone,
            channel=channel,
            message=message,
            status=status,
            failed_reason=reason,
            sent_by_id=sent_by_id,
            template_key=template_key,
            campaign_id=campaign_id,
            trigger=trigger,
            provider_message_id=result.get('provider_message_id'),
        )
        return {
            'status': status,
            'patient_id': patient_id,
            'phone': phone,
            'provider_message_id': result.get('provider_message_id'),
            'reason': reason,
        }

    def _deliver_whatsapp(self, phone, message):
        try:
            res = self._whatsapp().send_message(phone, message)
            return {'ok': True, 'provider_message_id': res.get('provider_message_id')}
        except Exception as exc:
            logger.warning('Fallo WhatsApp a %s: %s', phone[-4:], exc)
            return {'ok': False, 'error': str(exc)[:250]}

    def _deliver_sms(self, phone, message, patient):
        try:
            svc = self._sms()
            if not svc.is_available():
                return {'ok': False, 'error': 'SMS: no hay proveedor configurado'}
            ok = svc.send_sms_message(phone, message)
            if isinstance(ok, dict):
                return ok
            return {'ok': bool(ok), 'error': None if ok else 'El proveedor de SMS rechazo el envio'}
        except Exception as exc:
            logger.warning('Fallo SMS a %s: %s', phone[-4:], exc)
            return {'ok': False, 'error': str(exc)[:250]}

    def _log(
        self,
        patient,
        phone,
        channel,
        message,
        status,
        failed_reason=None,
        sent_by_id=None,
        template_key=None,
        campaign_id=None,
        trigger='manual',
        provider_message_id=None,
    ):
        try:
            entry = MessageLog(
                patient_id=patient.id if patient else None,
                phone=phone,
                channel=channel,
                message=(message or '')[:4000],
                template_key=template_key,
                campaign_id=campaign_id,
                status=status,
                failed_reason=(failed_reason or '')[:250] or None,
                sent_by_id=sent_by_id,
                trigger=trigger,
                provider_message_id=provider_message_id,
            )
            db.session.add(entry)
            db.session.commit()
            return entry
        except Exception:
            db.session.rollback()
            logger.exception('No se pudo registrar el envio en message_log')
            return None

    # ------------------------------------------------------------- campanas

    def build_recipients(self, campaign):
        """Arma la lista de destinatarios de una campana segun su segmento."""
        q = User.query.filter(User.role == 'jugador')

        if campaign.segment == 'active':
            q = q.filter(User.is_active.is_(True))
        elif campaign.segment == 'inactive':
            q = q.filter(User.is_active.is_(False))
        elif campaign.segment == 'with_phone':
            q = q.filter(User.phone.isnot(None), User.phone != '')
        elif campaign.segment == 'all':
            pass
        else:  # 'manual': los eligio el admin en la pantalla
            pass

        return q.all()

    def prepare_campaign(self, campaign, patients=None):
        """Crea un campaign_send por destinatario, saltando a quien no se pueda."""
        patients = patients if patients is not None else self.build_recipients(campaign)
        created, skipped = 0, 0

        for p in patients:
            if campaign_send_exists(campaign.id, p.id):
                continue
            ok, reason = self.check_contactable(p, campaign.channel)
            row = CampaignSend(
                campaign_id=campaign.id,
                patient_id=p.id,
                phone=self.resolve_phone(p) if ok else None,
                status='pending' if ok else 'skipped',
                skip_reason=None if ok else reason,
                message=self.render(campaign.message, {'nombre': _first_name(p)}),
            )
            db.session.add(row)
            created += 1
            if not ok:
                skipped += 1

        campaign.total_recipients = created
        campaign.skipped_count = skipped
        campaign.status = 'scheduled' if created else 'draft'
        db.session.commit()
        return {'recipients': created, 'skipped': skipped}

    def run_campaign(self, campaign_id, sent_by_id=None, max_messages=None, pace=True):
        """Manda la campana respetando el orden y sin repetir destinatarios.

        Se detiene solo si el puente cae o si se corta una linea: mejor media
        campana que insistirle a WhatsApp.
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return {'error': 'La campana no existe'}
        if campaign.status == 'sent':
            return {'error': 'La campana ya se completo'}

        pending = (
            CampaignSend.query.filter_by(campaign_id=campaign_id, status='pending').order_by(CampaignSend.id).all()
        )
        if max_messages:
            pending = pending[:max_messages]

        campaign.status = 'running'
        campaign.started_at = campaign.started_at or datetime.utcnow()
        db.session.commit()

        sent = failed = 0
        for row in pending:
            if pace and sent:
                # Pausa con jitter: siempre igual delata el patron automatico.
                # Es un retardo, no una decision criptografica.
                time.sleep(self.min_gap + random.uniform(0, self.min_gap))  # noqa: S311
            res = self.send_to_patient(
                row.patient_id,
                row.message,
                channel=campaign.channel,
                sent_by_id=sent_by_id,
                template_key=campaign.template_key,
                campaign_id=campaign.id,
                trigger='campaign',
            )
            row.status = res['status']
            if res['status'] == 'sent':
                row.sent_at = datetime.utcnow()
                sent += 1
            elif res['status'] == 'failed':
                row.failed_reason = res.get('reason')
                failed += 1
            else:
                row.skip_reason = res.get('reason')
            db.session.commit()

        # Recuento global de la campana, no solo de este tramo.
        campaign.sent_count = CampaignSend.query.filter_by(campaign_id=campaign_id, status='sent').count()
        campaign.failed_count = CampaignSend.query.filter_by(campaign_id=campaign_id, status='failed').count()
        campaign.skipped_count = CampaignSend.query.filter_by(campaign_id=campaign_id, status='skipped').count()

        left = CampaignSend.query.filter_by(campaign_id=campaign_id, status='pending').count()
        campaign.status = 'sent' if left == 0 else 'paused'
        if left == 0:
            campaign.finished_at = datetime.utcnow()
        db.session.commit()

        return {
            'campaign_id': campaign_id,
            'sent': sent,
            'failed': failed,
            'remaining': left,
            'status': campaign.status,
        }

    # ---------------------------------------------------------------- utiles

    def stats(self):
        """Resumen para la pantalla y para la IA."""
        out = {'channels': {}, 'today': datetime.utcnow().isoformat()}
        for channel, cap in self.daily_caps.items():
            used = self.sent_today(channel)
            out['channels'][channel] = {
                'sent_today': used,
                'daily_cap': cap,
                'remaining_today': max(0, cap - used),
            }
        out['contacts'] = contact_summary()
        return out


def campaign_send_exists(campaign_id, patient_id):
    return CampaignSend.query.filter_by(campaign_id=campaign_id, patient_id=patient_id).first() is not None


def _is_phone(value):
    """True si el valor es un telefono usable, y no un correo ni un resto.

    guardian_contact se carga a mano y termina guardando lo que sea: en un
    paciente real esta el correo del apoderado. Un telefono movil peruano
    tiene 9 digitos; con menos no hay con que enviar.
    """
    if not value or '@' in value:
        return False
    return len(re.sub(r'\D', '', value)) >= 9


def _first_name(user):
    return (getattr(user, 'first_name', None) or getattr(user, 'username', '') or '').split()[0]


def contact_summary():
    """Cuantos pacientes hay y cuantos se pueden contactar por cada canal."""
    total = User.query.filter_by(role='jugador').count()
    active = User.query.filter_by(role='jugador', is_active=True).count()
    with_phone = User.query.filter(
        User.role == 'jugador',
        User.is_active.is_(True),
        (User.phone.isnot(None) | (User.guardian_contact.isnot(None))),
    ).count()
    active_no_phone = active - with_phone
    return {
        'total_patients': total,
        'active': active,
        'inactive': total - active,
        'active_with_phone': with_phone,
        'active_without_phone': max(0, active_no_phone),
    }
