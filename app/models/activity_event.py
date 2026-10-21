"""Registro liviano de acciones de escritura que no dejan rastro propio (PRP 012).

Nunca guarda el cuerpo de la petición ni contenido clínico: solo quién, qué acción, sobre qué y cuándo.
"""

from datetime import datetime

from app.extensions import db


class ActivityEvent(db.Model):
    __tablename__ = 'activity_event'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    role = db.Column(db.String(20), nullable=True)
    action = db.Column(db.String(60), nullable=False, index=True)  # contracts.updated, drive.deleted…
    entity_type = db.Column(db.String(40), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    summary = db.Column(db.String(200), nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
