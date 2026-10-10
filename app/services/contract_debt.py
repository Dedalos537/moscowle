"""Deuda por cuotas de contrato, con una sola regla para el panel, el reporte de deudores y el resumen diario.

Regla (decisión del centro, oct-2026): si el paciente tiene un contrato activo, su deuda sale de las cuotas
(vencidas = fecha de vencimiento pasada y saldo pendiente). Si no tiene contrato activo, se sigue usando el plan
del paciente (payment_amount / payment_due_date). Así nadie se cuenta dos veces.

Antes la mora solo miraba el plan: al crear un contrato se copiaba el monto pero no la fecha de vencimiento, así
que un paciente con cuotas vencidas y sin pagos registrados no aparecía como moroso.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models.contract import Contract, Installment

OPEN = ('pending', 'partial')


@dataclass
class PatientContractDebt:
    overdue_amount: float = 0.0
    overdue_count: int = 0
    oldest_due: date | None = None
    next_due: date | None = None
    next_amount: float = 0.0
    installments: list = field(default_factory=list)

    @property
    def is_overdue(self):
        return self.overdue_amount > 0.005


def _remaining(inst):
    return max(0.0, float(inst.amount or 0) - float(inst.paid_amount or 0))


def contract_debt(today=None, patient_ids=None):
    """{patient_id: PatientContractDebt} para todos los pacientes con un contrato activo."""
    today = today or date.today()
    contracts = Contract.query.filter(Contract.status == 'active', Contract.is_active.isnot(False))
    if patient_ids is not None:
        ids = list(patient_ids)
        if not ids:
            return {}
        contracts = contracts.filter(Contract.patient_id.in_(ids))
    contract_patient = dict(contracts.with_entities(Contract.id, Contract.patient_id).all())
    result = {pid: PatientContractDebt() for pid in set(contract_patient.values())}
    if not contract_patient:
        return result

    rows = (
        Installment.query.filter(
            Installment.contract_id.in_(list(contract_patient)),
            Installment.status.in_(OPEN),
            Installment.is_active.isnot(False),
        )
        .order_by(Installment.due_date)
        .all()
    )
    for inst in rows:
        debt = result[contract_patient[inst.contract_id]]
        left = _remaining(inst)
        if left <= 0.005:
            continue
        if inst.due_date < today:
            debt.overdue_amount += left
            debt.overdue_count += 1
            debt.oldest_due = debt.oldest_due or inst.due_date
            debt.installments.append(inst)
        elif debt.next_due is None:
            debt.next_due = inst.due_date
            debt.next_amount = left
    for debt in result.values():
        debt.overdue_amount = round(debt.overdue_amount, 2)
        debt.next_amount = round(debt.next_amount, 2)
    return result


def due_within(debt, today, days=7):
    return debt.next_due is not None and today <= debt.next_due <= today + timedelta(days=days)
