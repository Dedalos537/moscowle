"""Libro de cobranza: la única puerta para registrar y aplicar pagos de pacientes (PRP 008).

Reglas:
- Un pago de cuotas (`kind='installment'`) se reparte en las cuotas abiertas más antiguas primero (FIFO); si se
  indica una cuota, empieza por esa. Cada parte queda en `PaymentAllocation` y suma a `Installment.paid_amount`.
- Lo que no alcanza a aplicarse es **saldo a favor**: cubre sola la próxima cuota que se cree (`apply_credit`).
- Un pago suelto (`kind='one_off'`) lleva categoría (evaluación, material, inscripción, otro): es ingreso, pero no
  cobranza de cuotas.
- Lo histórico registrado fuera de contratos queda `kind='unassigned'` hasta clasificarlo (importación del Excel).
- Nada se recalcula desde cero: se suma o resta lo aplicado, así las cuotas pagadas antes del libro (o los meses
  bonificados) conservan su estado.
"""

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Contract, Installment, Payment, User
from app.models.billing import PaymentAllocation

OPEN = ('pending', 'partial')
ONE_OFF_CATEGORIES = {
    'evaluacion': 'Evaluación',
    'material': 'Material',
    'inscripcion': 'Inscripción',
    'otro': 'Otro',
}
EPS = 0.005


class BillingError(ValueError):
    def __init__(self, message, code='invalid'):
        super().__init__(message)
        self.code = code


# ── consultas ────────────────────────────────────────────────────────────────


def _remaining(inst):
    return max(0.0, float(inst.amount or 0) - float(inst.paid_amount or 0))


def allocated(payment_id):
    return float(
        db.session.query(db.func.coalesce(db.func.sum(PaymentAllocation.amount), 0.0))
        .filter(PaymentAllocation.payment_id == payment_id)
        .scalar()
        or 0.0
    )


def active_contracts(patient_id):
    return (
        Contract.query.filter(
            Contract.patient_id == patient_id, Contract.status == 'active', Contract.is_active.isnot(False)
        )
        .order_by(Contract.id)
        .all()
    )


def open_installments(patient_id, contract_id=None):
    q = (
        Installment.query.join(Contract, Contract.id == Installment.contract_id)
        .filter(
            Contract.patient_id == patient_id,
            Contract.status == 'active',
            Contract.is_active.isnot(False),
            Installment.status.in_(OPEN),
            Installment.is_active.isnot(False),
        )
        .order_by(Installment.due_date, Installment.number, Installment.id)
    )
    if contract_id:
        q = q.filter(Installment.contract_id == contract_id)
    return [i for i in q.all() if _remaining(i) > EPS]


def credit(patient_id):
    """Saldo a favor: lo pagado en pagos de cuotas que aún no se aplicó a ninguna cuota."""
    return round(sum(left for _, left in _unapplied_payments(patient_id)), 2)


def _unapplied_payments(patient_id):
    rows = (
        db.session.query(Payment, db.func.coalesce(db.func.sum(PaymentAllocation.amount), 0.0))
        .outerjoin(PaymentAllocation, PaymentAllocation.payment_id == Payment.id)
        .filter(
            Payment.patient_id == patient_id,
            Payment.kind == 'installment',
            Payment.is_active.isnot(False),
            db.or_(Payment.status.is_(None), Payment.status.in_(('completed', 'paid'))),
        )
        .group_by(Payment.id)
        .order_by(Payment.date, Payment.id)
        .all()
    )
    return [
        (p, float(p.amount or 0) - float(done or 0))
        for p, done in rows
        if float(p.amount or 0) - float(done or 0) > EPS
    ]


# ── aplicar ──────────────────────────────────────────────────────────────────


def _apply(payment, installments, amount, source, import_id=None, user_id=None):
    made = []
    for inst in installments:
        if amount <= EPS:
            break
        take = round(min(_remaining(inst), amount), 2)
        if take <= EPS:
            continue
        made.append(
            PaymentAllocation(
                payment_id=payment.id,
                installment_id=inst.id,
                amount=take,
                source=source,
                import_id=import_id,
                created_by_id=user_id,
            )
        )
        inst.paid_amount = round(float(inst.paid_amount or 0) + take, 2)
        inst.status = 'paid' if _remaining(inst) <= EPS else 'partial'
        inst.paid_date = payment.date
        inst.payment_id = payment.id
        inst.payment_method = payment.method
        inst.real_amount = inst.paid_amount
        amount = round(amount - take, 2)
    for a in made:
        db.session.add(a)
    if made and not payment.installment_id:
        payment.installment_id = made[0].installment_id  # compatibilidad con pantallas que leen el enlace directo
    return made


def _targets(patient_id, installment_id=None, contract_id=None):
    rows = open_installments(patient_id, contract_id)
    if installment_id:
        first = [i for i in rows if i.id == installment_id]
        if not first:
            raise BillingError('Esa cuota no existe, no es de este paciente o ya está pagada.', 'installment')
        rows = first + [i for i in rows if i.id != installment_id]
    return rows


def apply_patient_payment(
    patient_id,
    amount,
    method,
    *,
    date_=None,
    reference=None,
    receipt_path=None,
    discount=0.0,
    notes=None,
    kind='installment',
    category=None,
    installment_id=None,
    contract_id=None,
    source='register',
    import_id=None,
    user_id=None,
    commit=True,
):
    """Registra un pago y, si es de cuotas, lo aplica. Devuelve (pago, asignaciones, saldo a favor que quedó)."""
    patient = db.session.get(User, int(patient_id)) if patient_id else None
    if not patient or patient.role != 'jugador':
        raise BillingError('Elige un paciente válido.', 'patient')
    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError) as exc:
        raise BillingError('El monto debe ser un número.', 'amount') from exc
    if amount <= 0:
        raise BillingError('El monto debe ser mayor que cero.', 'amount')
    if not (method or '').strip():
        raise BillingError('Elige el método de pago.', 'method')
    if kind == 'one_off':
        if category not in ONE_OFF_CATEGORIES:
            raise BillingError('Elige de qué es el pago suelto (evaluación, material, inscripción u otro).', 'category')
    elif kind == 'installment':
        if not active_contracts(patient.id):
            raise BillingError(
                'Este paciente no tiene contrato: créale un plan de pago o regístralo como pago suelto.', 'no_contract'
            )
    else:
        raise BillingError('Tipo de pago no válido.', 'kind')

    payment = Payment(
        patient_id=patient.id,
        amount=amount,
        method=method,
        reference=reference,
        receipt_image_path=receipt_path,
        discount=float(discount or 0),
        date=date_ or datetime.utcnow(),
        notes=notes,
        kind=kind,
        category=category if kind == 'one_off' else None,
        import_id=import_id,
        status='completed',
    )
    db.session.add(payment)
    db.session.flush()
    made = []
    if kind == 'installment':
        made = _apply(payment, _targets(patient.id, installment_id, contract_id), amount, source, import_id, user_id)
    left = round(amount - sum(a.amount for a in made), 2) if kind == 'installment' else 0.0
    if commit:
        db.session.commit()
    return payment, made, left


def allocate_existing(payment, *, contract_id=None, installment_id=None, source='import', import_id=None, user_id=None):
    """Aplica a cuotas un pago ya registrado (histórico) por lo que aún no tenga aplicado."""
    payment.kind = 'installment'
    payment.category = None
    left = round(float(payment.amount or 0) - allocated(payment.id), 2)
    if left <= EPS:
        return []
    return _apply(payment, _targets(payment.patient_id, installment_id, contract_id), left, source, import_id, user_id)


def classify_one_off(payment, category):
    if category not in ONE_OFF_CATEGORIES:
        raise BillingError('Categoría de pago suelto no válida.', 'category')
    if allocated(payment.id) > EPS:
        raise BillingError(f'El pago #{payment.id} ya está aplicado a cuotas: no puede ser suelto.', 'kind')
    payment.kind = 'one_off'
    payment.category = category


def apply_credit(patient_id, source='credit', import_id=None, user_id=None):
    """Aplica el saldo a favor del paciente a sus cuotas abiertas (lo antes pagado cubre lo primero que vence)."""
    made = []
    for payment, left in _unapplied_payments(patient_id):
        targets = open_installments(patient_id)
        if not targets:
            break
        made += _apply(payment, targets, left, source, import_id, user_id)
    return made


def revert_payment(payment):
    """Deshace lo que un pago aplicó (antes de anularlo o borrarlo). No hace commit."""
    allocs = PaymentAllocation.query.filter_by(payment_id=payment.id).all()
    touched = []
    for a in allocs:
        inst = db.session.get(Installment, a.installment_id)
        if inst:
            inst.paid_amount = max(0.0, round(float(inst.paid_amount or 0) - a.amount, 2))
            if inst.payment_id == payment.id:
                inst.payment_id = None
            if inst.paid_amount <= EPS:
                inst.status, inst.paid_date, inst.real_amount, inst.payment_method = 'pending', None, None, None
            else:
                inst.status = 'paid' if _remaining(inst) <= EPS else 'partial'
                inst.real_amount = inst.paid_amount
            touched.append(inst)
        db.session.delete(a)
    return touched


# ── planes ───────────────────────────────────────────────────────────────────


def _monthly(first_due, day, count):
    out = []
    for i in range(count):
        y = first_due.year + (first_due.month - 1 + i) // 12
        m = (first_due.month - 1 + i) % 12 + 1
        out.append(date(y, m, min(day, monthrange(y, m)[1])))
    return out


def _months_until(first_due, until):
    return max(1, (until.year - first_due.year) * 12 + until.month - first_due.month + 1)


def create_plan(
    patient_id,
    amount,
    payment_day,
    first_due,
    *,
    installments=None,
    billing_type='Mensual',
    name=None,
    service_start=None,
    notes=None,
    today=None,
    import_id=None,
    user_id=None,
    commit=True,
):
    """Crea el contrato con su cronograma. `installments=None` = renovable (se genera hasta el mes siguiente y luego
    una cuota por mes). Aplica enseguida el saldo a favor que el paciente tuviera."""
    patient = db.session.get(User, int(patient_id)) if patient_id else None
    if not patient or patient.role != 'jugador':
        raise BillingError('Elige un paciente válido.', 'patient')
    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError) as exc:
        raise BillingError('El monto de la cuota debe ser un número.', 'amount') from exc
    if amount <= 0:
        raise BillingError('El monto de la cuota debe ser mayor que cero.', 'amount')
    day = int(payment_day or first_due.day)
    if not 1 <= day <= 31:
        raise BillingError('El día de pago debe estar entre 1 y 31.', 'payment_day')
    if billing_type not in ('Mensual', 'Quincenal'):
        raise BillingError('La frecuencia debe ser Mensual o Quincenal.', 'billing_type')
    if installments is not None and not 1 <= int(installments) <= 60:
        raise BillingError('El número de cuotas debe estar entre 1 y 60 (o vacío para renovable).', 'installments')
    today = today or date.today()
    renewable = installments is None
    count = int(installments) if not renewable else 0
    if billing_type == 'Quincenal':
        if renewable:
            count = max(1, ((today + timedelta(days=31)) - first_due).days // 14 + 1)
        dues = [first_due + timedelta(days=14 * i) for i in range(count)]
    else:
        if renewable:
            nxt = today.replace(day=1) + timedelta(days=32)
            count = _months_until(first_due, nxt)
        dues = _monthly(first_due, day, count)

    contract = Contract(
        patient_id=patient.id,
        name=name or f'Plan {billing_type.lower()} desde {first_due.strftime("%m/%Y")}',
        total_amount=round(amount * count, 2),
        installment_count=count,
        installment_amount=amount,
        start_date=service_start or first_due,
        payment_start_date=first_due,
        status='active',
        notes=notes,
        billing_type=billing_type,
        sign_date=service_start or first_due,
        service_start_date=service_start or first_due,
        renewable=renewable,
        payment_day=day,
    )
    db.session.add(contract)
    db.session.flush()
    label = 'Cuota quincenal' if billing_type == 'Quincenal' else 'Cuota mensual'
    for i, due in enumerate(dues, start=1):
        db.session.add(
            Installment(contract_id=contract.id, number=i, due_date=due, amount=amount, description=f'{label} {i}')
        )
    db.session.flush()
    apply_credit(patient.id, import_id=import_id, user_id=user_id)
    if commit:
        db.session.commit()
    return contract


def extend_renewables(today=None):
    """Job diario: cada contrato renovable tiene generada su cuota del mes siguiente. Devuelve cuántas creó."""
    today = today or date.today()
    horizon = today + timedelta(days=31)
    created = 0
    for c in Contract.query.filter(
        Contract.renewable.is_(True), Contract.status == 'active', Contract.is_active.isnot(False)
    ):
        last = Installment.query.filter_by(contract_id=c.id).order_by(Installment.due_date.desc()).first()
        if not last:
            continue
        due, number = last.due_date, last.number
        while due < horizon:
            if c.billing_type == 'Quincenal':
                due = due + timedelta(days=14)
            else:
                due = _monthly(due, c.payment_day or due.day, 2)[1]
            number += 1
            db.session.add(
                Installment(
                    contract_id=c.id,
                    number=number,
                    due_date=due,
                    amount=c.installment_amount,
                    description=f'Cuota {number}',
                )
            )
            c.installment_count = number
            c.total_amount = round(float(c.total_amount or 0) + float(c.installment_amount or 0), 2)
            created += 1
        db.session.flush()
        apply_credit(c.patient_id)
    db.session.commit()
    return created


# ── cronograma ───────────────────────────────────────────────────────────────


def schedule(patient_id):
    """Cronograma completo del paciente: contratos, cuotas con lo aplicado, saldo a favor y pagos fuera de cuotas."""
    contracts = (
        Contract.query.filter(Contract.patient_id == patient_id, Contract.is_active.isnot(False))
        .order_by(Contract.id)
        .all()
    )
    inst_ids = [i.id for c in contracts for i in c.installments]
    allocs = defaultdict(list)
    if inst_ids:
        for a, p in (
            db.session.query(PaymentAllocation, Payment)
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .filter(PaymentAllocation.installment_id.in_(inst_ids))
            .order_by(Payment.date)
        ):
            allocs[a.installment_id].append(
                {
                    'payment_id': p.id,
                    'amount': a.amount,
                    'date': p.date.isoformat() if p.date else None,
                    'method': p.method,
                }
            )
    today = date.today()
    out = []
    for c in contracts:
        rows = sorted(c.installments, key=lambda i: (i.due_date, i.number))
        out.append(
            {
                'id': c.id,
                'name': c.name,
                'status': c.status,
                'renewable': bool(c.renewable),
                'billing_type': c.billing_type,
                'payment_day': c.payment_day,
                'installments': [
                    {
                        'id': i.id,
                        'number': i.number,
                        'due_date': i.due_date.isoformat(),
                        'amount': float(i.amount or 0),
                        'paid': float(i.paid_amount or 0),
                        'remaining': round(_remaining(i), 2),
                        'status': i.status,
                        'overdue': i.status in OPEN and i.due_date < today and _remaining(i) > EPS,
                        'payments': allocs.get(i.id, []),
                    }
                    for i in rows
                    if i.is_active is not False
                ],
            }
        )
    loose = Payment.query.filter(
        Payment.patient_id == patient_id, Payment.is_active.isnot(False), Payment.kind.in_(('one_off', 'unassigned'))
    ).order_by(Payment.date.desc())
    return {
        'contracts': out,
        'credit': credit(patient_id),
        'other_payments': [
            {
                'id': p.id,
                'date': p.date.isoformat() if p.date else None,
                'amount': float(p.amount or 0),
                'method': p.method,
                'kind': p.kind,
                'category': p.category,
            }
            for p in loose
        ],
    }


# ── migración inicial ────────────────────────────────────────────────────────


def backfill_allocations():
    """Una sola vez: los pagos que ya estaban enlazados a una cuota pasan al libro con su asignación."""
    if PaymentAllocation.query.first() is not None:
        return 0
    rows = Payment.query.filter(Payment.installment_id.isnot(None), Payment.is_active.isnot(False)).all()
    for p in rows:
        db.session.add(
            PaymentAllocation(
                payment_id=p.id, installment_id=p.installment_id, amount=float(p.amount or 0), source='installment'
            )
        )
        if not p.kind:
            p.kind = 'installment'
    db.session.commit()
    return len(rows)


# ── lo que entra (cronograma de cobros) ──────────────────────────────────────


def incoming(today=None, weeks=4, sede_id=None):
    """Cuotas vencidas y por vencer en las próximas `weeks` semanas, con totales por semana."""
    today = today or date.today()
    horizon = today + timedelta(weeks=weeks)
    q = (
        db.session.query(Installment, Contract, User)
        .join(Contract, Contract.id == Installment.contract_id)
        .join(User, User.id == Contract.patient_id)
        .filter(
            Contract.status == 'active',
            Contract.is_active.isnot(False),
            Installment.is_active.isnot(False),
            Installment.status.in_(OPEN),
            Installment.due_date <= horizon,
        )
        .order_by(Installment.due_date, User.username)
    )
    if sede_id:
        q = q.filter(User.sede_id == sede_id)
    items, weeks_total = [], defaultdict(float)
    overdue_total = 0.0
    monday = today - timedelta(days=today.weekday())
    for inst, contract, u in q:
        left = round(_remaining(inst), 2)
        if left <= EPS:
            continue
        overdue = inst.due_date < today
        if overdue:
            overdue_total += left
        else:
            wk = (inst.due_date - monday).days // 7
            weeks_total[wk] += left
        items.append(
            {
                'installment_id': inst.id,
                'number': inst.number,
                'due_date': inst.due_date.isoformat(),
                'remaining': left,
                'overdue': overdue,
                'contract': {'id': contract.id, 'name': contract.name},
                'patient': {'id': u.id, 'name': u.username or u.email, 'code': u.login_code or ''},
            }
        )
    return {
        'overdue_total': round(overdue_total, 2),
        'weeks': [
            {'start': (monday + timedelta(weeks=i)).isoformat(), 'total': round(weeks_total.get(i, 0.0), 2)}
            for i in range(weeks + 1)
        ],
        'items': items[:200],
    }
