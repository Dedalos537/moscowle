from flask import current_app
from flask_mail import Message as MailMessage
from app.extensions import mail
import secrets
import string

class EmailService:
    @staticmethod
    def generate_password(length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password

    @staticmethod
    def send_welcome_email(recipient_email: str, plain_password: str, username: str):
        """Send a welcome email with credentials."""
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            current_app.logger.warning("Email not configured. Skipping welcome email.")
            return False
        try:
            subject = "Bienvenido a Moscowle"
            body = (
                f"Hola {username or recipient_email},\n\n"
                f"Tu cuenta ha sido creada exitosamente en Moscowle.\n\n"
                f"Credenciales de acceso:\n"
                f"Correo: {recipient_email}\n"
                f"Contraseña temporal: {plain_password}\n\n"
                f"Inicia sesión y cambia tu contraseña temporal por una más segura desde tu perfil.\n\n"
                "Saludos,\nEquipo Moscowle"
            )
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
            mail.send(msg)
            current_app.logger.info(f"Welcome email sent successfully to {recipient_email}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send welcome email to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_password_change_email(recipient_email: str, new_password: str, username: str):
        """Send an email notifying password change."""
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            current_app.logger.warning("Email not configured. Skipping password change email.")
            return False
        try:
            subject = "Cambio de contraseña en Moscowle"
            body = (
                f"Hola {username or recipient_email},\n\n"
                f"Tu contraseña ha sido actualizada exitosamente.\n\n"
                f"Nueva contraseña: {new_password}\n\n"
                "Si no realizaste este cambio, por favor contacta al administrador de inmediato.\n\n"
                "Saludos,\nEquipo Moscowle"
            )
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
            mail.send(msg)
            current_app.logger.info(f"Password change email sent to {recipient_email}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send password change email to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_payment_reminder(recipient_email, username, days_until_due, due_date, amount):
        """Send a payment reminder email."""
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.warning("Email not configured. Skipping payment reminder.")
            # For development without email, we just log it as sent
            current_app.logger.info(f"[MOCK EMAIL] To: {recipient_email} | Subject: Recordatorio de Pago | Body: Vence en {days_until_due} dias")
            return True
            
        try:
            if days_until_due == 0:
                subject = "URGENTE: Tu pago vence hoy - Moscowle"
                urgency_text = "vence HOY"
            elif days_until_due < 0:
                subject = "URGENTE: Tu pago está vencido - Moscowle"
                urgency_text = f"venció hace {abs(days_until_due)} días"
            else:
                subject = f"Recordatorio: Tu pago vence pronto - Moscowle"
                urgency_text = f"vence en {days_until_due} días"

            body = (
                f"Hola {username},\n\n"
                f"Te recordamos que tu próximo pago de S/ {amount:.2f} {urgency_text}.\n"
                f"Fecha límite: {due_date.strftime('%d/%m/%Y')}\n\n"
                "Por favor, realiza el pago para evitar la suspensión de tu cuenta.\n"
                "Si ya realizaste el pago, por favor ignora este mensaje o contacta a administración.\n\n"
                "Saludos,\nEquipo Moscowle"
            )
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
            mail.send(msg)
            current_app.logger.info(f"Payment reminder email sent to {recipient_email}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send payment reminder to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_payment_confirmation(recipient_email, username, amount, date, method):
        """Send a payment confirmation email."""
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.warning("Email not configured. Skipping payment confirmation.")
            return False
            
        try:
            subject = "Confirmación de Pago - Moscowle"
            body = (
                f"Hola {username},\n\n"
                f"Hemos recibido tu pago exitosamente.\n\n"
                f"Detalles del pago:\n"
                f"Monto: S/ {amount:.2f}\n"
                f"Fecha: {date.strftime('%d/%m/%Y %H:%M')}\n"
                f"Método: {method}\n\n"
                "Gracias por mantener tu cuenta al día.\n\n"
                "Saludos,\nEquipo Moscowle"
            )
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
            mail.send(msg)
            current_app.logger.info(f"Payment confirmation email sent to {recipient_email}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send payment confirmation to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_session_notification(recipient_email, username, action, details, user_role='patient'):
        """
        Send session notification (created, updated, cancelled).
        action: 'programada', 'actualizada', 'cancelada'
        """
        if not current_app.config.get('MAIL_USERNAME'):
            return False
            
        try:
            subject = f"Sesión {action} - Moscowle"
            
            if action == 'programada':
                intro = "Se ha programado una nueva sesión."
            elif action == 'actualizada':
                intro = "Tu sesión ha sido actualizada."
            elif action == 'cancelada':
                intro = "Una sesión ha sido cancelada."
            else:
                intro = "Notificación de sesión."

            body = (
                f"Hola {username},\n\n"
                f"{intro}\n\n"
                f"Detalles:\n{details}\n\n"
                "Ingresa a la plataforma para ver más información.\n\n"
                "Saludos,\nEquipo Moscowle"
            )
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
            mail.send(msg)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send session notification to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_new_message_email(recipient_email, recipient_name, sender_name, message_snippet=""):
        """Send a notification about a new private message."""
        if not current_app.config.get('MAIL_USERNAME'):
            return False
            
        try:
            subject = f"Nuevo mensaje de {sender_name} - Moscowle"
            body = (
                f"Hola {recipient_name},\n\n"
                f"Has recibido un nuevo mensaje de {sender_name}.\n\n"
                f"\"{message_snippet}\"\n\n"
                "Inicia sesión para responder.\n\n"
                "Saludos,\nEquipo Moscowle"
            )
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
            mail.send(msg)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send message notification to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_admin_payment_report(admin_email, overdue_list, upcoming_list):
        """Send a weekly report of payments to admin."""
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.info(f"[MOCK EMAIL] To Admin: {admin_email} | Payment Report Generated")
            return False
            
        try:
            subject = f"Reporte Semanal de Pagos - {len(upcoming_list)} Por Vencer"
            
            body = "Hola Admin,\n\nEste es el reporte de pagos para la semana.\n\n"
            
            if overdue_list:
                body += "🔴 PAGOS VENCIDOS:\n"
                for i in overdue_list:
                    body += f"- {i['name']} ({i['email']}): S/ {i['amount']} (Hace {i['days']} días) - Vence: {i['due_date']}\n"
                body += "\n"
                
            if upcoming_list:
                body += "🟡 PAGOS POR VENCER (Próx. 7 días):\n"
                for i in upcoming_list:
                    days_txt = "HOY" if i['days'] == 0 else f"en {i['days']} días"
                    body += f"- {i['name']} ({i['email']}): S/ {i['amount']} ({days_txt}) - Vence: {i['due_date']}\n"
                body += "\n"
            
            if not overdue_list and not upcoming_list:
                body += "No hay pagos pendientes para esta semana.\n"
                
            body += "\nPor favor, contacta a los usuarios correspondientes.\n"
            body += "Saludos,\nSistema Moscowle"
            
            msg = MailMessage(subject=subject, recipients=[admin_email], body=body)
            mail.send(msg)
            current_app.logger.info(f"Admin payment report sent to {admin_email}")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to send admin payment report: {str(e)}")
            return False
