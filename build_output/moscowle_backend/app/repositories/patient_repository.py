from app.models import User, Payment, Sede
from sqlalchemy import func

class PatientRepository:
    """Repository providing queries related to patients and payments."""
    def get_active_patients(self):
        return User.query.filter_by(role='jugador', is_active=True).all()

    def get_patient(self, patient_id):
        return User.query.get(patient_id)

    def get_last_payment_date(self, patient_id):
        last = Payment.query.filter_by(patient_id=patient_id, status='completed')\
            .order_by(Payment.date.desc()).first()
        return last.date.date() if last and last.date else None

    def get_total_paid(self, patient_id):
        total = Payment.query.with_entities(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.patient_id == patient_id,
            Payment.status == 'completed'
        ).scalar() or 0.0
        return float(total)

    def get_sede_for_patient(self, patient):
        """Return (sede_id, sede_name) tuple for a user instance."""
        if not patient:
            return (0, 'Sin Sede Asignada')
        if getattr(patient, 'sede_id', None):
            s = Sede.query.get(patient.sede_id)
            if s:
                return (s.id, s.name)
            return (patient.sede_id, f"Sede {patient.sede_id}")
        if getattr(patient, 'assigned_sedes', None) and patient.assigned_sedes.count() > 0:
            s = patient.assigned_sedes.first()
            return (s.id, s.name)
        return (0, 'Sin Sede Asignada')
