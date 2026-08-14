"""Sesiones JWT persistentes en la DB.

Cada sesión guarda los jti (identificadores) de los tokens access y refresh
emitidos en un login. Un jti activo = la sesión existe, no fue revocada y no
expiro. El blocklist loader de Flask-JWT-Extended consulta esta tabla para
rechazar tokens revocados y permitir revocar todas las sesiones desde logout.
"""

from datetime import datetime, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models.base import AuditMixin


class UserSession(db.Model, AuditMixin):
    __tablename__ = 'user_session'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    access_jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    refresh_jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    device_info = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='user_sessions')

    @classmethod
    def create(cls, user_id, access_jti, refresh_jti, ttl_seconds, device_info=None, ip_address=None):
        record = cls(
            user_id=user_id,
            access_jti=access_jti,
            refresh_jti=refresh_jti,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        )
        db.session.add(record)
        return record

    def is_valid(self):
        return self.revoked_at is None and self.expires_at > datetime.utcnow()

    def revoke(self):
        self.revoked_at = datetime.utcnow()

    @classmethod
    def is_jti_valid(cls, jti):
        if not jti:
            return False
        record = cls.query.filter(or_(cls.access_jti == jti, cls.refresh_jti == jti)).first()
        if record is None:
            # Fail-open: tokens sin sesion rastreada (internos, MFA, tools)
            # no se bloquean. Solo se bloquean sesiones explicitamente revocadas
            # o expiradas.
            return True
        return record.is_valid()

    @classmethod
    def find_by_refresh_jti(cls, refresh_jti):
        return cls.query.filter_by(refresh_jti=refresh_jti).first()

    @classmethod
    def revoke_all_for_user(cls, user_id):
        cls.query.filter_by(user_id=user_id, revoked_at=None).update({'revoked_at': datetime.utcnow()})
        db.session.commit()

    @classmethod
    def list_active_for_user(cls, user_id):
        return (
            cls.query.filter(
                cls.user_id == user_id,
                cls.revoked_at.is_(None),
                cls.expires_at > datetime.utcnow(),
            )
            .order_by(cls.id.desc())
            .all()
        )
