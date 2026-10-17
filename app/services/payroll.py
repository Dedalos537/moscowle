"""Nómina de terapeutas por periodo (PRP 008).

- Lo que corresponde a un terapeuta en un mes = horas de sus sesiones completadas × tarifa
  (`salary_base / contract_hours`). Una sesión sin `duration_minutes` cuenta con la duración estándar
  (ajuste `payroll.default_session_minutes`, por defecto 45) y se informa para revisarla: antes valía 0.
- Lo pagado se registra como `Expense(category='therapist_payment')` apuntando al periodo (`payroll_period_id`):
  pagar en mayo la liquidación de abril deja abril pagado y mayo sin sobrepago. Los pagos antiguos sin periodo
  se atribuyen al mes de su fecha (como se hacía antes).
- Cada periodo vence el día `payroll.due_day` (por defecto 5) del mes siguiente. Al cerrarse (job del día 1),
  el monto queda congelado; mientras está abierto se recalcula con las sesiones que se vayan completando.
"""

from calendar import monthrange
from datetime import date, datetime

from app.extensions import db
from app.models import Appointment, User
from app.models.billing import PayrollPeriod
from app.models.payment import Expense
from app.models.system_setting import SystemSetting
from app.services.report_service import lima_today, utc_bounds

DEFAULTS = {'payroll.default_session_minutes': 45, 'payroll.due_day': 5}


def setting(key):
    row = db.session.get(SystemSetting, key)
    try:
        return int(row.value) if row and row.value not in (None, '') else DEFAULTS[key]
    except ValueError:
        return DEFAULTS[key]


def save_settings(values, user_id=None):
    for key, val in (values or {}).items():
        if key not in DEFAULTS or val in (None, ''):
            continue
        num = int(val)
        if key == 'payroll.due_day' and not 1 <= num <= 28:
            raise ValueError('El día de pago a terapeutas debe estar entre 1 y 28.')
        if key == 'payroll.default_session_minutes' and not 15 <= num <= 180:
            raise ValueError('La duración estándar debe estar entre 15 y 180 minutos.')
        row = db.session.get(SystemSetting, key) or SystemSetting(key=key)
        row.value = str(num)
        row.updated_by_id = user_id
        db.session.add(row)
    db.session.commit()
    return {k: setting(k) for k in DEFAULTS}


def _bounds(period):
    y, m = (int(x) for x in period.split('-'))
    first = date(y, m, 1)
    last = date(y, m, monthrange(y, m)[1])
    return first, last


def period_of(d):
    return f'{d.year:04d}-{d.month:02d}'


def _due(period):
    y, m = (int(x) for x in period.split('-'))
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return date(y, m, min(setting('payroll.due_day'), monthrange(y, m)[1]))


def _compute(therapist, period):
    first, last = _bounds(period)
    start, end = utc_bounds(first, last)
    rows = (
        db.session.query(Appointment.duration_minutes)
        .filter(
            Appointment.therapist_id == therapist.id,
            Appointment.status == 'completed',
            Appointment.start_time >= start,
            Appointment.start_time < end,
            Appointment.is_active.isnot(False),
        )
        .all()
    )
    std = setting('payroll.default_session_minutes')
    minutes = sum((d or std) for (d,) in rows)
    rate = (therapist.salary_base or 0) / therapist.contract_hours if therapist.contract_hours else 0.0
    return {
        'sessions': len(rows),
        'sessions_without_duration': sum(1 for (d,) in rows if not d),
        'hours': round(minutes / 60, 2),
        'rate': round(rate, 4),
        'amount_due': round(rate * minutes / 60, 2),
    }


def sync(therapist, period):
    """Crea o actualiza el periodo (si sigue abierto) y lo devuelve."""
    row = PayrollPeriod.query.filter_by(therapist_id=therapist.id, period=period).first()
    if row and row.closed_at:
        return row
    calc = _compute(therapist, period)
    if not row:
        row = PayrollPeriod(therapist_id=therapist.id, period=period, due_date=_due(period))
        db.session.add(row)
    for k, v in calc.items():
        setattr(row, k, v)
    row.due_date = _due(period)
    db.session.flush()
    return row


def paid(row):
    """Pagado contra el periodo: pagos con su `payroll_period_id` + pagos antiguos sin periodo del mismo mes."""
    first, last = _bounds(row.period)
    linked = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0))
        .filter(Expense.payroll_period_id == row.id, Expense.is_active.isnot(False))
        .scalar()
    )
    legacy = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0.0))
        .filter(
            Expense.payroll_period_id.is_(None),
            Expense.therapist_id == row.therapist_id,
            Expense.category == 'therapist_payment',
            Expense.is_active.isnot(False),
            Expense.date >= datetime.combine(first, datetime.min.time()),
            Expense.date < datetime.combine(last, datetime.max.time()),
        )
        .scalar()
    )
    return round(float(linked or 0) + float(legacy or 0), 2)


def status(row, paid_amount, today=None):
    today = today or lima_today()
    if row.amount_due <= 0.005 and paid_amount <= 0.005:
        return 'none'
    if paid_amount >= row.amount_due - 0.005:
        return 'paid'
    if row.due_date < today:
        return 'overdue'
    return 'partial' if paid_amount > 0.005 else 'pending'


def serialize(row, therapist=None, today=None):
    p = paid(row)
    therapist = therapist or db.session.get(User, row.therapist_id)
    return {
        'id': row.id,
        'therapist': {'id': therapist.id, 'name': therapist.username or therapist.email} if therapist else None,
        'period': row.period,
        'hours': row.hours,
        'sessions': row.sessions,
        'sessions_without_duration': row.sessions_without_duration,
        'rate': row.rate,
        'amount_due': round(row.amount_due, 2),
        'paid': p,
        'balance': round(row.amount_due - p, 2),
        'due_date': row.due_date.isoformat(),
        'closed': bool(row.closed_at),
        'status': status(row, p, today),
    }


def recent_periods(months=4, today=None, therapist_id=None):
    """Periodos de los últimos `months` meses (incluido el actual) de los terapeutas activos."""
    today = today or lima_today()
    periods = []
    y, m = today.year, today.month
    for _ in range(months):
        periods.append(f'{y:04d}-{m:02d}')
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    q = User.query.filter(User.role == 'terapista', User.is_active.isnot(False))
    if therapist_id:
        q = q.filter(User.id == therapist_id)
    out = []
    for t in q.order_by(User.username):
        for per in periods:
            out.append(serialize(sync(t, per), t, today))
    db.session.commit()
    return [r for r in out if r['status'] != 'none']


def pay(therapist_id, period, amount, method, *, date_=None, notes=None, receipt_path=None, user_id=None):
    """Registra un pago a terapeuta contra un periodo (puede ser parcial)."""
    t = db.session.get(User, int(therapist_id)) if therapist_id else None
    if not t or t.role != 'terapista':
        raise ValueError('Elige un terapeuta válido.')
    try:
        _bounds(period)
    except (ValueError, AttributeError) as exc:
        raise ValueError('Indica el periodo (AAAA-MM) que se paga.') from exc
    amount = round(float(amount or 0), 2)
    if amount <= 0:
        raise ValueError('El monto debe ser mayor que cero.')
    row = sync(t, period)
    exp = Expense(
        category='therapist_payment',
        amount=amount,
        date=date_ or datetime.utcnow(),
        description=notes or f'Pago a terapeuta · periodo {period}',
        therapist_id=t.id,
        method=method or 'Transferencia',
        receipt_image_path=receipt_path,
        payroll_period_id=row.id,
        created_by_id=user_id,
    )
    db.session.add(exp)
    db.session.commit()
    return exp, serialize(row, t)


def close_previous_month(today=None):
    """Job del día 1: congela el monto de los periodos del mes anterior."""
    today = today or lima_today()
    y, m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    per = f'{y:04d}-{m:02d}'
    count = 0
    for t in User.query.filter(User.role == 'terapista', User.is_active.isnot(False)):
        row = sync(t, per)
        if not row.closed_at:
            row.closed_at = datetime.utcnow()
            count += 1
    db.session.commit()
    return count
