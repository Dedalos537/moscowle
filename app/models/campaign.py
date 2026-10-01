"""Campañas de difusion y sus destinatarios.

La campaign es la intencion ("avisar renewal a los que se les vence este
mes") y el campaign_send es un destinatario con su propio estado. Separarlos
permite reanudar una campaña a medio mandar sin duplicar a los que ya
recibieron, que es justo como se termina floodeando a un paciente.
"""
from app import db
from datetime import datetime


class Campaign(db.Model):
    __tablename__ = 'campaign'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    channel = db.Column(db.String(20), nullable=False)  # sms | whatsapp
    template_key = db.Column(db.String(60), nullable=True)
    message = db.Column(db.Text, nullable=False)

    # Como se eligieron los destinatarios. Se guarda la descripcion para que
    # dentro de tres meses se entienda a quien se le mando esto y por que.
    segment = db.Column(db.String(60), default='manual')
    # draft -> aun editable | scheduled -> esperando | running -> mandando
    # paused -> detenida a mitad | sent -> terminada | cancelled
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)

    total_recipients = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    skipped_count = db.Column(db.Integer, default=0)

    scheduled_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sends = db.relationship(
        'CampaignSend', backref='campaign', lazy='select', cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'channel': self.channel,
            'template_key': self.template_key,
            'message': self.message,
            'segment': self.segment,
            'status': self.status,
            'total_recipients': self.total_recipients,
            'sent_count': self.sent_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }


class CampaignSend(db.Model):
    __tablename__ = 'campaign_send'
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'patient_id', name='uq_campaign_patient'),
        db.Index('ix_campsend_status', 'status'),
    )

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    phone = db.Column(db.String(50), nullable=True)
    # pending -> falta mandarle | sent | failed | skipped
    # skipped es distinto de failed: se salta porque el paciente esta
    # desactivado o no tiene numero, no porque el proveedor fallara.
    status = db.Column(db.String(20), nullable=False, default='pending')
    skip_reason = db.Column(db.String(255), nullable=True)
    failed_reason = db.Column(db.String(255), nullable=True)

    message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'patient_id': self.patient_id,
            'phone': self.phone,
            'status': self.status,
            'skip_reason': self.skip_reason,
            'failed_reason': self.failed_reason,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
        }