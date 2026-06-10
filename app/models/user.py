from flask_login import UserMixin
from datetime import datetime
from app.extensions import db
from app.models.base import AuditMixin

patient_therapist = db.Table('patient_therapist',
    db.Column('patient_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('therapist_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    extend_existing=True
)

therapist_sede = db.Table('therapist_sede',
    db.Column('therapist_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('sede_id', db.Integer, db.ForeignKey('sede.id'), primary_key=True),
    extend_existing=True
)

class Sede(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)


class User(db.Model, UserMixin, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=False, nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(1200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    oauth_provider = db.Column(db.String(50), nullable=True)
    oauth_id = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    mfa_enabled = db.Column(db.Boolean, default=False)
    otp_secret = db.Column(db.String(32), nullable=True)
    account_status = db.Column(db.String(50), default='active')
    avatar = db.Column(db.String(400), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    guardian_name = db.Column(db.String(150), nullable=True)
    guardian_contact = db.Column(db.String(150), nullable=True)
    document_number = db.Column(db.String(20), nullable=True)
    therapy_goals = db.Column(db.Text, nullable=True)
    timezone = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    assigned_therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    assigned_therapist = db.relationship(
        'User', remote_side=[id], foreign_keys=[assigned_therapist_id],
        backref=db.backref('assigned_patients', lazy=True),
    )

    therapists = db.relationship(
        'User',
        secondary='patient_therapist',
        primaryjoin="User.id==patient_therapist.c.patient_id",
        secondaryjoin="User.id==patient_therapist.c.therapist_id",
        backref=db.backref('associated_patients', lazy='dynamic'),
        lazy='dynamic'
    )

    game_profile = db.Column(db.Text, nullable=True)

    admin_password_changed_count = db.Column(db.Integer, default=0)

    payment_plan = db.Column(db.String(50), default='monthly')
    payment_due_date = db.Column(db.Date, nullable=True)
    payment_amount = db.Column(db.Float, default=0.0)

    payment_day = db.Column(db.Integer, nullable=True)

    sessions_total = db.Column(db.Integer, default=0)
    sessions_attended = db.Column(db.Integer, default=0)
    sessions_remaining = db.Column(db.Integer, default=0)
    session_cost = db.Column(db.Float, default=0.0)
    plan_type = db.Column(db.String(50), default='individual')

    has_second_shift = db.Column(db.Boolean, default=False)
    modality_2 = db.Column(db.Integer, default=0)
    payment_amount_2 = db.Column(db.Float, default=0.0)
    sessions_total_2 = db.Column(db.Integer, default=0)
    sessions_attended_2 = db.Column(db.Integer, default=0)
    session_cost_2 = db.Column(db.Float, default=0.0)
    plan_type_2 = db.Column(db.String(50), default='individual')

    salary_base = db.Column(db.Float, default=0.0)
    contract_hours = db.Column(db.Integer, default=0)

    work_start_time = db.Column(db.String(5), nullable=True)
    work_end_time = db.Column(db.String(5), nullable=True)
    work_days = db.Column(db.String(20), nullable=True)

    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True, index=True)
    sede_item = db.relationship('Sede', foreign_keys=[sede_id], backref=db.backref('patients_assigned', lazy='dynamic'))

    assigned_sedes = db.relationship(
        'Sede',
        secondary='therapist_sede',
        backref=db.backref('therapists_assigned', lazy='dynamic'),
        lazy='dynamic'
    )

    payments = db.relationship('Payment', foreign_keys='Payment.patient_id', backref='patient', lazy=True)
