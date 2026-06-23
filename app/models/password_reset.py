import secrets
import string
from datetime import datetime, timedelta

from app.extensions import db


class PasswordReset(db.Model):
    __tablename__ = 'password_resets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    new_password_hash = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate_code(length=6):
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @classmethod
    def create_for_email(cls, email, user_id=None, expiry_minutes=30):
        code = cls.generate_code()
        record = cls(
            user_id=user_id,
            email=email,
            code=code,
            status='pending',
            expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
        )
        db.session.add(record)
        db.session.commit()
        return record

    def is_valid(self):
        return self.status == 'pending' and self.expires_at > datetime.utcnow()

    def mark_verified(self):
        self.status = 'verified'
        self.verified_at = datetime.utcnow()
        db.session.commit()

    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def mark_expired(self):
        self.status = 'expired'
        db.session.commit()
