from app.extensions import db
from app.models.base import AuditMixin


class Contract(db.Model, AuditMixin):
    __tablename__ = 'contract'

    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    installment_count = db.Column(db.Integer, default=4)
    installment_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active', index=True)
    notes = db.Column(db.Text, nullable=True)

    billing_type = db.Column(db.String(20), default='Mensual')
    currency = db.Column(db.String(5), default='PEN')
    bonus_months = db.Column(db.Integer, default=0)
    sign_date = db.Column(db.Date, nullable=True)
    service_start_date = db.Column(db.Date, nullable=True)
    billing_rule = db.Column(db.String(20), default='standard')
    implementation_cost = db.Column(db.Float, default=0.0)

    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.String(200), nullable=True)
    cancellation_comment = db.Column(db.Text, nullable=True)
    refund_status = db.Column(db.String(20), nullable=True)
    total_refunded = db.Column(db.Float, default=0.0)

    patient = db.relationship('User', foreign_keys=[patient_id], backref=db.backref('contracts', lazy=True))

    installments = db.relationship(
        'Installment', backref='contract', lazy=True, cascade='all, delete-orphan', order_by='Installment.number'
    )


class Installment(db.Model, AuditMixin):
    __tablename__ = 'installment'

    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False, index=True)
    number = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    paid_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)
    reminder_sent = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)

    real_amount = db.Column(db.Float, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    payment_currency = db.Column(db.String(5), nullable=True)
    payment_notes = db.Column(db.Text, nullable=True)
    is_free_month = db.Column(db.Boolean, default=False)
    refunded_amount = db.Column(db.Float, default=0.0)
    refunded_at = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.String(200), nullable=True)
    is_implementation = db.Column(db.Boolean, default=False)
