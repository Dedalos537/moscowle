"""Plantillas de mensaje persistidas.

Antes vivian en os.environ, que se pierde con cada reinicio: la pantalla de
configuracion decia "Sin configurar" aunque el admin la hubiera guardado.

Una plantilla guarda el texto con marcadores {nombre}, {monto}, etc. El render
lo hace MessagingService con un formateo que no revienta si falta un dato.
"""

from datetime import datetime

from app import db


class MessageTemplate(db.Model):
    __tablename__ = 'message_template'

    id = db.Column(db.Integer, primary_key=True)
    # Identificador funcional ('payment_reminder_sms'), no un id numerico:
    # el codigo lo pide por nombre y asi sobrevive a los ids.
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    channel = db.Column(db.String(20), nullable=False)  # sms | whatsapp
    label = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    # Los marcadores admitidos, para que el editor pueda validarlos y la
    # pantalla sepa que campos pedir antes de guardar.
    placeholders = db.Column(db.String(255), default='')
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'channel': self.channel,
            'label': self.label,
            'body': self.body,
            'placeholders': [p for p in (self.placeholders or '').split(',') if p],
            'is_active': self.is_active,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
