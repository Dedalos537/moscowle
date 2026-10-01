"""Registro de todo mensaje que sale del centro.

Sin esto no hay forma de responder "a quien le escribimos, que le dijimos y
si le llego". Tampoco de detectar que una campaña se mando dos veces.

Guarda una fila por envio, exitos o no. Los fallos se guardan igual: un envio
que se registro como fallido es informacion, no basura.
"""
from app import db
from datetime import datetime


class MessageLog(db.Model):
    __tablename__ = 'message_log'
    __table_args__ = (
        db.Index('ix_msglog_patient_channel', 'patient_id', 'channel'),
        db.Index('ix_msglog_created_at', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    # A quien se le mando. NULL cuando todavia no se pudo resolver
    # (por ejemplo: paciente sin telefono), que es informacion distinta
    # a 'no se pudo enviar'.
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # Numero usado de verdad, por si el telefono del paciente cambia luego:
    # el historico tiene que seguir mostrando a quien se le escribio ese dia.
    phone = db.Column(db.String(50), nullable=True)
    channel = db.Column(db.String(20), nullable=False)  # sms | whatsapp

    message = db.Column(db.Text, nullable=False)
    template_key = db.Column(db.String(60), nullable=True)
    campaign_id = db.Column(db.Integer, nullable=True)

    # queued -> el puente lo tiene pendiente
    # sent    -> el proveedor lo recibio
    # failed  -> no salio, y failed_reason dice por que
    status = db.Column(db.String(20), nullable=False, default='sent', index=True)
    failed_reason = db.Column(db.String(255), nullable=True)
    # Id que devuelve el proveedor, para pedirle receipts despues.
    provider_message_id = db.Column(db.String(120), nullable=True)

    # Quien lo disparo: un admin desde la pantalla, o el sistema por
    # automatismo (recordatorio de sesion, job de cobranza).
    sent_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    trigger = db.Column(db.String(30), default='manual')  # manual | automated
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'phone': self.phone,
            'channel': self.channel,
            'message': self.message,
            'template_key': self.template_key,
            'campaign_id': self.campaign_id,
            'status': self.status,
            'failed_reason': self.failed_reason,
            'trigger': self.trigger,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }