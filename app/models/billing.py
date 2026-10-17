"""Libro de cobranza: a qué cuota se aplicó cada pago, lotes de importación y nómina de terapeutas.

- `PaymentAllocation`: una fila por cada (pago, cuota) con el monto aplicado. `Installment.paid_amount` es la suma
  de sus asignaciones (se mantiene como caché porque todos los indicadores la leen). Lo que un pago no alcanzó a
  aplicar queda como saldo a favor del paciente y cubre sola la próxima cuota.
- `BillingImport`: cada importación desde Excel (quién, cuándo, huella del archivo y resumen). Las asignaciones y
  los pagos creados por una importación guardan su `import_id`, así todo cambio se puede rastrear y revisar.
- `PayrollPeriod`: lo que corresponde pagar a un terapeuta por un mes (horas × tarifa), lo pagado contra ese mes
  y su vencimiento. Los pagos (`Expense` de categoría `therapist_payment`) apuntan al periodo, no a su fecha.
"""

from datetime import UTC, datetime

from app.extensions import db


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


class PaymentAllocation(db.Model):
    __tablename__ = 'payment_allocation'

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False, index=True)
    installment_id = db.Column(db.Integer, db.ForeignKey('installment.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(30), nullable=False, default='register')  # register | installment | import | credit
    import_id = db.Column(db.Integer, db.ForeignKey('billing_import.id'), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)


class BillingImport(db.Model):
    __tablename__ = 'billing_import'

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_sha256 = db.Column(db.String(64), nullable=False, index=True)
    summary = db.Column(db.Text, nullable=True)  # JSON con lo creado y aplicado
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)


class PayrollPeriod(db.Model):
    __tablename__ = 'payroll_period'
    __table_args__ = (db.UniqueConstraint('therapist_id', 'period', name='uq_payroll_therapist_period'),)

    id = db.Column(db.Integer, primary_key=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    period = db.Column(db.String(7), nullable=False, index=True)  # AAAA-MM
    hours = db.Column(db.Float, default=0.0, nullable=False)
    sessions = db.Column(db.Integer, default=0, nullable=False)
    sessions_without_duration = db.Column(db.Integer, default=0, nullable=False)
    rate = db.Column(db.Float, default=0.0, nullable=False)
    amount_due = db.Column(db.Float, default=0.0, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    closed_at = db.Column(db.DateTime, nullable=True)  # cerrado = monto congelado
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)
