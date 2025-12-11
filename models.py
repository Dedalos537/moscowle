from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db= SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=False, nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(1200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google', 'microsoft', None
    oauth_id = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    # Profile fields to support sessions and patient management
    avatar = db.Column(db.String(400), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    guardian_name = db.Column(db.String(150), nullable=True)
    guardian_contact = db.Column(db.String(150), nullable=True)
    therapy_goals = db.Column(db.Text, nullable=True)
    timezone = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    # Assigned therapist relationship (optional for patients)
    assigned_therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_therapist = db.relationship('User', remote_side=[id], backref=db.backref('assigned_patients', lazy=True))
    # JSON string for AI-generated game profile/config per user
    game_profile = db.Column(db.Text, nullable=True)

class SessionMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    game_name = db.Column(db.String(100), nullable=False)
    accurracy = db.Column(db.Float, nullable=False)
    avg_time = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='scheduled')  # scheduled, completed, cancelled
    location = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    # JSON string list of assigned games for this session
    games = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    therapist = db.relationship('User', foreign_keys=[therapist_id], backref=db.backref('appointments_as_therapist', lazy=True))
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('appointments_as_patient', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    link = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    parent_message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)  # For threading
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True))
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy=True)


