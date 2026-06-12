from datetime import datetime

from app.models import Appointment


class AppointmentRepository:
    @staticmethod
    def count_total():
        return Appointment.query.count()

    @staticmethod
    def count_by_therapist(therapist_id):
        return Appointment.query.filter_by(therapist_id=therapist_id).count()

    @staticmethod
    def get_upcoming_for_patient(patient_id, limit=3):
        return (
            Appointment.query.filter(
                Appointment.patient_id == patient_id,
                Appointment.start_time >= datetime.utcnow(),
                Appointment.status == 'scheduled',
            )
            .order_by(Appointment.start_time)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_upcoming_for_user(user_id, role, limit=5):
        now = datetime.utcnow()
        query = (
            Appointment.query.filter(Appointment.start_time >= now, Appointment.status != 'cancelled')
            .order_by(Appointment.start_time)
            .limit(limit)
        )
        if role == 'terapista':
            query = query.filter(Appointment.therapist_id == user_id)
        else:
            query = query.filter(Appointment.patient_id == user_id)
        return query.all()
