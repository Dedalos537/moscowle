"""Ajustes del sistema que deben sobrevivir a reinicios y verse igual en todos los procesos.

`SystemSetting`: clave/valor (antes los canales de aviso solo se guardaban en os.environ del proceso).
`LiveVersion`: contador por «ámbito»; cada cambio de configuración lo incrementa y las pantallas abiertas lo
detectan para recargarse solas, sin tener que refrescar la página.
"""

from datetime import UTC, datetime

from app.extensions import db


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


class SystemSetting(db.Model):
    __tablename__ = 'system_setting'

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


class LiveVersion(db.Model):
    __tablename__ = 'live_version'

    scope = db.Column(db.String(80), primary_key=True)
    version = db.Column(db.Integer, default=1, nullable=False)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)
