from app.extensions import db
from app.models.base import AuditMixin


class SessionAudit(db.Model, AuditMixin):
    __tablename__ = 'session_audit'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False, unique=True)

    planned_text = db.Column(db.Text, nullable=True)
    docx_uploaded_at = db.Column(db.DateTime, nullable=True)
    docx_uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    transcript_text = db.Column(db.Text, nullable=True)
    audio_transcribed_at = db.Column(db.DateTime, nullable=True)
    audio_duration_seconds = db.Column(db.Integer, nullable=True)

    audit_report_json = db.Column(db.Text, nullable=True)
    audit_score = db.Column(db.Float, nullable=True)
    audit_status = db.Column(db.String(30), default='pending')
    audited_at = db.Column(db.DateTime, nullable=True)

    appointment = db.relationship(
        'Appointment',
        backref=db.backref('audit', uselist=False, lazy=True, cascade='all, delete-orphan')
    )
    uploader = db.relationship('User', foreign_keys=[docx_uploaded_by])

    feedback_engagement = db.Column(db.Integer, nullable=True)
    feedback_progress = db.Column(db.Integer, nullable=True)
    feedback_notes = db.Column(db.Text, nullable=True)
    feedback_submitted_at = db.Column(db.DateTime, nullable=True)

    def get_report(self):
        import json
        try:
            return json.loads(self.audit_report_json) if self.audit_report_json else {}
        except Exception:
            return {}


class WeeklyReport(db.Model, AuditMixin):
    __tablename__ = 'weekly_report'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    report_text = db.Column(db.Text, nullable=True)
    avg_score = db.Column(db.Float, default=0.0)
    sessions_count = db.Column(db.Integer, default=0)
    objectives_achieved = db.Column(db.Integer, default=0)
    objectives_total = db.Column(db.Integer, default=0)

    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('weekly_reports', lazy=True))
    therapist = db.relationship('User', foreign_keys=[therapist_id])


class DailyReport(db.Model, AuditMixin):
    __tablename__ = 'daily_report'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    sessions_count = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)

    patient = db.relationship('User', foreign_keys=[patient_id])
    therapist = db.relationship('User', foreign_keys=[therapist_id])

    __table_args__ = (
        db.UniqueConstraint('patient_id', 'therapist_id', 'date', name='uq_daily_report'),
    )


class MonthlyReport(db.Model, AuditMixin):
    __tablename__ = 'monthly_report'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    sessions_count = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Float, default=0.0)
    objectives_achieved = db.Column(db.Integer, default=0)
    objectives_total = db.Column(db.Integer, default=0)
    report_text = db.Column(db.Text, nullable=True)

    patient = db.relationship('User', foreign_keys=[patient_id])
    therapist = db.relationship('User', foreign_keys=[therapist_id])

    __table_args__ = (
        db.UniqueConstraint('patient_id', 'therapist_id', 'month', 'year', name='uq_monthly_report'),
    )


class QuarterlyReport(db.Model, AuditMixin):
    __tablename__ = 'quarterly_report'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    quarter = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    sessions_count = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Float, default=0.0)
    objectives_achieved = db.Column(db.Integer, default=0)
    objectives_total = db.Column(db.Integer, default=0)
    report_text = db.Column(db.Text, nullable=True)

    patient = db.relationship('User', foreign_keys=[patient_id])
    therapist = db.relationship('User', foreign_keys=[therapist_id])

    __table_args__ = (
        db.UniqueConstraint('patient_id', 'therapist_id', 'quarter', 'year', name='uq_quarterly_report'),
    )
