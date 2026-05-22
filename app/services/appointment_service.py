from app.models import Appointment, db, User
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.utils import get_user_today_utc_range, localize_datetime_for_display
from flask import url_for, current_app
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import or_, and_

class AppointmentService:
    def __init__(self):
        self.notification_service = NotificationService()
        self.email_service = EmailService()
        self.display_timezone = 'America/Lima' # Enforce fixed timezone for notifications

    def validate_session_times(self, start_time, end_time, patient_id, therapist_id, session_id=None, ignore_therapist_conflict=False):
        """Validar horario de sesión y evitar conflictos"""
        errors = []
        
        if start_time >= end_time:
            errors.append("La hora de inicio debe ser anterior a la hora de fin")
            return errors
        
        duration = (end_time - start_time).total_seconds() / 60
        if duration < 15:
            errors.append("La duración mínima de una sesión es 15 minutos")
        if duration > 240:
            errors.append("La duración máxima de una sesión es 4 horas")
        
        # Validacion relajada: hasta 24h atras pa registrar sesiones recientes
        if not session_id and start_time < (datetime.utcnow() - timedelta(hours=24)):
             errors.append("No se pueden crear sesiones con más de 24 horas de antigüedad")
        
        if not ignore_therapist_conflict:
            therapist_conflict = Appointment.query.filter(
                Appointment.therapist_id == therapist_id,
                Appointment.status.in_(['scheduled', 'in_progress']),
                or_(
                    and_(Appointment.start_time <= start_time, Appointment.end_time > start_time),
                    and_(Appointment.start_time < end_time, Appointment.end_time >= end_time),
                    and_(Appointment.start_time >= start_time, Appointment.end_time <= end_time)
                )
            )
            if session_id:
                therapist_conflict = therapist_conflict.filter(Appointment.id != session_id)
            
            if therapist_conflict.first():
                errors.append("Ya tienes una sesión programada en ese horario")
        
        patient_conflict = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.status.in_(['scheduled', 'in_progress']),
            or_(
                and_(Appointment.start_time <= start_time, Appointment.end_time > start_time),
                and_(Appointment.start_time < end_time, Appointment.end_time >= end_time),
                and_(Appointment.start_time >= start_time, Appointment.end_time <= end_time)
            )
        )
        if session_id:
            patient_conflict = patient_conflict.filter(Appointment.id != session_id)
        
        conflicting_patient_appt = patient_conflict.first()
        if conflicting_patient_appt:
            patient = User.query.get(patient_id)
            patient_name = patient.username if patient else "El paciente"
            errors.append(f"{patient_name} ya tiene una sesión programada en ese horario")
        
        return errors

    def get_therapist_appointments(self, therapist_id, start_dt, end_dt):
        return Appointment.query.filter(
            Appointment.therapist_id == therapist_id,
            Appointment.start_time >= start_dt,
            Appointment.start_time <= end_dt
        ).all()

    def get_all_appointments(self, start_dt, end_dt):
        return Appointment.query.filter(
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

    def update_expired_appointments(self, patient_id):
        """Auto-completar citas programadas ya vencidas"""
        now = datetime.utcnow()
        # Check explicit end_time or default 1h duration
        expired = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.status == 'scheduled',
            or_(
                Appointment.end_time < now,
                and_(Appointment.end_time == None, Appointment.start_time < now - timedelta(hours=1))
            )
        ).all()
        
        if expired:
            for appt in expired:
                appt.status = 'completed'
            db.session.commit()

    def get_patient_appointments(self, patient_id, start_dt=None, end_dt=None, limit=10):
        self.update_expired_appointments(patient_id)
        
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
                Appointment.start_time >= today_start
            ).order_by(Appointment.start_time.asc()).limit(limit).all()

    def create_session(self, therapist_id, data, therapist_username):
        from app.models import User, Game, AppointmentGame
        patient_id = data.get('patient_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
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
        
        db.session.add(appt)
        db.session.flush()
        
        # Handle games using new unified method
        games_payload = data.get('games')
        if games_payload:
            games_list = []
            if isinstance(games_payload, str):
                games_list = [g.strip() for g in games_payload.split(',') if g.strip()]
            elif isinstance(games_payload, list):
                games_list = games_payload
            
            if games_list:
                try:
                    self.set_session_games(appt.id, games_list)
                except ValueError as e:
                    # Rollback if game validation fails
                    db.session.rollback()
                    raise e

        db.session.commit()

        try:
            # Convert naive UTC start_time to Peru time for display
            display_time = localize_datetime_for_display(start_time, self.display_timezone)
            fmt_date_time = display_time.strftime('%d/%m/%Y %H:%M')
            fmt_short = display_time.strftime("%d %b %H:%M")

            msg_details = f"Título: {appt.title}\nFecha: {fmt_date_time}\nTerapeuta: {therapist_username}"
            
            self.notification_service.create_notification(
                therapist_id, 
                f'Sesión programada: {appt.title} — {fmt_short}', 
                url_for('therapist.sessions')
            )
            self.notification_service.create_notification(
                patient_id, 
                f'Tienes una nueva sesión programada con {therapist_username} el {fmt_short}', 
                url_for('main.game')
            )
            
            therapist = User.query.get(therapist_id)
            self.email_service.send_session_notification(patient.email, patient.username, "programada", msg_details, 'patient')
            self.email_service.send_session_notification(therapist.email, therapist.username, "programada", f"Paciente: {patient.username}\nFecha: {fmt_date_time}", 'therapist')
        except Exception as e:
            current_app.logger.error(f"Error sending notifications: {e}")
            pass
            
        return appt

    def update_session(self, session_id, data):
        appt = Appointment.query.get(session_id)
        if not appt:
            return None
            
        old_attendance = appt.attendance

        if 'start_time' in data:
            appt.start_time = data.get('start_time')
        if 'end_time' in data:
            appt.end_time = data.get('end_time')
        if 'status' in data:
            appt.status = data.get('status')
        if 'attendance' in data:
            appt.attendance = data.get('attendance')
        if 'notes' in data:
            appt.notes = data.get('notes')
        if 'title' in data:
            appt.title = data.get('title')
            
        if 'attendance' in data:
             patient = User.query.get(appt.patient_id)
             if patient:
                if patient.sessions_attended is None: patient.sessions_attended = 0
                
                if appt.attendance == 'present' and old_attendance != 'present':
                    patient.sessions_attended += 1
                
                elif appt.attendance != 'present' and old_attendance == 'present':
                    if patient.sessions_attended > 0:
                        patient.sessions_attended -= 1
            
        db.session.commit()

        try:
            self.notification_service.create_notification(appt.patient_id, f'Se actualizó la sesión: {appt.title}', link=url_for('patient.calendar'))
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
            self.notification_service.create_notification(therapist_id, f'Sesión eliminada: {title}', link=url_for('therapist.sessions'))
            self.notification_service.create_notification(patient_id, f'Tu sesión programada ({title}) ha sido cancelada.', link=url_for('patient.calendar'))
            
            import threading
            def _send_emails():
                with current_app.app_context():
                    try:
                        therapist = User.query.get(therapist_id)
                        patient = User.query.get(patient_id)
                        details = f"Título: {title}\nLa sesión ha sido eliminada del calendario."
                        if patient:
                            self.email_service.send_session_notification(patient.email, patient.username, "cancelada", details)
                        if therapist:
                            self.email_service.send_session_notification(therapist.email, therapist.username, "cancelada", details)
                    except Exception:
                        pass
            threading.Thread(target=_send_emails, daemon=True).start()
        except Exception:
            pass
            
        return True

    def set_session_games(self, session_id, game_filenames):
        """Asigna juegos a la sesión. Nombres repetidos los salta."""
        from app.models import Game, AppointmentGame
        
        appt = Appointment.query.get(session_id)
        if not appt:
            raise ValueError("Sesión no encontrada")
        
        # Validate all games exist before making any changes
        validated_games = []
        for filename in game_filenames:
            game = Game.query.filter_by(filename=filename, is_active=True).first()
            
            if not game:
                # Check if file exists physically
                game_path = os.path.join(current_app.static_folder, 'games', filename)
                if not os.path.exists(game_path):
                    raise ValueError(f"Juego no encontrado: {filename}")
                
                # Auto-create game entry if file exists
                game = Game(
                    title=filename.replace('.html', '').replace('_', ' ').title(),
                    filename=filename,
                    is_active=True
                )
                db.session.add(game)
                db.session.flush()
            
            validated_games.append(game)
        
        AppointmentGame.query.filter_by(appointment_id=session_id).delete()
        
        for game in validated_games:
            assoc = AppointmentGame(appointment_id=session_id, game_id=game.id)
            db.session.add(assoc)
        
        # Update legacy JSON column for backward compatibility (read-only)
        appt.games = json.dumps([g.filename for g in validated_games])
        
        db.session.commit()
        return validated_games

    def transition_status(self, session_id, new_status, changed_by_user_id=None, notify=True):
        """Cambia estado de sesión con validación"""
        appt = Appointment.query.get(session_id)
        if not appt:
            raise ValueError("Sesión no encontrada")
        
        valid_transitions = {
            'scheduled': ['in_progress', 'completed', 'cancelled'],
            'in_progress': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': []
        }
        
        current_status = appt.status
        
        if new_status not in valid_transitions.get(current_status, []):
            if current_status == new_status:
                return appt  # No change needed
            raise ValueError(
                f"Transición inválida: no se puede cambiar de '{current_status}' a '{new_status}'"
            )
        
        # Additional validation for completing/cancelling
        if new_status == 'completed':
            # Can only complete past or current sessions
            if appt.end_time and appt.end_time > datetime.utcnow():
                # Allow completion if within 15 minutes of end time
                if appt.end_time > datetime.utcnow() + timedelta(minutes=15):
                    raise ValueError("No se puede completar una sesión futura")
        
        old_status = appt.status
        appt.status = new_status
        appt.status_changed_at = datetime.utcnow()
        appt.status_changed_by = changed_by_user_id
        
        try:
            db.session.commit()
            
            if notify:
                self._send_status_change_notification(appt, old_status, new_status)
            
            change_by = "sistema" if not changed_by_user_id else f"usuario {changed_by_user_id}"
            current_app.logger.info(
                f"Sesión {session_id}: {old_status} → {new_status} (por {change_by})"
            )
            
            return appt
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al cambiar estado de sesión {session_id}: {str(e)}")
            raise
    
    def _send_status_change_notification(self, appt, old_status, new_status):
        """Notificar cambio de estado de sesión"""
        try:
            # Determine message based on transition
            messages = {
                'completed': f"Tu sesión '{appt.title}' ha sido marcada como completada",
                'cancelled': f"Tu sesión '{appt.title}' ha sido cancelada",
                'in_progress': f"Tu sesión '{appt.title}' está en progreso"
            }
            
            message = messages.get(new_status, f"Estado de sesión actualizado a {new_status}")
            
            self.notification_service.create_notification(
                user_id=appt.patient_id,
                message=message,
                type='session_update'
            )
            
            # Notify therapist if status was changed automatically
            if not appt.status_changed_by:
                self.notification_service.create_notification(
                    user_id=appt.therapist_id,
                    message=f"Sesión con {appt.patient.username} actualizada automáticamente a '{new_status}'",
                    type='session_update'
                )
                
        except Exception as e:
            # Don't fail the status change if notification fails
            current_app.logger.error(f"Error enviando notificación: {str(e)}")

