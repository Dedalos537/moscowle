"""Historial del estado del servidor (una foto cada 5 minutos, se guardan 7 días)."""

from datetime import UTC, datetime

from app.extensions import db


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


class ServerSnapshot(db.Model):
    __tablename__ = 'server_snapshot'

    id = db.Column(db.Integer, primary_key=True)
    taken_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    cpu_pct = db.Column(db.Float, nullable=True)
    load1 = db.Column(db.Float, nullable=True)
    mem_pct = db.Column(db.Float, nullable=True)
    disk_pct = db.Column(db.Float, nullable=True)
    app_rss_mb = db.Column(db.Float, nullable=True)
    services_down = db.Column(db.String(255), nullable=True)  # nombres separados por coma

    def to_dict(self):
        return {
            'taken_at': self.taken_at.isoformat() + 'Z',
            'cpu_pct': self.cpu_pct,
            'load1': self.load1,
            'mem_pct': self.mem_pct,
            'disk_pct': self.disk_pct,
            'app_rss_mb': self.app_rss_mb,
            'services_down': [s for s in (self.services_down or '').split(',') if s],
        }
