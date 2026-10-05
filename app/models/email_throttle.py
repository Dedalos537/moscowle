"""Limite de frecuencia de correos, persistente (sobrevive a reinicios y a varios
workers). Una fila por clave: 'newmsg:<destino>:<remitente>', 'sla:<id>'..."""

from datetime import datetime, timedelta

from app.extensions import db


class EmailThrottle(db.Model):
    __tablename__ = 'email_throttle'

    key = db.Column(db.String(190), primary_key=True)
    last_sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @classmethod
    def allow(cls, key, cooldown_minutes):
        """True (y registra el envio) si pasaron ``cooldown_minutes`` desde el ultimo
        envio con esa clave; False si todavia esta en enfriamiento."""
        now = datetime.utcnow()
        row = db.session.get(cls, key)
        if row is not None and now - row.last_sent_at < timedelta(minutes=cooldown_minutes):
            return False
        if row is None:
            db.session.add(cls(key=key, last_sent_at=now))
        else:
            row.last_sent_at = now
        db.session.commit()
        return True
