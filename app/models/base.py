from datetime import UTC, datetime

from sqlalchemy.orm import declared_attr

from app.extensions import db


class AuditMixin:
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(UTC), nullable=True)

    @declared_attr
    def created_by(cls):
        return db.relationship('User', foreign_keys=[cls.created_by_id], lazy='select')


class SoftDeleteMixin:
    is_active = db.Column(db.Boolean, default=True, nullable=False)
