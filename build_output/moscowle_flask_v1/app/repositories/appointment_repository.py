from app.models import Appointment, db

class AppointmentRepository:
    @staticmethod
    def count_total():
        return Appointment.query.count()

    @staticmethod
    def count_by_therapist(therapist_id):
        return Appointment.query.filter_by(therapist_id=therapist_id).count()

    @staticmethod
    def get_upcoming_for_patient(patient_id, limit=3):
        from datetime import datetime
        return Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.start_time >= datetime.utcnow(),
            Appointment.status == 'scheduled'
        ).order_by(Appointment.start_time).limit(limit).all()
