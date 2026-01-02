from app.models import Appointment, db, User
from app.services.notification_service import NotificationService
from app.utils import get_user_today_utc_range
from flask import url_for
import json
from datetime import datetime, timedelta

class AppointmentService:
    def __init__(self):
        self.notification_service = NotificationService()

    def get_therapist_appointments(self, therapist_id, start_dt, end_dt):
        return Appointment.query.filter(
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= start_dt,
            Appointment.start_time <= end_dt
        ).all()

    def get_upcoming_sessions(self, therapist_id, limit=20):
        now = datetime.utcnow()
        return Appointment.query.filter(
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= now,
            Appointment.status == 'scheduled'
        ).order_by(Appointment.start_time.asc()).limit(limit).all()

    def get_patient_appointments(self, patient_id, start_dt=None, end_dt=None, limit=10):
        query = Appointment.query.filter(Appointment.patient_id == patient_id)
        if start_dt and end_dt:
            return query.filter(
                Appointment.start_time >= start_dt,
                Appointment.start_time <= end_dt
            ).order_by(Appointment.start_time.asc()).all()
        else:
            # Default: upcoming and today's sessions
            # Use user's timezone to determine "today"
            patient = User.query.get(patient_id)
            if patient:
                today_start, _ = get_user_today_utc_range(patient)
            else:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            return query.filter(
                Appointment.start_time >= today_start,
                Appointment.status == 'scheduled'
            ).order_by(Appointment.start_time.asc()).limit(limit).all()

    def create_session(self, therapist_id, data, therapist_username):
        from app.models import User, Game, AppointmentGame
        patient_id = data.get('patient_id')
        start_time = data.get('start_time') # Assumes datetime object
        end_time = data.get('end_time') # Assumes datetime object
        
        patient = User.query.get(patient_id)
        if not patient or patient.role != 'jugador':
            raise ValueError("Paciente no válido")

        appt = Appointment(
            therapist_id=therapist_id,
            patient_id=patient_id,
            title=data.get('title') or f"Sesión con {patient.username}",
            start_time=start_time,
            end_time=end_time,
            notes=data.get('notes'),
            location=data.get('location'),
            status=data.get('status') or 'scheduled'
        )
        
        # Handle games
        games_payload = data.get('games')
        games_list = []
        if games_payload:
            if isinstance(games_payload, str):
                games_list = [g.strip() for g in games_payload.split(',') if g.strip()]
            elif isinstance(games_payload, list):
                games_list = games_payload
        
        # Legacy support: save to JSON column
        if games_list:
            appt.games = json.dumps(games_list)
        
        db.session.add(appt)
        db.session.flush() # Get ID
        
        # New support: save to AppointmentGame table
        if games_list:
            for game_filename in games_list:
                # Find game by filename
                game = Game.query.filter_by(filename=game_filename).first()
                if game:
                    assoc = AppointmentGame(appointment_id=appt.id, game_id=game.id)
                    db.session.add(assoc)
                else:
                    # Auto-create if missing (fallback for custom/legacy files not in DB yet)
                    # Ideally we shouldn't do this, but for stability:
                    pass 

        db.session.commit()

        # Notifications
        try:
            self.notification_service.create_notification(therapist_id, f'Sesión programada: {appt.title} — {start_time.strftime("%d %b %H:%M")}', url_for('main.sessions'))
            self.notification_service.create_notification(patient_id, f'Tienes una nueva sesión programada con {therapist_username} el {start_time.strftime("%d %b %H:%M")}', url_for('main.game'))
        except Exception:
            pass
            
        return appt

    def update_session(self, session_id, data):
        appt = Appointment.query.get(session_id)
        if not appt:
            return None
            
        if 'start_time' in data:
            appt.start_time = data.get('start_time')
        if 'end_time' in data:
            appt.end_time = data.get('end_time')
        if 'status' in data:
            appt.status = data.get('status')
        if 'notes' in data:
            appt.notes = data.get('notes')
        if 'title' in data:
            appt.title = data.get('title')
            
        db.session.commit()

        try:
            self.notification_service.create_notification(appt.patient_id, f'Se actualizó la sesión: {appt.title}', url_for('main.calendar_patient'))
        except Exception:
            pass
            
        return appt

    def delete_session(self, session_id, therapist_id):
        appt = Appointment.query.get(session_id)
        if not appt:
            return False
            
        patient_id = appt.patient_id
        title = appt.title
        
        db.session.delete(appt)
        db.session.commit()

        try:
            self.notification_service.create_notification(therapist_id, f'Sesión eliminada: {title}', url_for('main.sessions'))
            self.notification_service.create_notification(patient_id, f'Tu sesión programada ({title}) ha sido cancelada.', url_for('main.calendar_patient'))
        except Exception:
            pass
            
        return True
