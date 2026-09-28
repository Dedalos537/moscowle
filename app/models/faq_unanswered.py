from datetime import UTC, datetime

from app.extensions import db


class FaqUnanswered(db.Model):
    """Contador persistente de preguntas que el asistente no pudo responder.

    Antes vivia en un diccionario en memoria (`_UnansweredTracker._log`), lo
    que hacia que los contadores se perdieran en cada reinicio y que no se
    compartieran entre los workers de gunicorn: una pregunta solo contada en
    un worker podia no alcanzar jamas el umbral.
    """

    __tablename__ = 'faq_unanswered'

    id = db.Column(db.Integer, primary_key=True)
    question_key = db.Column(db.String(160), nullable=False, unique=True, index=True)
    question = db.Column(db.Text, nullable=False)
    count = db.Column(db.Integer, default=1, nullable=False)
    first_seen_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    last_seen_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'count': self.count,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
        }
