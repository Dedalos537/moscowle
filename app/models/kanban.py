from app.extensions import db
from app.models.base import AuditMixin, SoftDeleteMixin


class KanbanTask(db.Model, AuditMixin, SoftDeleteMixin):
    __tablename__ = 'kanban_task'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    therapy_type = db.Column(db.String(50), nullable=True, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True, index=True)
    max_minutes = db.Column(db.Integer, default=0, nullable=False)
    column = db.Column(db.String(20), default='todo', nullable=False, index=True)
    position = db.Column(db.Integer, default=0, nullable=False)
    timer_start = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.Integer, default=3, nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True, index=True)
    is_expired = db.Column(db.Boolean, default=False, nullable=False)

    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], lazy='select')
    sede_item = db.relationship('Sede', foreign_keys=[sede_id], lazy='select')
    session_item = db.relationship('Appointment', foreign_keys=[session_id], lazy='select')
    attachments = db.relationship('KanbanAttachment', backref='task', lazy='select', cascade='all, delete-orphan')

    @property
    def attachment_count(self):
        return len(self.attachments) if self.attachments is not None else 0


class KanbanAttachment(db.Model, AuditMixin):
    __tablename__ = 'kanban_attachment'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('kanban_task.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(120), nullable=True)
    size = db.Column(db.Integer, default=0, nullable=False)
    data = db.Column(db.LargeBinary, nullable=True)
    data_b64 = db.Column(db.Text, nullable=True)
