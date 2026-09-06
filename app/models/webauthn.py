from datetime import datetime

from app.extensions import db


class WebAuthnCredential(db.Model):
    __tablename__ = 'webauthn_credential'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    credential_id = db.Column(db.String(600), unique=True, nullable=False, index=True)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, nullable=False, default=0)
    transports = db.Column(db.Text, nullable=True)
    device_name = db.Column(db.String(120), nullable=True)
    aaguid = db.Column(db.String(64), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)


class WebAuthnChallenge(db.Model):
    __tablename__ = 'webauthn_challenge'

    id = db.Column(db.Integer, primary_key=True)
    challenge = db.Column(db.String(200), unique=True, nullable=False)
    user_handle = db.Column(db.String(64), nullable=False)
    operation = db.Column(db.String(16), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
