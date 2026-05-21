from datetime import datetime, timedelta
from app.models import Appointment, User
from app.extensions import db
from sqlalchemy import or_, and_

class AvailabilityService:
    @staticmethod
    def check_availability(therapist_id, start_time, end_time, exclude_appointment_id=None):
        """
        Verifies if a therapist is available for a given time slot.
        Checks for double booking of the therapist.
        Returns (bool, message) tuple.
        """
        conflict_query = Appointment.query.filter(
            Appointment.therapist_id == therapist_id,
            Appointment.status != 'cancelled'
        )
        
        if exclude_appointment_id:
            conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)
            
        # Overlap Logic:
        # Conflict if existing appointment starts BEFORE new ends AND ends AFTER new starts
        conflicts = conflict_query.filter(
            Appointment.start_time < end_time,
            Appointment.end_time > start_time
        ).all()
        
        if conflicts:
            conflicting_ids = [str(c.id) for c in conflicts]
            # Get therapist name for context
            therapist = User.query.get(therapist_id)
            t_name = therapist.username if therapist else "El terapeuta"
            return False, f"{t_name} ya tiene una sesión agendada en ese horario (Cruce: Sesión {', '.join(conflicting_ids)})"
            
        return True, "Disponible"
