from app.models import User, db
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.extensions import bcrypt

class AdminService:
    def __init__(self):
        self.notification_service = NotificationService()
        self.email_service = EmailService()

    def assign_therapist(self, patient_id, therapist_id):
        patient = User.query.get(patient_id)
        therapist = User.query.get(therapist_id)
        
        if not patient or not therapist:
            return False, "Usuario no encontrado"
            
        if patient.role != 'jugador' or therapist.role != 'terapista':
            return False, "Roles inválidos"
            
        patient.assigned_therapist_id = therapist.id
        db.session.commit()
        
        try:
            self.notification_service.create_notification(patient.id, f"Terapeuta asignado: {therapist.username}")
            self.notification_service.create_notification(therapist.id, f"Nuevo paciente asignado: {patient.username}")
        except Exception:
            pass
            
        return True, "Asignación exitosa"

    def create_user(self, data):
        email = data.get('email', '').strip().lower()
        role = data.get('role')
        username = data.get('username')
        
        # 1. Validation for Duplicate Email (only if email provided)
        if email:
            if User.query.filter_by(email=email).first():
                return False, "El correo ya está registrado"
        
        # 2. Handle "No Email" case
        import uuid # Keep this just in case, but usually better at top. 
        # Actually I will move it to top in next edit if I care, but just fixing the logic.
        
        is_active = True
        plain_password = None
        
        if not email:
            # Generate fake unique email for DB constraint
            email = f"noemail_{uuid.uuid4().hex[:8]}@local"
            # Random password, user can't login anyway
            plain_password = uuid.uuid4().hex 
            is_active = False # Inactive until they provide real email
        else:
            # Normal flow
            plain_password = self.email_service.generate_password()
            is_active = True
            
        hashed_password = bcrypt.generate_password_hash(plain_password).decode('utf-8')
        
        user = User(
            username=username or email.split('@')[0],
            email=email,
            password=hashed_password,
            role=role,
            is_active=is_active
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Send email only if real email
        if is_active and 'noemail_' not in email:
            try:
                self.email_service.send_welcome_email(email, plain_password, user.username)
            except Exception:
                pass # Don't block creation if email fails
        
        # Return object with user and password
        return True, {'user': user, 'temp_password': plain_password if is_active else 'N/A (Presencial)'}

    def reset_user_password(self, user_id, new_password=None):
        """
        Resets user password. 
        If 1st time (count=0), admin usually sets it manually.
        Subsequent times, it can be auto-generated.
        """
        user = User.query.get(user_id)
        if not user:
            return False, "Usuario no encontrado"

        # Limit removed as per user request
        # if user.admin_password_changed_count >= 1: ...

        plain_password = new_password if new_password else self.email_service.generate_password()
        hashed_password = bcrypt.generate_password_hash(plain_password).decode('utf-8')

        user.password = hashed_password
        user.admin_password_changed_count += 1
        db.session.commit()
        
        # Notify user via email
        try:
            msg_type = "manual" if new_password else "automatico"
            self.email_service.send_email(
                user.email,
                "Tu contraseña ha sido actualizada",
                f"Hola {user.username},\n\nTu contraseña ha sido actualizada ({msg_type}).\nNueva contraseña: {plain_password}\n\nPor favor, contacta con soporte si no solicitaste esto."
            )
        except Exception:
            pass
            
        return True, plain_password

    def update_user(self, data):
        user_id = data.get('id')
        user = User.query.get(user_id)
        if not user:
            return False, "Usuario no encontrado"
            
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            # Check uniqueness if email changed
            new_email = data['email'].strip().lower()
            if new_email != user.email:
                if User.query.filter_by(email=new_email).first():
                    return False, "El correo ya está en uso"
                user.email = new_email
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
            
        db.session.commit()
        return True, user

    def list_users(self, role=None):
        q = User.query
        if role in ('terapista', 'jugador'):
            q = q.filter_by(role=role)
        return q.order_by(User.username.asc()).all()

    def broadcast_message(self, sender_id, subject, body, target, receiver_id=None):
        from app.models import Message
        from flask import url_for
        
        recipients = []
        if target == 'single' and receiver_id:
            u = User.query.get(receiver_id)
            if not u:
                return False, "Destinatario no encontrado"
            recipients = [u]
        else:
            q = User.query
            if target in ('terapista','jugador'):
                q = q.filter_by(role=target)
            recipients = q.all()
            
        for u in recipients:
            msg = Message(sender_id=sender_id, receiver_id=u.id, subject=subject, body=body)
            db.session.add(msg)
            try:
                self.notification_service.create_notification(u.id, f"Mensaje del administrador: {subject or 'Sin asunto'}", url_for('main.messages_list'))
                
                # Send email
                self.email_service.send_new_message_email(
                    u.email,
                    u.username,
                    "Administrador",
                    body[:100] + '...' if body and len(body) > 100 else body
                )
            except Exception:
                pass
                
        db.session.commit()
        return True, len(recipients)
