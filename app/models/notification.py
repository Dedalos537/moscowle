from datetime import datetime

from app.extensions import db
from app.models.base import AuditMixin


class Notification(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=True, default='info')
    category = db.Column(db.String(50), nullable=False, default='system')
    priority = db.Column(db.String(20), nullable=False, default='normal')
    icon = db.Column(db.String(50), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)

    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('notifications', cascade='all, delete-orphan'),
    )


class UserNotificationPreference(db.Model, AuditMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    debt_enabled = db.Column(db.Boolean, default=True)
    activity_enabled = db.Column(db.Boolean, default=True)
    system_enabled = db.Column(db.Boolean, default=True)
    alert_enabled = db.Column(db.Boolean, default=True)
    payment_enabled = db.Column(db.Boolean, default=True)
    sound_enabled = db.Column(db.Boolean, default=True)
    browser_notifications = db.Column(db.Boolean, default=False)

    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('notification_preferences', uselist=False, cascade='all, delete-orphan'),
    )
