from datetime import datetime
from app.extensions import db
from app.models.base import AuditMixin


class ServiceRequest(db.Model, AuditMixin):
    __tablename__ = 'service_request'

    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)
    priority = db.Column(db.String(20), default='normal')
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)

    requester = db.relationship('User', foreign_keys=[requester_id], backref='submitted_requests')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'requester_id': self.requester_id,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'approved_by_id': self.approved_by_id,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
        }

    def approve(self, admin_id, notes=None):
        self.status = 'approved'
        self.approved_by_id = admin_id
        self.admin_notes = notes
        self.resolved_at = datetime.utcnow()

    def reject(self, admin_id, notes=None):
        self.status = 'rejected'
        self.approved_by_id = admin_id
        self.admin_notes = notes
        self.resolved_at = datetime.utcnow()
