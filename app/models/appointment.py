from datetime import datetime
from app.extensions import db
from app.models.base import AuditMixin


class SessionMetrics(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True, index=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=True, index=True)
    game_name = db.Column(db.String(100), nullable=False)
    accurracy = db.Column(db.Float, nullable=False)
    avg_time = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    game = db.relationship('Game', backref=db.backref('metrics', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('metrics', lazy=True, cascade="all, delete-orphan"))


class AppointmentGame(db.Model, AuditMixin):
    __tablename__ = 'appointment_game'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False, index=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False, index=True)
    config = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')

    appointment = db.relationship('Appointment', backref=db.backref('appointment_games', lazy=True, cascade="all, delete-orphan"))
    game = db.relationship('Game', backref=db.backref('game_appointments', lazy=True))


class SessionImage(db.Model, AuditMixin):
    __tablename__ = 'session_image'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False, index=True)
    image_path = db.Column(db.String(500), nullable=False)
    image_type = db.Column(db.String(50), default='session_photo')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)

    appointment = db.relationship('Appointment', backref=db.backref('session_images', lazy=True, cascade="all, delete-orphan"))
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id], backref=db.backref('uploaded_images', lazy=True))


class Appointment(db.Model, AuditMixin):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='scheduled')
    location = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    therapy_type = db.Column(db.String(120), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)

    games = db.Column(db.Text, nullable=True)
    attendance = db.Column(db.String(20), default='pending')
    status_changed_at = db.Column(db.DateTime, nullable=True)
    status_changed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    therapist = db.relationship('User', foreign_keys=[therapist_id], backref=db.backref('appointments_as_therapist', lazy=True, cascade="all, delete-orphan"))
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('appointments_as_patient', lazy=True, cascade="all, delete-orphan"))

    @property
    def games_list(self):
        if self.appointment_games:
            return [ag.game.filename for ag in self.appointment_games]
        if self.games:
            import json
            try:
                return json.loads(self.games)
            except:
                return []
        return []
