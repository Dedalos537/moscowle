from datetime import UTC, datetime

from app.extensions import db


def _utcnow():
    """Return naive UTC now for SQLite compatibility, aware for MySQL."""
    return datetime.now(UTC).replace(tzinfo=None)


class UserStatusLog(db.Model):
    """Registro de cambios de estado (account_status) de usuarios."""

    __tablename__ = 'user_status_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    justification = db.Column(db.Text, nullable=True)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    changed_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('status_logs', lazy=True))
    changed_by = db.relationship('User', foreign_keys=[changed_by_id], lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'justification': self.justification or '',
            'changed_by_id': self.changed_by_id,
            'changed_by_username': self.changed_by.username if self.changed_by else None,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
        }

    def __repr__(self):
        return f'<UserStatusLog #{self.id}: {self.old_status} -> {self.new_status}>'
