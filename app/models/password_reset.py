import secrets
import string
from datetime import datetime, timedelta

from app.extensions import db


class PasswordReset(db.Model):
    __tablename__ = 'password_resets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=True)
    new_password_hash = db.Column(db.String(255), nullable=True)
    temp_password_plain = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(30), default='awaiting_approval', index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    admin_decision = db.Column(db.String(20), nullable=True)
    decision_at = db.Column(db.DateTime, nullable=True)
    requester_ip = db.Column(db.String(64), nullable=True)
    requester_user_agent = db.Column(db.String(255), nullable=True)

    @staticmethod
    def generate_code(length=6):
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def generate_temp_password(length=12):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @classmethod
    def create_for_email(cls, email, user_id=None, expiry_minutes=1440, requester_ip=None, user_agent=None):
        temp_password = cls.generate_temp_password()
        record = cls(
            user_id=user_id,
            email=email,
            code=cls.generate_code(),
            temp_password_plain=temp_password,
            status='awaiting_approval',
            expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
            requester_ip=requester_ip,
            requester_user_agent=(user_agent or '')[:255],
        )
        db.session.add(record)
        db.session.commit()
        return record

    def is_valid(self):
        return self.status == 'pending' and self.expires_at > datetime.utcnow()

    def is_awaiting_approval(self):
        return self.status == 'awaiting_approval' and self.expires_at > datetime.utcnow()

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

    def approve(self, admin_id):
        self.status = 'approved'
        self.admin_id = admin_id
        self.admin_decision = 'approved'
        self.decision_at = datetime.utcnow()
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def reject(self, admin_id):
        self.status = 'rejected'
        self.admin_id = admin_id
        self.admin_decision = 'rejected'
        self.decision_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self, include_temp_password=False):
        d = {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'admin_id': self.admin_id,
            'admin_decision': self.admin_decision,
            'decision_at': self.decision_at.isoformat() if self.decision_at else None,
            'requester_ip': self.requester_ip,
        }
        if include_temp_password:
            d['temp_password'] = self.temp_password_plain
        return d
