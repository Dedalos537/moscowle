"""Solicitudes de terapeutas que la coordinación aprueba: crear sesiones, pacientes o grupos.

Igual que el cambio de contraseña: el terapeuta llena el mismo formulario, la coordinación revisa y, al aprobar, se
ejecuta la acción real (con las mismas validaciones que el alta directa). Se guarda el resultado o el motivo.
"""

from datetime import UTC, datetime

from app.extensions import db


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


class ActionRequest(db.Model):
    __tablename__ = 'action_request'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False, index=True)  # sessions | patient | group
    payload = db.Column(db.JSON, nullable=False)
    summary = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # pending | approved | rejected
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    review_note = db.Column(db.Text, nullable=True)
    result = db.Column(db.JSON, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    requester = db.relationship('User', foreign_keys=[requester_id])
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])

    def to_dict(self):
        return {
            'id': self.id,
            'kind': self.kind,
            'payload': self.payload,
            'summary': self.summary,
            'status': self.status,
            'requester_id': self.requester_id,
            'requester_name': (self.requester.username or self.requester.email) if self.requester else None,
            'reviewer_name': (self.reviewer.username or self.reviewer.email) if self.reviewer else None,
            'review_note': self.review_note,
            'result': self.result,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() + 'Z' if self.resolved_at else None,
        }
