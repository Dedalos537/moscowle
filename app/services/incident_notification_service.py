import logging

import requests as http_requests

from app.models.incidente import Incidente
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

LEVEL_LABELS = {
    1: 'Advertencia',
    2: 'Error Crítico',
    3: 'Incidente de Negocio',
}

CATEGORY_COLORS = {
    'HARDWARE': '#e74c3c',
    'SOFTWARE': '#e67e22',
    'RED': '#9b59b6',
    'ACCESOS': '#3498db',
    'OPERACIONES': '#2ecc71',
}


class IncidentNotificationService:
    @classmethod
    def _notify_user(cls, user_id, message, title=None, category='alert', priority='normal', link=None):
        """Create an in-app notification for a user."""
        try:
            notif_service = NotificationService()
            notif_service.notify_user(
                user_id=user_id,
                message=message,
                title=title,
                notif_type='alert',
                link=link,
                category=category,
                priority=priority,
                icon=['fas', 'triangle-exclamation'],
            )
        except Exception as e:
            logger.exception('Failed to create in-app notification for user %s: %s', user_id, e)

    @classmethod
    def notify_new_incident(cls, incidente: Incidente):
        """Notifica la creación de un incidente al responsable y admin."""
        logger.info('Notifying new incident #%s', incidente.id_incidente)

        cls._send_email_new(incidente)
        cls._send_slack_new(incidente)
        cls._notify_inapp_new(incidente)

    @classmethod
    def notify_escalation(cls, incidente: Incidente, nivel_anterior: int):
        """Notifica escalamiento a nivel superior."""
        logger.info(
            'Notifying escalation incident #%s level %s->%s',
            incidente.id_incidente,
            nivel_anterior,
            incidente.escalamiento_nivel,
        )

        cls._send_email_escalation(incidente, nivel_anterior)
        cls._send_slack_escalation(incidente, nivel_anterior)
        cls._notify_inapp_escalation(incidente, nivel_anterior)

    @classmethod
    def notify_sla_breach(cls, incidente: Incidente):
        """Notifica violación de SLA."""
        logger.info('SLA breach for incident #%s', incidente.id_incidente)

        cls._send_email_sla_breach(incidente)
        cls._send_slack_sla_breach(incidente)
        cls._notify_inapp_sla_breach(incidente)

    @classmethod
    def notify_sla_breach_grouped(cls, incidentes: list):
        """Envía UN SOLO mensaje agrupado con todos los SLA vencidos. Reemplaza los mensajes individuales."""
        if not incidentes:
            return

        logger.info('Sending grouped SLA breach notification for %d incidents', len(incidentes))

        # Build grouped message
        lines = [f'🚨 *{len(incidentes)} INCIDENTES CON SLA VENCIDO*']
        lines.append('')
        for i, inc in enumerate(incidentes[:15], 1):  # max 15 in message
            sla_str = inc.fecha_limite_sla.strftime('%d/%m %H:%M') if inc.fecha_limite_sla else 'N/A'
            horas = inc.horas_invertidas or 0
            lines.append(f'{i}. *#{inc.id_incidente}* {inc.titulo}')
            lines.append(f'   P{inc.prioridad} | {inc.categoria} | SLA: {sla_str} | {horas:.0f}h')
        if len(incidentes) > 15:
            lines.append(f'\n... y {len(incidentes) - 15} más')

        telegram_msg = '\n'.join(lines)

        # Send ONE Telegram message
        try:
            from app.services.telegram_bot_service import send_telegram_message

            send_telegram_message(telegram_msg)
            logger.info('Grouped SLA Telegram sent: %d incidents', len(incidentes))
        except Exception as e:
            logger.error(f'Failed to send grouped SLA Telegram: {e}')

        # Send ONE email with all incidents
        try:
            cls._send_email_sla_breach_grouped(incidentes)
        except Exception as e:
            logger.error(f'Failed to send grouped SLA email: {e}')

        # Send ONE in-app notification (not per-incident to avoid flood)
        try:
            from app.models.user import User

            msg_inapp = f'🚨 {len(incidentes)} incidentes con SLA vencido. Requieren atención inmediata.'
            admins = User.query.filter_by(role='admin', is_active=True).all()
            notif_service = NotificationService()
            for admin in admins:
                notif_service.notify_user(
                    user_id=admin.id,
                    message=msg_inapp,
                    title='SLA Vencido (Agrupado)',
                    notif_type='alert',
                    link='/admin/incidents',
                    category='alert',
                    priority='high',
                    icon=['fas', 'triangle-exclamation'],
                    skip_telegram=True,
                )
        except Exception as e:
            logger.error(f'Failed to send grouped in-app notification: {e}')

    @classmethod
    def notify_resolution(cls, incidente: Incidente):
        """Notifica resolución al creador."""
        logger.info('Notifying resolution for incident #%s', incidente.id_incidente)

        cls._send_email_resolution(incidente)
        cls._send_slack_resolution(incidente)
        cls._notify_inapp_resolution(incidente)

    @classmethod
    def _get_admin_emails(cls):
        from app.models.user import User

        admins = User.query.filter_by(role='admin', is_active=True).all()
        return [a.email for a in admins if a.email]

    @classmethod
    def _get_responsible_email(cls, incidente: Incidente):
        if incidente.responsable_id:
            from app.models.user import User

            user = User.query.get(incidente.responsable_id)
            if user and user.email:
                return user.email
        return None

    @classmethod
    def _get_creator_email(cls, incidente: Incidente):
        if incidente.user_id:
            from app.models.user import User

            user = User.query.get(incidente.user_id)
            if user and user.email:
                return user.email
        return None

    @classmethod
    def _send_email_new(cls, incidente: Incidente):
        recipients = cls._get_admin_emails()
        resp_email = cls._get_responsible_email(incidente)
        if resp_email:
            recipients.append(resp_email)
        recipients = list(set(recipients))

        if not recipients:
            return

        subject = f'[Moscowle] Nuevo Incidente #{incidente.id_incidente}: {incidente.titulo}'
        sla_str = incidente.fecha_limite_sla.strftime('%d/%m/%Y %H:%M') if incidente.fecha_limite_sla else 'N/A'
        body = (
            f'Se ha creado un nuevo incidente en el sistema Moscowle IA.\n\n'
            f'ID: #{incidente.id_incidente}\n'
            f'Título: {incidente.titulo}\n'
            f'Categoría: {incidente.categoria}\n'
            f'Prioridad: P{incidente.prioridad}\n'
            f'Estado: {incidente.estado}\n'
            f'SLA límite: {sla_str}\n\n'
            f'Descripción:\n{incidente.descripcion}\n'
        )

        try:
            EmailService.send_notification_email(subject, recipients, body)
        except Exception as e:
            logger.exception('Failed to send new incident email: %s', e)

    @classmethod
    def _send_email_escalation(cls, incidente: Incidente, nivel_anterior: int):
        recipients = cls._get_admin_emails()
        if not recipients:
            return

        nivel_label = LEVEL_LABELS.get(incidente.escalamiento_nivel, f'Nivel {incidente.escalamiento_nivel}')
        subject = f'[Moscowle] ESCALAMIENTO Nivel {incidente.escalamiento_nivel} - Incidente #{incidente.id_incidente}'
        body = (
            f'El incidente #{incidente.id_incidente} ha sido escalado.\n\n'
            f'Título: {incidente.titulo}\n'
            f'Escalamiento: Nivel {nivel_anterior} -> Nivel {incidente.escalamiento_nivel} ({nivel_label})\n'
            f'Categoría: {incidente.categoria}\n'
            f'Prioridad: P{incidente.prioridad}\n'
            f'Estado: {incidente.estado}\n'
            f'Tiempo transcurrido: {incidente.horas_invertidas:.1f}h\n'
        )

        try:
            EmailService.send_notification_email(subject, recipients, body)
        except Exception as e:
            logger.exception('Failed to send escalation email: %s', e)

    @classmethod
    def _send_email_sla_breach(cls, incidente: Incidente):
        recipients = cls._get_admin_emails()
        resp_email = cls._get_responsible_email(incidente)
        if resp_email:
            recipients.append(resp_email)
        recipients = list(set(recipients))

        if not recipients:
            return

        subject = f'[Moscowle] SLA VENCIDO - Incidente #{incidente.id_incidente}'
        sla_str = incidente.fecha_limite_sla.strftime('%d/%m/%Y %H:%M') if incidente.fecha_limite_sla else 'N/A'
        body = (
            f'ALERTA: El SLA del incidente #{incidente.id_incidente} ha sido vulnerado.\n\n'
            f'Título: {incidente.titulo}\n'
            f'Categoría: {incidente.categoria}\n'
            f'Prioridad: P{incidente.prioridad}\n'
            f'SLA límite: {sla_str}\n'
            f'Horas transcurridas: {incidente.horas_invertidas:.1f}h\n'
            f'Nivel de escalamiento: {incidente.escalamiento_nivel}\n\n'
            f'Requiere atención inmediata.\n'
        )

        try:
            EmailService.send_notification_email(subject, recipients, body)
        except Exception as e:
            logger.exception('Failed to send SLA breach email: %s', e)

    @classmethod
    def _send_email_sla_breach_grouped(cls, incidentes: list):
        """Send ONE email with all SLA breaches grouped."""
        recipients = cls._get_admin_emails()
        if not recipients:
            return

        subject = f'[Moscowle] {len(incidentes)} INCIDENTES CON SLA VENCIDO'
        lines = [
            f'ALERTA: {len(incidentes)} incidentes tienen SLA vencido.\n',
            f'{"ID":<8} {"Título":<40} {"Categ."} {"P":>2} {"SLA":>16} {"Horas":>6}',
            '-' * 85,
        ]
        for inc in incidentes[:20]:
            sla_str = inc.fecha_limite_sla.strftime('%d/%m/%Y %H:%M') if inc.fecha_limite_sla else 'N/A'
            horas = inc.horas_invertidas or 0
            lines.append(
                f'#{inc.id_incidente:<7} {inc.titulo[:40]:<40} {inc.categoria} {inc.prioridad:>2} {sla_str:>16} {horas:>5.1f}h'
            )
        if len(incidentes) > 20:
            lines.append(f'\n... y {len(incidentes) - 20} más')
        lines.append('\nRequiere atención inmediata.')

        body = '\n'.join(lines)
        try:
            EmailService.send_notification_email(subject, recipients, body)
        except Exception as e:
            logger.exception('Failed to send grouped SLA email: %s', e)

    @classmethod
    def _send_email_resolution(cls, incidente: Incidente):
        recipients = cls._get_creator_email(incidente)
        if not recipients:
            return

        subject = f'[Moscowle] Incidente #{incidente.id_incidente} Resuelto'
        res_str = incidente.fecha_resolucion.strftime('%d/%m/%Y %H:%M') if incidente.fecha_resolucion else 'N/A'
        body = (
            f'El incidente #{incidente.id_incidente} ha sido marcado como resuelto.\n\n'
            f'Título: {incidente.titulo}\n'
            f'Categoría: {incidente.categoria}\n'
            f'Resolución: {res_str}\n'
        )

        try:
            EmailService.send_notification_email(subject, [recipients], body)
        except Exception as e:
            logger.exception('Failed to send resolution email: %s', e)

    @classmethod
    def _send_slack_new(cls, incidente: Incidente):
        from flask import current_app

        webhook_url = current_app.config.get('ALERT_SLACK_WEBHOOK_URL', '')
        if not webhook_url:
            return

        color = CATEGORY_COLORS.get(incidente.categoria, '#95a5a6')
        payload = {
            'attachments': [
                {
                    'color': color,
                    'blocks': [
                        {
                            'type': 'header',
                            'text': {
                                'type': 'plain_text',
                                'text': f'🆕 Incidente #{incidente.id_incidente}',
                            },
                        },
                        {
                            'type': 'section',
                            'fields': [
                                {'type': 'mrkdwn', 'text': f'*Título:*\n{incidente.titulo}'},
                                {'type': 'mrkdwn', 'text': f'*Categoría:*\n{incidente.categoria}'},
                                {'type': 'mrkdwn', 'text': f'*Prioridad:*\nP{incidente.prioridad}'},
                                {'type': 'mrkdwn', 'text': f'*Estado:*\n{incidente.estado}'},
                            ],
                        },
                    ],
                }
            ],
        }

        cls._post_slack(webhook_url, payload)

    @classmethod
    def _send_slack_escalation(cls, incidente: Incidente, nivel_anterior: int):
        from flask import current_app

        webhook_url = current_app.config.get('ALERT_SLACK_WEBHOOK_URL', '')
        if not webhook_url:
            return

        nivel_label = LEVEL_LABELS.get(incidente.escalamiento_nivel, f'Nivel {incidente.escalamiento_nivel}')
        payload = {
            'attachments': [
                {
                    'color': '#e74c3c',
                    'blocks': [
                        {
                            'type': 'header',
                            'text': {
                                'type': 'plain_text',
                                'text': f'⬆️ ESCALAMIENTO Nivel {incidente.escalamiento_nivel}',
                            },
                        },
                        {
                            'type': 'section',
                            'fields': [
                                {'type': 'mrkdwn', 'text': f'*Incidente:*\n#{incidente.id_incidente}'},
                                {'type': 'mrkdwn', 'text': f'*Título:*\n{incidente.titulo}'},
                                {'type': 'mrkdwn', 'text': f'*Escalamiento:*\n{nivel_label}'},
                                {'type': 'mrkdwn', 'text': f'*Tiempo:*\n{incidente.horas_invertidas:.1f}h'},
                            ],
                        },
                    ],
                }
            ],
        }

        cls._post_slack(webhook_url, payload)

    @classmethod
    def _send_slack_sla_breach(cls, incidente: Incidente):
        from flask import current_app

        webhook_url = current_app.config.get('ALERT_SLACK_WEBHOOK_URL', '')
        if not webhook_url:
            return

        payload = {
            'attachments': [
                {
                    'color': '#e74c3c',
                    'blocks': [
                        {
                            'type': 'header',
                            'text': {
                                'type': 'plain_text',
                                'text': f'🚨 SLA VENCIDO - Incidente #{incidente.id_incidente}',
                            },
                        },
                        {
                            'type': 'section',
                            'fields': [
                                {'type': 'mrkdwn', 'text': f'*Título:*\n{incidente.titulo}'},
                                {'type': 'mrkdwn', 'text': f'*Categoría:*\n{incidente.categoria}'},
                                {'type': 'mrkdwn', 'text': f'*Prioridad:*\nP{incidente.prioridad}'},
                                {'type': 'mrkdwn', 'text': f'*Tiempo:*\n{incidente.horas_invertidas:.1f}h'},
                            ],
                        },
                    ],
                }
            ],
        }

        cls._post_slack(webhook_url, payload)

    @classmethod
    def _send_slack_resolution(cls, incidente: Incidente):
        from flask import current_app

        webhook_url = current_app.config.get('ALERT_SLACK_WEBHOOK_URL', '')
        if not webhook_url:
            return

        payload = {
            'attachments': [
                {
                    'color': '#2ecc71',
                    'blocks': [
                        {
                            'type': 'header',
                            'text': {
                                'type': 'plain_text',
                                'text': f'✅ Resuelto - Incidente #{incidente.id_incidente}',
                            },
                        },
                        {
                            'type': 'section',
                            'fields': [
                                {'type': 'mrkdwn', 'text': f'*Título:*\n{incidente.titulo}'},
                                {'type': 'mrkdwn', 'text': f'*Categoría:*\n{incidente.categoria}'},
                            ],
                        },
                    ],
                }
            ],
        }

        cls._post_slack(webhook_url, payload)

    @staticmethod
    def _post_slack(webhook_url, payload):
        try:
            resp = http_requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.exception('Failed to send Slack alert: %s', e)

    # --- In-app notifications ---

    @classmethod
    def _notify_inapp_new(cls, incidente: Incidente):
        from app.models.user import User

        sla_str = incidente.fecha_limite_sla.strftime('%d/%m %H:%M') if incidente.fecha_limite_sla else 'N/A'
        msg = f'Nuevo incidente #{incidente.id_incidente}: {incidente.titulo} (P{incidente.prioridad}, SLA: {sla_str})'
        link = f'/admin/incidents/{incidente.id_incidente}'

        # Notify admins
        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            cls._notify_user(admin.id, msg, title='Nuevo Incidente', category='alert', priority='high', link=link)

        # Notify responsible
        if incidente.responsable_id and incidente.responsable_id != incidente.user_id:
            cls._notify_user(
                incidente.responsable_id, msg, title='Incidente Asignado', category='alert', priority='high', link=link
            )

    @classmethod
    def _notify_inapp_escalation(cls, incidente: Incidente, nivel_anterior: int):
        from app.models.user import User

        nivel_label = {1: 'Advertencia', 2: 'Error Crítico', 3: 'Incidente de Negocio'}.get(
            incidente.escalamiento_nivel, f'Nivel {incidente.escalamiento_nivel}'
        )
        msg = f'Incidente #{incidente.id_incidente} escalado a {nivel_label}: {incidente.titulo}'
        link = f'/admin/incidents/{incidente.id_incidente}'

        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            cls._notify_user(admin.id, msg, title='Escalamiento', category='alert', priority='urgent', link=link)

    @classmethod
    def _notify_inapp_sla_breach(cls, incidente: Incidente):
        from app.models.user import User

        msg = f'SLA VENCIDO - Incidente #{incidente.id_incidente}: {incidente.titulo}'
        link = f'/admin/incidents/{incidente.id_incidente}'

        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            cls._notify_user(admin.id, msg, title='SLA Vencido', category='alert', priority='urgent', link=link)

        if incidente.responsable_id:
            cls._notify_user(
                incidente.responsable_id, msg, title='SLA Vencido', category='alert', priority='urgent', link=link
            )

    @classmethod
    def _notify_inapp_resolution(cls, incidente: Incidente):
        msg = f'Incidente #{incidente.id_incidente} resuelto: {incidente.titulo}'
        link = f'/admin/incidents/{incidente.id_incidente}'

        # Notify creator
        if incidente.user_id:
            cls._notify_user(
                incidente.user_id, msg, title='Incidente Resuelto', category='system', priority='normal', link=link
            )

        # Notify responsible
        if incidente.responsable_id and incidente.responsable_id != incidente.user_id:
            cls._notify_user(
                incidente.responsable_id,
                msg,
                title='Incidente Resuelto',
                category='system',
                priority='normal',
                link=link,
            )
