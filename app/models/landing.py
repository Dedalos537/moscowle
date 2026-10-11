"""Sitio público (centrojuanpabloii.com): contenido editable y contactos que llegan desde la landing.

El contenido se guarda versionado: cada publicación es una fila nueva, así el admin puede volver a una anterior.
Los contactos (leads) son las solicitudes de evaluación que llegan por el formulario, WhatsApp o llamada.
"""

from datetime import UTC, datetime

from app.extensions import db


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


class LandingContentVersion(db.Model):
    __tablename__ = 'landing_content_version'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.JSON, nullable=False)
    note = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

    author = db.relationship('User', foreign_keys=[created_by])

    def summary(self):
        return {
            'id': self.id,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'author': self.author.username if self.author else None,
        }


class LandingLead(db.Model):
    __tablename__ = 'landing_lead'

    id = db.Column(db.Integer, primary_key=True)
    # form: dejó sus datos para que lo llamen · whatsapp: abrió el chat · call: pulsó «Llamar»
    channel = db.Column(db.String(20), nullable=False, default='form', index=True)
    name = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    patient_age = db.Column(db.String(30), nullable=True)
    service = db.Column(db.String(120), nullable=True)
    preferred_time = db.Column(db.String(30), nullable=True)  # manana | tarde | cualquiera
    message = db.Column(db.Text, nullable=True)
    # new → contacted → scheduled | discarded
    status = db.Column(db.String(20), nullable=False, default='new', index=True)
    staff_note = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(200), nullable=True)  # utm / referrer, para saber de dónde llegan
    ip_hash = db.Column(db.String(64), nullable=True, index=True)
    handled_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)

    handler = db.relationship('User', foreign_keys=[handled_by])

    def to_dict(self):
        return {
            'id': self.id,
            'channel': self.channel,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'patient_age': self.patient_age,
            'service': self.service,
            'preferred_time': self.preferred_time,
            'message': self.message,
            'status': self.status,
            'staff_note': self.staff_note,
            'source': self.source,
            'handled_by': self.handler.username if self.handler else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
