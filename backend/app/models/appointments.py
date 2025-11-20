from ..extensions import db
from datetime import datetime

class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    therapy_id = db.Column(db.Integer, db.ForeignKey('therapies.id'), nullable=False)
    therapist_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    patient = db.relationship('Patient', backref=db.backref('appointments', lazy=True))
    therapy = db.relationship('Therapy', backref=db.backref('appointments', lazy=True))
    therapist = db.relationship('User', backref=db.backref('appointments', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'therapy_id': self.therapy_id,
            'therapist_id': self.therapist_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
        }
