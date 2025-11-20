from ..extensions import db
from datetime import datetime

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.Date, nullable=True)
    medical_record = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys example if patients belong to a user/therapist
    # owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}" 

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'dob': self.dob.isoformat() if self.dob else None,
            'medical_record': self.medical_record,
        }
