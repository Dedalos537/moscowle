import secrets
import string
from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models.base import AuditMixin


class TelegramUser(db.Model, AuditMixin):
    __tablename__ = 'telegram_users'

    id = db.Column(db.Integer, primary_key=True)
    telegram_chat_id = db.Column(db.BigInteger, unique=True, nullable=False, index=True)
    telegram_user_id = db.Column(db.BigInteger, nullable=True)
    telegram_username = db.Column(db.String(255), nullable=True)
    telegram_first_name = db.Column(db.String(255), nullable=True)

    admin_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    is_linked = db.Column(db.Boolean, default=False, nullable=False)

    link_code = db.Column(db.String(8), unique=True, nullable=True, index=True)
    link_code_expires_at = db.Column(db.DateTime, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)
    last_interaction_at = db.Column(db.DateTime, nullable=True)

    pending_confirmation = db.Column(db.JSON, nullable=True)
    pending_confirmation_expires_at = db.Column(db.DateTime, nullable=True)
    awaiting_patient_name = db.Column(db.JSON, nullable=True)

    admin_user = db.relationship(
        'User',
        foreign_keys=[admin_user_id],
        primaryjoin='TelegramUser.admin_user_id == User.id',
        backref=db.backref('telegram_links', lazy='dynamic'),
    )

    def generate_link_code(self):
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        self.link_code = code
        self.link_code_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        return code

    def is_link_code_valid(self, code):
        if not self.link_code or not self.link_code_expires_at:
            return False
        now = datetime.now(UTC).replace(tzinfo=None)
        return self.link_code == code.upper() and self.link_code_expires_at > now

    def __repr__(self):
        return f'<TelegramUser {self.telegram_chat_id} linked={self.is_linked}>'
