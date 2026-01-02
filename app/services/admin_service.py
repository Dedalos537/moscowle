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
        if User.query.filter_by(email=email).first():
            return False, "El correo ya está registrado"
            
        plain_password = self.email_service.generate_password()
        hashed_password = bcrypt.generate_password_hash(plain_password).decode('utf-8')
        
        user = User(
            username=data.get('username'),
            email=email,
            password=hashed_password,
            role=data.get('role'),
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Send email
        self.email_service.send_welcome_email(email, plain_password, user.username)
        
        return True, user

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
            except Exception:
                pass
                
        db.session.commit()
        return True, len(recipients)
