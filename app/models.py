from flask_login import UserMixin
from datetime import datetime
from app.extensions import db

# Association table for Patient <-> Therapist (Many-to-Many)
patient_therapist = db.Table('patient_therapist',
    db.Column('patient_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('therapist_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Association table for Therapist <-> Sede (Many-to-Many)
therapist_sede = db.Table('therapist_sede',
    db.Column('therapist_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('sede_id', db.Integer, db.ForeignKey('sede.id'), primary_key=True)
)

class Sede(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    
    # NEW: Many-to-Many Relationship for multiple therapists (Max 3)
    therapists = db.relationship(
        'User',
        secondary='patient_therapist',
        primaryjoin="User.id==patient_therapist.c.patient_id",
        secondaryjoin="User.id==patient_therapist.c.therapist_id",
        backref=db.backref('associated_patients', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # JSON string for AI-generated game profile/config per user
    game_profile = db.Column(db.Text, nullable=True)
    
    # Security/Admin fields
    admin_password_changed_count = db.Column(db.Integer, default=0)

    # Payment System Fields
    payment_plan = db.Column(db.String(50), default='monthly') # monthly, quincenal, weekly
    payment_due_date = db.Column(db.Date, nullable=True)
    payment_amount = db.Column(db.Float, default=0.0)
    
    # NEW: Specific payment day (E.g. 5 for every 5th of the month)
    payment_day = db.Column(db.Integer, nullable=True)
    
    # New Fields for Session Management
    sessions_total = db.Column(db.Integer, default=0) # Total allocated sessions for current payment cycle (4, 8, 12)
    sessions_attended = db.Column(db.Integer, default=0) # Sessions consumed
    sessions_remaining = db.Column(db.Integer, default=0) # Sessions left from last cycle to recover
    session_cost = db.Column(db.Float, default=0.0) # Calculated cost per session
    plan_type = db.Column(db.String(50), default='individual') # individual, group

    # Secondary Shift Fields
    has_second_shift = db.Column(db.Boolean, default=False)
    modality_2 = db.Column(db.Integer, default=0)
    payment_amount_2 = db.Column(db.Float, default=0.0)
    sessions_total_2 = db.Column(db.Integer, default=0)
    sessions_attended_2 = db.Column(db.Integer, default=0)
    session_cost_2 = db.Column(db.Float, default=0.0)
    plan_type_2 = db.Column(db.String(50), default='individual')
    
    # Therapist Financials
    salary_base = db.Column(db.Float, default=0.0)
    contract_hours = db.Column(db.Integer, default=0)
    

    # Therapist Schedule (for auto-calc)
    work_start_time = db.Column(db.String(5), nullable=True) # HH:MM
    work_end_time = db.Column(db.String(5), nullable=True) # HH:MM
    work_days = db.Column(db.String(20), nullable=True) # "0,1,2,3,4" (Mon-Fri)
    
    # Sede/Branch Relationship
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)
    # Use string 'Sede' if class not fully defined, or properties. 
    # Since Sede is defined before, we can use it, but to be safe and consistent with previous patterns:
    sede_item = db.relationship('Sede', foreign_keys=[sede_id], backref=db.backref('patients_assigned', lazy='dynamic'))

    # Therapist Sedes (Many-to-Many)
    assigned_sedes = db.relationship(
        'Sede',
        secondary='therapist_sede',
        backref=db.backref('therapists_assigned', lazy='dynamic'),
        lazy='dynamic'
    )

    payments = db.relationship('Payment', backref='patient', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    method = db.Column(db.String(50), nullable=False) # transfer, yape, cash, card
    reference = db.Column(db.String(100), nullable=True)
    receipt_image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='completed')
    notes = db.Column(db.Text, nullable=True)
    discount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # 'therapist_payment', 'operational', 'other'
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # New fields for payment tracking
    method = db.Column(db.String(50), nullable=True) # transfer, cash, yape_plin
    receipt_image_path = db.Column(db.String(255), nullable=True)

    therapist = db.relationship('User', backref=db.backref('expenses', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class YapeTransaction(db.Model):
    """
    Transacciones importadas desde Yape/Plin.
    Usar UPSERT pattern para evitar duplicados.
    operation_number es la clave única que garantiza idempotencia.
    """
    __tablename__ = 'yape_transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # UNIQUE constraint en operation_number para idempotencia
    operation_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Datos clave del reporte Yape
    transaction_date = db.Column(db.DateTime, nullable=False)
    sender_name = db.Column(db.String(255), nullable=True)  # Razón Social / Nombre
    amount = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text, nullable=True)  # Campo de descripción/nota
    
    # Clasificación y enlace
    category = db.Column(db.String(50), default='unclassified')  # deposit, expense, transfer, etc.
    is_expense = db.Column(db.Boolean, default=False)  # ¿Es un gasto importante?
    
    # Enlace a registro de Expense si se procesa
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=True)
    expense = db.relationship('Expense', backref='yape_transaction')
    
    # Comprobante/Foto
    receipt_image_path = db.Column(db.String(255), nullable=True)
    
    # Auditoría
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    import_batch_id = db.Column(db.String(100), nullable=True)  # Para agrupar importes
    
    def __repr__(self):
        return f'<YapeTransaction {self.operation_number} - {self.amount}>'


class Game(db.Model):
    __tablename__ = 'game'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    thumbnail = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AppointmentGame(db.Model):
    __tablename__ = 'appointment_game'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    config = db.Column(db.Text, nullable=True) # JSON for specific game config (difficulty, etc)
    status = db.Column(db.String(50), default='pending') # pending, completed
    
    appointment = db.relationship('Appointment', backref=db.backref('appointment_games', lazy=True, cascade="all, delete-orphan"))
    game = db.relationship('Game', backref=db.backref('game_appointments', lazy=True))

class SessionMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=True) # Link to Game model
    game_name = db.Column(db.String(100), nullable=False)
    accurracy = db.Column(db.Float, nullable=False)
    avg_time = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    game = db.relationship('Game', backref=db.backref('metrics', lazy=True))
    user = db.relationship('User', backref=db.backref('metrics', lazy=True, cascade="all, delete-orphan"))



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
    
    # Fields from deployed DB
    therapy_type = db.Column(db.String(120), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)

    # JSON string list of assigned games for this session
    games = db.Column(db.Text, nullable=True)
    attendance = db.Column(db.String(20), default='pending') # pending, present, absent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Status tracking for audit trail
    status_changed_at = db.Column(db.DateTime, nullable=True)
    status_changed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    therapist = db.relationship('User', foreign_keys=[therapist_id], backref=db.backref('appointments_as_therapist', lazy=True, cascade="all, delete-orphan"))
    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('appointments_as_patient', lazy=True, cascade="all, delete-orphan"))

    @property
    def games_list(self):
        """Returns list of game filenames from relationship, falling back to legacy JSON."""
        if self.appointment_games:
            return [ag.game.filename for ag in self.appointment_games]
        # Fallback
        if self.games:
            import json
            try:
                return json.loads(self.games)
            except:
                return []
        return []

class SessionImage(db.Model):
    __tablename__ = 'session_image'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    image_type = db.Column(db.String(50), default='session_photo') # session_photo, therapy_notes, patient_work
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    appointment = db.relationship('Appointment', backref=db.backref('session_images', lazy=True, cascade="all, delete-orphan"))
    uploaded_by = db.relationship('User', backref=db.backref('uploaded_images', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    link = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))


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
    
    # Multimedia support
    attachment_path = db.Column(db.String(500), nullable=True)
    attachment_type = db.Column(db.String(50), nullable=True) # image, video, audio, file
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True, cascade="all, delete-orphan"))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy=True, cascade="all, delete-orphan"))
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy=True)


class ContactMessage(db.Model):
    __tablename__ = 'contact_message'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    service_interest = db.Column(db.String(100), nullable=True)
    urgency = db.Column(db.String(50), default='medium')
    status = db.Column(db.String(50), default='unread') # unread, read, replied, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SmartAction(db.Model):
    """
    Motor de Automatización Progresiva (ERP Moscowle)
    Mantiene las tareas pendientes detectadas por el WorkflowEngine.
    """
    __tablename__ = 'smart_action'
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(50), nullable=False, index=True) # 'pagos', 'sesiones', 'usuarios', 'yape', 'sede'
    description = db.Column(db.String(255), nullable=False)
    
    # Datos JSON para ejecutar la acción (patient_id, amount, date, etc)
    suggested_payload = db.Column(db.Text, nullable=True) 
    
    # Nivel de intervención: 'manual', 'requires_confirmation', 'auto'
    automation_level = db.Column(db.String(30), default='manual')
    
    # Estado del ciclo de vida: 'pending', 'resolved', 'ignored'
    status = db.Column(db.String(20), default='pending', index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    def get_payload(self):
        import json
        try:
            return json.loads(self.suggested_payload) if self.suggested_payload else {}
        except:
            return {}

class CSPReport(db.Model):
    __tablename__ = 'csp_report'
    id = db.Column(db.Integer, primary_key=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    document_uri = db.Column(db.String(1000), nullable=True)
    violated_directive = db.Column(db.String(255), nullable=True)
    blocked_uri = db.Column(db.String(1000), nullable=True)
    original_policy = db.Column(db.Text, nullable=True)
    raw_report = db.Column(db.Text, nullable=True)  # store full JSON payload as text
    ip_address = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    user = db.relationship('User', backref=db.backref('csp_reports', lazy=True, cascade='all, delete-orphan'))


class AdminAPIToken(db.Model):
    __tablename__ = 'admin_api_token'
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def deactivate(self):
        self.is_active = False
