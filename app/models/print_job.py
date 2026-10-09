"""Trabajos de impresión enviados desde el drive (inmediatos o programados)."""

from datetime import UTC, datetime

from app.extensions import db


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


class PrintJob(db.Model):
    __tablename__ = 'print_job'

    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(1024), nullable=False)  # relativa a la raíz del drive
    file_name = db.Column(db.String(255), nullable=False)
    printer = db.Column(db.String(160), nullable=False)
    copies = db.Column(db.Integer, default=1, nullable=False)
    duplex = db.Column(db.Boolean, default=False, nullable=False)
    color = db.Column(db.Boolean, default=True, nullable=False)
    page_range = db.Column(db.String(60), nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=True, index=True)  # UTC; None = enseguida
    # scheduled -> sent | failed | cancelled
    status = db.Column(db.String(20), default='scheduled', nullable=False, index=True)
    cups_job = db.Column(db.String(80), nullable=True)
    error = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        iso = lambda d: d.isoformat() + 'Z' if d else None  # noqa: E731
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'printer': self.printer,
            'copies': self.copies,
            'duplex': self.duplex,
            'color': self.color,
            'page_range': self.page_range,
            'scheduled_at': iso(self.scheduled_at),
            'status': self.status,
            'cups_job': self.cups_job,
            'error': self.error,
            'created_at': iso(self.created_at),
            'sent_at': iso(self.sent_at),
        }
