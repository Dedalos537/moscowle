import io
import base64
from datetime import datetime, timedelta
import pyotp
import qrcode

from app.extensions import db


class MFAService:
    def generate_secret(self):
        return pyotp.random_base32()

    def get_totp_uri(self, secret, email):
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name='Centro de Terapias'
        )

    def get_qr_svg(self, secret, email):
        uri = self.get_totp_uri(secret, email)
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode()

    def verify_totp(self, secret, code):
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    def enable_mfa(self, user):
        if not user.otp_secret:
            user.otp_secret = self.generate_secret()
        user.mfa_enabled = True
        db.session.commit()

    def disable_mfa(self, user):
        user.mfa_enabled = False
        user.otp_secret = None
        db.session.commit()

    def check_lockout(self, user):
        if user.mfa_locked_until and user.mfa_locked_until > datetime.utcnow():
            remaining = int((user.mfa_locked_until - datetime.utcnow()).total_seconds() // 60)
            return {"locked": True, "minutes_remaining": remaining}
        return {"locked": False}

    def record_attempt(self, user, success=False):
        from flask import current_app
        if success:
            user.mfa_failed_attempts = 0
            user.mfa_locked_until = None
        else:
            user.mfa_failed_attempts = (user.mfa_failed_attempts or 0) + 1
            max_attempts = current_app.config.get('MFA_MAX_ATTEMPTS', 5)
            if user.mfa_failed_attempts >= max_attempts:
                lockout_minutes = current_app.config.get('MFA_LOCKOUT_MINUTES', 15)
                user.mfa_locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
        db.session.commit()
