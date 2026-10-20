import html as _html
import re
import secrets
import string

from flask import current_app
from flask_mail import Message as MailMessage

from app.extensions import mail

UNSUBSCRIBE_PATH = '/api/public/email/unsubscribe'
NEW_MESSAGE_COOLDOWN_MINUTES = 30

# Correos que el sistema genera cuando no se dio uno (pacientes sin correo): nunca se les escribe.
_PLACEHOLDER_PREFIXES = ('noemail_', 'temp_')
_PLACEHOLDER_DOMAINS = ('local', 'localhost', 'invalid')


def is_real_email(address):
    """True si es un correo dado por la persona (no el generado `noemail_…@local` / `temp_…`)."""
    addr = (address or '').strip().lower()
    if '@' not in addr or addr.startswith(_PLACEHOLDER_PREFIXES):
        return False
    domain = addr.rsplit('@', 1)[1]
    return bool(domain) and domain not in _PLACEHOLDER_DOMAINS and not domain.endswith('.local')


def recipient_for(user):
    """A quién se le escribe: para un paciente, el correo del apoderado si lo tiene; si no, el suyo si es real.

    Si no hay ningún correo real, None: el aviso queda solo en la app (y WhatsApp donde aplique). En cuanto se
    registre un correo real, los envíos vuelven solos.
    """
    if not user:
        return None
    if getattr(user, 'role', None) == 'jugador':
        guardian = (getattr(user, 'guardian_contact', None) or '').strip()
        if is_real_email(guardian):
            return guardian
    own = (getattr(user, 'email', None) or '').strip()
    return own if is_real_email(own) else None


def _send(msg):
    """Último filtro antes de Gmail: quita direcciones generadas; si no queda ninguna, no envía."""
    msg.recipients = [r for r in (msg.recipients or []) if is_real_email(r if isinstance(r, str) else r[-1])]
    if not msg.recipients:
        current_app.logger.info(f'Correo «{msg.subject}» no enviado: sin dirección real (aviso solo en la app)')
        return False
    mail.send(msg)
    return True


def _html_to_text(markup):
    """Alternativa de texto plano para un correo HTML (clientes sin HTML y filtros antispam)."""
    text = re.sub(r'(?is)<(script|style).*?</\1>', '', markup or '')
    text = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|h[1-6]|li)>', '\n', text)
    text = _html.unescape(re.sub(r'<[^>]+>', '', text))
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n\s*\n\s*\n+', '\n\n', text).strip()


def _make_message(subject, recipients, body=None, html=None, user_id=None):
    """Mensaje de NOTIFICACION: parte html con alternativa de texto, remitente con nombre,
    cabeceras de correo automatico y, si se conoce al usuario, baja con un clic (RFC 8058).
    Son las senales con las que Gmail distingue una notificacion de un correo personal."""
    cfg = current_app.config
    address = cfg.get('MAIL_DEFAULT_SENDER') or cfg.get('MAIL_USERNAME')
    if isinstance(address, str) and '<' not in address:
        sender = (cfg.get('MAIL_SENDER_NAME') or 'Notificaciones', address)
    else:
        sender = address
    headers = {
        'Auto-Submitted': 'auto-generated',
        'X-Auto-Response-Suppress': 'OOF, AutoReply',
    }
    if user_id:
        from app.utils.email_tokens import make_unsubscribe_token

        base = (cfg.get('PUBLIC_API_URL') or '').rstrip('/')
        headers['List-Unsubscribe'] = f'<{base}{UNSUBSCRIBE_PATH}?t={make_unsubscribe_token(user_id)}>'
        headers['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
    text = body if body is not None else (_html_to_text(html) if html else '')
    return MailMessage(
        subject=subject,
        recipients=recipients if isinstance(recipients, list) else [recipients],
        body=text,
        html=html,
        sender=sender,
        extra_headers=headers,
    )


class EmailService:
    @staticmethod
    def generate_password(length=12):
        """Genera una clave segura al azar"""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password

    @staticmethod
    def send_welcome_email(recipient_email: str, plain_password: str = None, username: str = None):
        """Bienvenida SIN contraseña en el correo: código de acceso + enlace para crearla (un solo uso, 72 h).

        `plain_password` se mantiene por compatibilidad con quienes llaman, pero ya no se escribe en el correo.
        """
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            current_app.logger.warning('Email not configured in MAIL_USERNAME/MAIL_PASSWORD. Skipping welcome email.')
            return False
        try:
            from app.models import User
            from app.utils.email_tokens import set_password_link

            user = User.query.filter(User.email == recipient_email).first()
            to = recipient_for(user) if user else (recipient_email if is_real_email(recipient_email) else None)
            if not to:
                return False
            code_line = f'Tu código de acceso: {user.login_code}\n' if user and user.login_code else ''
            link_line = (
                f'Crea tu contraseña aquí (el enlace sirve una vez y vence en 72 horas):\n{set_password_link(user)}\n\n'
                if user
                else ''
            )
            body = (
                f'Hola {username or (user.username if user else recipient_email)},\n\n'
                'Tu cuenta en la plataforma del Centro de Terapias Juan Pablo II ya está lista.\n\n'
                f'{code_line}Correo: {recipient_email}\n\n'
                f'{link_line}'
                'Si no esperabas este correo, puedes ignorarlo.\n\n'
                'Saludos,\nCentro de Terapias Juan Pablo II'
            )
            msg = _make_message('Bienvenido(a) al Centro Juan Pablo II', [to], body)
            if not _send(msg):
                return False
            current_app.logger.info(f'Welcome email sent successfully to {to}')
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to send welcome email to {recipient_email}: {str(e)}')
            return False

    @staticmethod
    def send_password_change_email(recipient_email: str, new_password: str = None, username: str = None):
        """Aviso de cambio de contraseña SIN la contraseña: fecha y enlace por si no fue la persona (o no la conoce,
        cuando la cambió un administrador)."""
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            current_app.logger.warning('Email not configured. Skipping password change email.')
            return False
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            from app.models import User
            from app.utils.email_tokens import set_password_link

            user = User.query.filter(User.email == recipient_email).first()
            to = recipient_for(user) if user else (recipient_email if is_real_email(recipient_email) else None)
            if not to:
                return False
            when = datetime.now(ZoneInfo('America/Lima')).strftime('%d/%m/%Y a las %H:%M')
            link = (
                f'\n\nSi no fuiste tú, o no conoces la nueva contraseña, créala aquí (un solo uso, 72 h):\n{set_password_link(user)}'
                if user
                else ''
            )
            body = (
                f'Hola {username or recipient_email},\n\n'
                f'La contraseña de tu cuenta se cambió el {when}.{link}\n\n'
                'Si no reconoces este cambio, avisa al centro de inmediato.\n\n'
                'Saludos,\nCentro de Terapias Juan Pablo II'
            )
            msg = _make_message('Se cambió tu contraseña', [to], body)
            if not _send(msg):
                return False
            current_app.logger.info(f'Password change email sent to {to}')
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to send password change email to {recipient_email}: {str(e)}')
            return False

    @staticmethod
    def send_email(
        recipient=None, subject=None, body=None, *, recipients=None, text_body=None, html=None, user_id=None
    ):
        """Compatibilidad: 3 lugares llamaban a `EmailService.send_email`, que no existía (esos correos nunca
        salían: recordatorio manual de deuda, renovación y cambio de contraseña por admin)."""
        to = list(recipients or ([recipient] if recipient else []))
        return EmailService.send_notification_email(subject, to, body=body or text_body, html=html, user_id=user_id)

    @staticmethod
    def send_payment_reminder(recipient_email, username, days_until_due, due_date, amount):
        """Recordatorio de pago"""
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.warning('Email not configured. Skipping payment reminder.')
            current_app.logger.info(
                f'[MOCK EMAIL] To: {recipient_email} | Subject: Recordatorio de Pago | Body: Vence en {days_until_due} dias'
            )
            return True

        try:
            if days_until_due == 0:
                subject = 'URGENTE: Tu pago vence hoy - Moscowle'
                urgency_text = 'vence HOY'
            elif days_until_due < 0:
                subject = 'URGENTE: Tu pago está vencido - Moscowle'
                urgency_text = f'venció hace {abs(days_until_due)} días'
            else:
                subject = 'Recordatorio: Tu pago vence pronto - Moscowle'
                urgency_text = f'vence en {days_until_due} días'

            body = (
                f'Hola {username},\n\n'
                f'Te recordamos que tu próximo pago de S/ {amount:.2f} {urgency_text}.\n'
                f'Fecha límite: {due_date.strftime("%d/%m/%Y")}\n\n'
                'Por favor, realiza el pago para evitar la suspensión de tu cuenta.\n'
                'Si ya realizaste el pago, por favor ignora este mensaje o contacta a administración.\n\n'
                'Saludos,\nEquipo Moscowle'
            )
            msg = _make_message(subject, [recipient_email], body)
            if not _send(msg):
                return False
            current_app.logger.info(f'Payment reminder email sent to {recipient_email}')
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to send payment reminder to {recipient_email}: {str(e)}')
            return False

    @staticmethod
    def send_payment_confirmation(recipient_email, username, amount, date, method):
        """Confirmación de pago"""
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.warning('Email not configured. Skipping payment confirmation.')
            return False

        try:
            subject = 'Confirmación de Pago - Moscowle'
            body = (
                f'Hola {username},\n\n'
                f'Hemos recibido tu pago exitosamente.\n\n'
                f'Detalles del pago:\n'
                f'Monto: S/ {amount:.2f}\n'
                f'Fecha: {date.strftime("%d/%m/%Y %H:%M")}\n'
                f'Método: {method}\n\n'
                'Gracias por mantener tu cuenta al día.\n\n'
                'Saludos,\nEquipo Moscowle'
            )
            msg = _make_message(subject, [recipient_email], body)
            if not _send(msg):
                return False
            current_app.logger.info(f'Payment confirmation email sent to {recipient_email}')
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to send payment confirmation to {recipient_email}: {str(e)}')
            return False

    @staticmethod
    def send_session_notification(recipient_email, username, action, details, user_role='patient'):
        """Notificación de sesión: programada, actualizada, cancelada"""
        if not current_app.config.get('MAIL_USERNAME'):
            return False

        try:
            subject = f'Sesión {action} - Moscowle'

            if action == 'programada':
                intro = 'Se ha programado una nueva sesión.'
            elif action == 'actualizada':
                intro = 'Tu sesión ha sido actualizada.'
            elif action == 'cancelada':
                intro = 'Una sesión ha sido cancelada.'
            else:
                intro = 'Notificación de sesión.'

            body = (
                f'Hola {username},\n\n'
                f'{intro}\n\n'
                f'Detalles:\n{details}\n\n'
                'Ingresa a la plataforma para ver más información.\n\n'
                'Saludos,\nEquipo Moscowle'
            )
            msg = _make_message(subject, [recipient_email], body)
            return _send(msg)
        except Exception as e:
            current_app.logger.error(f'Failed to send session notification to {recipient_email}: {str(e)}')
            return False

    @staticmethod
    def send_new_message_email(recipient_email, recipient_name, sender_name, message_snippet=''):
        """Aviso de mensaje nuevo"""
        if not current_app.config.get('MAIL_USERNAME'):
            return False

        from app.models.email_throttle import EmailThrottle

        # Un correo por conversacion cada 30 min (el aviso en la app sigue siendo uno por mensaje).
        if not EmailThrottle.allow(f'newmsg:{recipient_email}:{sender_name}', NEW_MESSAGE_COOLDOWN_MINUTES):
            return False

        try:
            subject = f'Nuevo mensaje de {sender_name} - Moscowle'
            body = (
                f'Hola {recipient_name},\n\n'
                f'Has recibido un nuevo mensaje de {sender_name}.\n\n'
                f'"{message_snippet}"\n\n'
                'Inicia sesión para responder.\n\n'
                'Saludos,\nEquipo Moscowle'
            )
            msg = _make_message(subject, [recipient_email], body)
            return _send(msg)
        except Exception as e:
            current_app.logger.error(f'Failed to send message notification to {recipient_email}: {str(e)}')
            return False

    @staticmethod
    def send_password_reset_code(recipient_email: str, username: str, code: str):
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            current_app.logger.warning('Email not configured. Skipping password reset code email.')
            return False
        try:
            subject = 'Código de recuperación - Moscowle'
            body = (
                f'Hola {username or recipient_email},\n\n'
                f'Has solicitado restablecer tu contraseña.\n\n'
                f'Tu código de verificación es: {code}\n\n'
                f'Este código expira en 30 minutos.\n\n'
                'Si no solicitaste este cambio, ignora este mensaje.\n\n'
                'Saludos,\nEquipo Moscowle'
            )
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
            if not _send(msg):
                return False
            current_app.logger.info(f'Password reset code sent to {recipient_email}')
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to send password reset code to {recipient_email}: {str(e)}')
            return False

    @staticmethod
    def send_password_reset_notification_admin(admin_email: str, user_email: str, username: str):
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            current_app.logger.warning('Email not configured. Skipping admin reset notification.')
            return False
        try:
            subject = 'Solicitud de cambio de contraseña - Moscowle'
            body = (
                f'Hola Administrador,\n\n'
                f'El usuario {username or user_email} ({user_email}) ha solicitado un cambio de contraseña.\n\n'
                f'Ingresa al panel de administración para revisar la solicitud.\n\n'
                'Saludos,\nEquipo Moscowle'
            )
            msg = MailMessage(subject=subject, recipients=[admin_email], body=body)
            if not _send(msg):
                return False
            current_app.logger.info(f'Password reset notification sent to admin {admin_email}')
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to send admin reset notification: {str(e)}')
            return False

    @staticmethod
    def send_admin_payment_report_v2(admin_email, report_data):
        """Reporte semanal agrupado por sede"""
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.info(f'[MOCK EMAIL] Enhanced Report generated for {admin_email}')
            return False

        try:
            total_alerts = 0
            for s in report_data.values():
                total_alerts += len(s['overdue']) + len(s['upcoming'])

            subject = f' Reporte de Pagos Moscowle - {total_alerts} Alertas'

            html_body = """
            <div style="font-family: sans-serif; color: #333;">
                <h2 style="color: #2c3e50;">Resumen Semanal de Pagos por Sede</h2>
                <p>Hola Admin, aquí tienes el estado de cuentas actualizado.</p>
            """

            for sede_name, categories in report_data.items():
                overdue_list = categories.get('overdue', [])
                upcoming_list = categories.get('upcoming', [])

                if not overdue_list and not upcoming_list:
                    continue

                html_body += (
                    "<div style='margin-bottom: 20px; border: 1px solid #eee; padding: 15px; border-radius: 8px;'>"
                )
                html_body += f"<h3 style='margin-top: 0; color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px;'> {sede_name}</h3>"

                if overdue_list:
                    html_body += "<h4 style='color: #e74c3c; margin-bottom: 5px;'> Vencidos (Atención Inmediata)</h4>"
                    html_body += "<ul style='padding-left: 20px;'>"
                    for p in overdue_list:
                        html_body += f"""
                         <li style='margin-bottom: 8px;'>
                            <strong>{p.get('name', 'N/A')}</strong> <span style='color: #7f8c8d; font-size: 0.9em;'>({p.get('phone') or 'Sin Tlf'})</span><br>
                            Deuda: <strong>S/ {p.get('amount', 0)}</strong> • Vencido hace: {p.get('days_diff', 0)} días<br>
                            <span style='font-size: 0.85em; color: #95a5a6;'>Último pago: {p.get('last_payment') or 'N/A'}</span>
                         </li>
                         """
                    html_body += '</ul>'

                if upcoming_list:
                    html_body += "<h4 style='color: #f39c12; margin-bottom: 5px;'> Por Vencer (Próximos 7 días)</h4>"
                    html_body += "<ul style='padding-left: 20px;'>"
                    for p in upcoming_list:
                        days_diff = p.get('days_diff', 0)
                        days_txt = '¡HOY!' if days_diff == 0 else f'en {days_diff} días'
                        html_body += f"""
                         <li style='margin-bottom: 8px;'>
                            <strong>{p.get('name', 'N/A')}</strong> <span style='color: #7f8c8d; font-size: 0.9em;'>({p.get('phone') or 'Sin Tlf'})</span><br>
                            Monto: <strong>S/ {p.get('amount', 0)}</strong> • Vence: {days_txt} ({p.get('due_date', 'N/A')})<br>
                            <span style='font-size: 0.85em; color: #95a5a6;'>Último pago: {p.get('last_payment') or 'N/A'}</span>
                         </li>
                         """
                    html_body += '</ul>'

                html_body += '</div>'

            html_body += """
                <p style='font-size: 0.8em; color: #7f8c8d; margin-top: 30px;'>
                    Este reporte fue generado automáticamente por Moscowle AI Agent.
                </p>
            </div>
            """

            msg = MailMessage(
                subject=subject,
                recipients=[admin_email],
                html=html_body,
                body='Por favor habilita HTML para ver este reporte.',
            )
            if not _send(msg):
                return False
            current_app.logger.info(f'Enhanced admin report sent to {admin_email}')
            return True

        except Exception as e:
            current_app.logger.error(f'Failed to send enhanced admin report: {str(e)}')
            return False

    @staticmethod
    def send_notification_email(subject, recipients, body=None, html=None, user_id=None):
        """Correo de notificacion generico. ``html`` va en su parte propia (con ``body`` como
        alternativa de texto; si falta se deriva del HTML). ``user_id`` habilita la baja."""
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.info(f'[MOCK EMAIL] {subject} to {recipients}')
            return False
        try:
            return _send(_make_message(subject, recipients, body, html=html, user_id=user_id))
        except Exception as e:
            current_app.logger.error(f'Failed to send notification email: {e}')
            return False
