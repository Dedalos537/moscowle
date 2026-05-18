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
            current_app.logger.warning("Email not configured in MAIL_USERNAME/MAIL_PASSWORD. Skipping welcome email.")
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
            sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
            msg = MailMessage(subject=subject, recipients=[recipient_email], body=body, sender=sender)
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
    def send_admin_payment_report_v2(admin_email, report_data):
        """
        Send an enhanced weekly report grouped by Sede.
        report_data format: { 'Sede Name': { 'overdue': [], 'upcoming': [], 'uptodate': [] } }
        """
        if not current_app.config.get('MAIL_USERNAME'):
            current_app.logger.info(f"[MOCK EMAIL] Enhanced Report generated for {admin_email}")
            return False
            
        try:
            total_alerts = 0
            for s in report_data.values():
                total_alerts += len(s['overdue']) + len(s['upcoming'])
                
            subject = f"🔔 Reporte de Pagos Moscowle - {total_alerts} Alertas"
            
            # Build HTML Body
            html_body = f"""
            <div style="font-family: sans-serif; color: #333;">
                <h2 style="color: #2c3e50;">Resumen Semanal de Pagos por Sede</h2>
                <p>Hola Admin, aquí tienes el estado de cuentas actualizado.</p>
            """
            
            for sede_name, categories in report_data.items():
                # Correct filtering: check if the categories keys exist
                overdue_list = categories.get('overdue', [])
                upcoming_list = categories.get('upcoming', [])
                
                if not overdue_list and not upcoming_list:
                    continue # Skip sedes with no alerts
                    
                html_body += f"<div style='margin-bottom: 20px; border: 1px solid #eee; padding: 15px; border-radius: 8px;'>"
                html_body += f"<h3 style='margin-top: 0; color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px;'>🏢 {sede_name}</h3>"
                
                # Overdue
                if overdue_list:
                    html_body += "<h4 style='color: #e74c3c; margin-bottom: 5px;'>🔴 Vencidos (Atención Inmediata)</h4>"
                    html_body += "<ul style='padding-left: 20px;'>"
                    for p in overdue_list:
                         html_body += f"""
                         <li style='margin-bottom: 8px;'>
                            <strong>{p.get('name', 'N/A')}</strong> <span style='color: #7f8c8d; font-size: 0.9em;'>({p.get('phone') or 'Sin Tlf'})</span><br>
                            Deuda: <strong>S/ {p.get('amount', 0)}</strong> • Vencido hace: {p.get('days_diff', 0)} días<br>
                            <span style='font-size: 0.85em; color: #95a5a6;'>Último pago: {p.get('last_payment') or 'N/A'}</span>
                         </li>
                         """
                    html_body += "</ul>"
                
                # Upcoming
                if upcoming_list:
                    html_body += "<h4 style='color: #f39c12; margin-bottom: 5px;'>🟡 Por Vencer (Próximos 7 días)</h4>"
                    html_body += "<ul style='padding-left: 20px;'>"
                    for p in upcoming_list:
                         days_diff = p.get('days_diff', 0)
                         days_txt = "¡HOY!" if days_diff == 0 else f"en {days_diff} días"
                         html_body += f"""
                         <li style='margin-bottom: 8px;'>
                            <strong>{p.get('name', 'N/A')}</strong> <span style='color: #7f8c8d; font-size: 0.9em;'>({p.get('phone') or 'Sin Tlf'})</span><br>
                            Monto: <strong>S/ {p.get('amount', 0)}</strong> • Vence: {days_txt} ({p.get('due_date', 'N/A')})<br>
                            <span style='font-size: 0.85em; color: #95a5a6;'>Último pago: {p.get('last_payment') or 'N/A'}</span>
                         </li>
                         """
                    html_body += "</ul>"
                
                # Up to Date (Optional summary)
                # html_body += f"<p style='font-size: 0.9em; color: #27ae60;'>✅ {len(categories['uptodate'])} pacientes al día.</p>"
                
                html_body += "</div>"

            html_body += """
                <p style='font-size: 0.8em; color: #7f8c8d; margin-top: 30px;'>
                    Este reporte fue generado automáticamente por Moscowle AI Agent.
                </p>
            </div>
            """
            
            msg = MailMessage(subject=subject, recipients=[admin_email], html=html_body, body="Por favor habilita HTML para ver este reporte.")
            mail.send(msg)
            current_app.logger.info(f"Enhanced admin report sent to {admin_email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send enhanced admin report: {str(e)}")
            return False
