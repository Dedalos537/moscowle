from datetime import datetime, timedelta
import secrets
import hashlib
from app.extensions import db
from app.models.base import AuditMixin


class RefreshToken(db.Model, AuditMixin):
    __tablename__ = 'refresh_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    device_info = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='refresh_tokens')

    @classmethod
    def create(cls, user_id, ttl_seconds, device_info=None, ip_address=None):
        token = secrets.token_urlsafe(48)
        token_hash = cls._hash(token)
        record = cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
            device_info=device_info,
            ip_address=ip_address,
        )
        db.session.add(record)
        return token, record

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def is_valid(self):
        return (
            self.revoked_at is None
            and self.expires_at > datetime.utcnow()
        )

    def revoke(self):
        self.revoked_at = datetime.utcnow()

    @classmethod
    def find_valid(cls, token_raw, user_id=None):
        token_hash = cls._hash(token_raw)
        q = cls.query.filter_by(token_hash=token_hash, revoked_at=None)
        if user_id:
            q = q.filter_by(user_id=user_id)
        record = q.first()
        if record and record.expires_at > datetime.utcnow():
            return record
        if record:
            record.revoke()
            db.session.commit()
        return None

    @classmethod
    def revoke_all_for_user(cls, user_id):
        cls.query.filter_by(user_id=user_id, revoked_at=None).update(
            {"revoked_at": datetime.utcnow()}
        )
        db.session.commit()
