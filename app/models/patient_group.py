import json

from app.extensions import db
from app.models.base import AuditMixin

patient_group_member = db.Table(
    'patient_group_member',
    db.Column('group_id', db.Integer, db.ForeignKey('patient_group.id'), primary_key=True),
    db.Column('patient_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
)


class PatientGroup(db.Model, AuditMixin):
    __tablename__ = 'patient_group'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)
    start_time = db.Column(db.String(5), nullable=True)
    end_time = db.Column(db.String(5), nullable=True)
    work_days = db.Column(db.String(20), nullable=True, default='0,1,2,3,4')
    session_dates = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    sede = db.relationship('Sede', backref='patient_groups', lazy=True)
    therapist = db.relationship('User', foreign_keys=[therapist_id], backref='patient_groups_assigned', lazy=True)
    members = db.relationship('User', secondary=patient_group_member, backref='patient_groups', lazy=True)

    def to_dict(self):
        try:
            session_dates = json.loads(self.session_dates) if self.session_dates else []
        except (ValueError, TypeError):
            session_dates = [d for d in self.session_dates.split(',') if d] if self.session_dates else []
        return {
            'id': self.id,
            'name': self.name,
            'therapist_id': self.therapist_id,
            'therapist_name': self.therapist.username if self.therapist else None,
            'sede_id': self.sede_id,
            'sede_name': self.sede.name if self.sede else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'work_days': self.work_days,
            'session_dates': session_dates,
            'notes': self.notes,
            'is_active': self.is_active,
            'member_ids': [m.id for m in self.members],
            'member_count': len(self.members),
        }
