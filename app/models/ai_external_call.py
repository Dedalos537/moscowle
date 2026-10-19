"""Registro de cada envío a un modelo externo (PRP 009): qué ruta y qué tipo de dato, nunca el contenido."""

from datetime import datetime

from app.extensions import db


class AiExternalCall(db.Model):
    __tablename__ = 'ai_external_call'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    route = db.Column(db.String(20), nullable=False)  # chat | vision | dev
    doc_type = db.Column(db.String(40), nullable=True)
    tools = db.Column(db.String(300), nullable=True)
    tokens_in = db.Column(db.Integer, default=0, nullable=False)
    tokens_out = db.Column(db.Integer, default=0, nullable=False)
    ms = db.Column(db.Integer, default=0, nullable=False)
    ok = db.Column(db.Boolean, default=True, nullable=False)
    error = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
