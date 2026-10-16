"""Dashboard del centro: lo que hay que hacer hoy, si el centro crece y quién está en riesgo de dejarlo.

Todo sale de datos registrados (nada estimado). Los indicadores son los mismos del Balanced Scorecard de sedes
(`sede_scorecard`), calculados para todo el centro o para una sede, así ambas pantallas dicen lo mismo.

Secciones:
- `pulse`: indicadores del periodo con el anterior, la meta y 6 meses de tendencia.
- `flow`: altas y bajas de pacientes por mes (crecimiento neto).
- `today`: sesiones de hoy, cobros que vencen hoy y pendientes por aprobar.
- `risks`: pacientes activos con señales de abandono (deuda, faltas, sin agenda, plan por terminar, inactivos).
- `team`: carga y resultados de cada terapeuta en el periodo.
- `sedes`: puntaje y cifras clave de cada sede (solo cuando se mira todo el centro).
- `data_quality`: pacientes activos sin plan de pago (afectan la veracidad de las finanzas).
"""

from collections import defaultdict
from datetime import timedelta

from app.models import Appointment, Sede, User, db
from app.models.action_request import ActionRequest
from app.models.contract import Contract, Installment
from app.models.incidente import Incidente
from app.models.password_reset import PasswordReset
from app.models.user_status_log import UserStatusLog
from app.services import sede_scorecard as bsc
from app.services.messaging import MessagingService
from app.services.report_service import utc_bounds

LEFT_STATUSES = ('retired', 'inactive')
CANCELLED = ('cancelled', 'canceled')
RISK_KINDS = {
    'debt': ('Deuda vencida', 3),
    'absences': ('Faltó a sus últimas sesiones', 3),
    'idle': ('Sin sesiones recientes', 2),
    'no_schedule': ('Sin próxima sesión', 2),
    'plan_ending': ('Plan por terminar', 1),
}
MAX_RISKS = 40


def _sede_filter(query, column, sede_id):
    return query.filter(column == sede_id) if sede_id else query


def _patients(sede_id):
    q = User.query.filter(
        User.role == 'jugador',
        User.is_active.isnot(False),
        db.or_(User.account_status.is_(None), User.account_status.notin_(LEFT_STATUSES)),
    )
    return _sede_filter(q, User.sede_id, sede_id).all()


def _flow(sede_id, month_starts, today):
    """Altas (pacientes creados) y bajas (pasaron a retirado/inactivo) por mes."""
    first = utc_bounds(month_starts[0])[0]
    end = utc_bounds(today)[1]
    new_q = db.session.query(User.created_at).filter(
        User.role == 'jugador', User.created_at >= first, User.created_at < end
    )
    new_rows = [r[0] for r in _sede_filter(new_q, User.sede_id, sede_id)]
    left_q = (
        db.session.query(UserStatusLog.changed_at)
        .join(User, User.id == UserStatusLog.user_id)
        .filter(
            User.role == 'jugador',
            UserStatusLog.new_status.in_(LEFT_STATUSES),
            db.or_(UserStatusLog.old_status.is_(None), UserStatusLog.old_status.notin_(LEFT_STATUSES)),
            UserStatusLog.changed_at >= first,
            UserStatusLog.changed_at < end,
        )
    )
    left_rows = [r[0] for r in _sede_filter(left_q, User.sede_id, sede_id)]
    months = []
    for i, ms in enumerate(month_starts):
        me = today if i == len(month_starts) - 1 else bsc._add_months(ms, 1) - timedelta(days=1)
        s, e = utc_bounds(ms, me)
        new = sum(1 for c in new_rows if c and s <= c < e)
        left = sum(1 for c in left_rows if c and s <= c < e)
        months.append({'month': ms.isoformat(), 'new': new, 'left': left, 'net': new - left})
    return months


def _today(sede_id, today, names):
    start, end = utc_bounds(today)
    q = Appointment.query.filter(
        Appointment.start_time >= start, Appointment.start_time < end, Appointment.is_active.isnot(False)
    )
    if sede_id:
        q = q.join(User, User.id == Appointment.patient_id).filter(User.sede_id == sede_id)
    sessions = q.order_by(Appointment.start_time).all()
    by_status = defaultdict(int)
    for a in sessions:
        by_status[a.status or 'scheduled'] += 1
    items = [
        {
            'id': a.id,
            'start': a.start_time.isoformat() + 'Z',
            'status': a.status,
            'attendance': a.attendance,
            'patient': {'id': a.patient_id, 'name': names.get(a.patient_id, '')},
            'therapist': {'id': a.therapist_id, 'name': names.get(a.therapist_id, '')},
        }
        for a in sessions[:60]
    ]

    dq = (
        db.session.query(Contract.patient_id, Installment.amount, Installment.paid_amount)
        .join(Contract, Contract.id == Installment.contract_id)
        .filter(
            Installment.due_date == today,
            Installment.is_active.isnot(False),
            Contract.is_active.isnot(False),
            Installment.status.notin_(('paid', 'cancelled')),
        )
    )
    due = defaultdict(float)
    for pid, amount, paid in dq:
        due[pid] += max(0.0, (amount or 0) - (paid or 0))
    patients = {u.id: u for u in User.query.filter(User.id.in_(list(due))).all()} if due else {}
    payments = []
    for pid, amount in due.items():
        u = patients.get(pid)
        if not u or amount <= 0 or (sede_id and u.sede_id != sede_id):
            continue
        payments.append(
            {
                'patient': {'id': u.id, 'name': u.username or '', 'code': u.login_code or ''},
                'amount': round(amount, 2),
                'phone': MessagingService.resolve_phone(u) or None,
            }
        )
    payments.sort(key=lambda p: -p['amount'])

    pending = {
        'requests': ActionRequest.query.filter(ActionRequest.status == 'pending').count(),
        'password_resets': PasswordReset.query.filter(PasswordReset.status == 'awaiting_approval').count(),
        'incidents': Incidente.query.filter(
            Incidente.is_active.isnot(False), Incidente.estado.notin_(bsc.CLOSED_INCIDENTS)
        ).count(),
    }
    return {
        'sessions': {'total': len(sessions), 'by_status': dict(by_status), 'items': items},
        'payments_due': {
            'count': len(payments),
            'total': round(sum(p['amount'] for p in payments), 2),
            'items': payments,
        },
        'pending': pending,
    }


def _risks(patients, today, now):
    """Señales de abandono por paciente activo. Cada razón trae un texto concreto para decidir qué hacer."""
    if not patients:
        return {'total': 0, 'by_kind': {}, 'items': []}
    ids = [p.id for p in patients]
    since = now - timedelta(days=120)
    appts = defaultdict(list)
    for a in (
        db.session.query(Appointment.patient_id, Appointment.start_time, Appointment.status, Appointment.attendance)
        .filter(Appointment.patient_id.in_(ids), Appointment.start_time >= since, Appointment.is_active.isnot(False))
        .order_by(Appointment.start_time)
    ):
        appts[a.patient_id].append(a)
    overdue = defaultdict(float)
    for pid, amount, paid in (
        db.session.query(Contract.patient_id, Installment.amount, Installment.paid_amount)
        .join(Contract, Contract.id == Installment.contract_id)
        .filter(
            Contract.patient_id.in_(ids),
            Installment.due_date < today,
            Installment.is_active.isnot(False),
            Contract.is_active.isnot(False),
            Installment.status.notin_(('paid', 'cancelled')),
        )
    ):
        overdue[pid] += max(0.0, (amount or 0) - (paid or 0))

    items, by_kind = [], defaultdict(int)
    for p in patients:
        mine = appts.get(p.id, [])
        past = [a for a in mine if a.start_time < now]
        upcoming = [a for a in mine if a.start_time >= now and a.status not in CANCELLED]
        done = [a for a in past if a.status == 'completed']
        marked = [a for a in past if a.attendance in ('present', 'absent')]
        reasons = []
        if overdue.get(p.id, 0) > 0.009:
            reasons.append(('debt', f'Debe S/ {overdue[p.id]:,.2f} en cuotas vencidas'))
        last_two = marked[-2:]
        if len(last_two) == 2 and all(a.attendance == 'absent' for a in last_two):
            reasons.append(('absences', 'Faltó a sus 2 últimas sesiones'))
        last_done = done[-1].start_time if done else None
        if last_done is not None:
            days = (now - last_done).days
            if days > 21:
                reasons.append(('idle', f'Su última sesión fue hace {days} días'))
            if not upcoming and days <= 45:
                reasons.append(('no_schedule', 'No tiene ninguna sesión agendada'))
        remaining = p.sessions_remaining
        if (p.sessions_total or 0) > 0 and remaining is not None and 0 <= remaining <= 2:
            reasons.append(
                ('plan_ending', f'Le quedan {remaining} {"sesión" if remaining == 1 else "sesiones"} del plan')
            )
        if not reasons:
            continue
        for kind, _ in reasons:
            by_kind[kind] += 1
        items.append(
            {
                'patient': {'id': p.id, 'name': p.username or '', 'code': p.login_code or '', 'sede_id': p.sede_id},
                'phone': MessagingService.resolve_phone(p) or None,
                'score': sum(RISK_KINDS[k][1] for k, _ in reasons),
                'reasons': [{'kind': k, 'label': RISK_KINDS[k][0], 'detail': d} for k, d in reasons],
                'last_session': last_done.isoformat() + 'Z' if last_done else None,
                'next_session': upcoming[0].start_time.isoformat() + 'Z' if upcoming else None,
                'overdue': round(overdue.get(p.id, 0.0), 2),
                'sessions_remaining': remaining,
            }
        )
    items.sort(key=lambda r: (-r['score'], -r['overdue']))
    return {'total': len(items), 'by_kind': dict(by_kind), 'items': items[:MAX_RISKS]}


def _team(sede_id, first, last, now, names):
    start, end = utc_bounds(first, last)
    q = User.query.filter(User.role == 'terapista', User.is_active.isnot(False))
    if sede_id:
        q = q.filter(User.assigned_sedes.any(Sede.id == sede_id))
    therapists = q.all()
    if not therapists:
        return []
    ids = [t.id for t in therapists]
    aq = db.session.query(
        Appointment.therapist_id,
        Appointment.patient_id,
        Appointment.start_time,
        Appointment.status,
        Appointment.attendance,
    ).filter(
        Appointment.therapist_id.in_(ids),
        Appointment.is_active.isnot(False),
        Appointment.start_time >= start,
        Appointment.start_time < max(end, now + timedelta(days=7)),
    )
    if sede_id:
        aq = aq.join(User, User.id == Appointment.patient_id).filter(User.sede_id == sede_id)
    per = defaultdict(list)
    for a in aq:
        per[a.therapist_id].append(a)
    rows = []
    week_end = now + timedelta(days=7)
    for t in therapists:
        mine = per.get(t.id, [])
        period = [a for a in mine if start <= a.start_time < end]
        done = [a for a in period if a.status == 'completed']
        cancelled = [a for a in period if a.status in CANCELLED]
        marked = [a for a in period if a.attendance in ('present', 'absent')]
        rows.append(
            {
                'id': t.id,
                'name': names.get(t.id, t.username or ''),
                'patients': len({a.patient_id for a in done}),
                'sessions_done': len(done),
                'sessions_scheduled': len(period),
                'next_7_days': sum(1 for a in mine if now <= a.start_time < week_end and a.status not in CANCELLED),
                'attendance': bsc._pct(sum(1 for a in marked if a.attendance == 'present'), len(marked)),
                'cancel_rate': bsc._pct(len(cancelled), len(period)),
            }
        )
    rows.sort(key=lambda r: (-r['sessions_done'], r['name']))
    return rows


def _data_quality(patients):
    ids = [p.id for p in patients]
    with_contract = (
        {
            pid
            for (pid,) in db.session.query(Contract.patient_id).filter(
                Contract.patient_id.in_(ids), Contract.is_active.isnot(False), Contract.status == 'active'
            )
        }
        if ids
        else set()
    )
    missing = [p for p in patients if p.id not in with_contract and not (p.payment_amount or 0) > 0]
    return {
        'without_plan': len(missing),
        'items': [{'id': p.id, 'name': p.username or '', 'code': p.login_code or ''} for p in missing[:20]],
    }


def dashboard(period='month', sede_id=None, today=None):
    period, today, cur, prev, month_starts, data = bsc.load_window(period, today)
    targets = bsc.get_targets()
    unit = sede_id or bsc.CENTER
    center = bsc._unit_block(data, unit, cur, prev, month_starts, today, targets)
    names = dict(db.session.query(User.id, User.username).filter(User.role.in_(('jugador', 'terapista'))))
    patients = _patients(sede_id)

    sedes = []
    if not sede_id:
        for s in Sede.query.filter(db.or_(Sede.is_active.is_(True), Sede.is_active.is_(None))).order_by(Sede.name):
            block = bsc._unit_block(data, s.id, cur, prev, month_starts, today, targets)
            values = {k['key']: k for k in block['kpis']}
            sedes.append(
                {
                    'id': s.id,
                    'name': s.name,
                    'score': block['score'],
                    'kpis': {
                        key: {
                            'value': values[key]['value'],
                            'previous': values[key]['previous'],
                            'status': values[key]['status'],
                        }
                        for key in ('revenue', 'active_patients', 'attendance', 'collection', 'retention')
                    },
                }
            )

    return {
        'period': period,
        'period_label': bsc.PERIODS[period],
        'range': {'from': cur[0].isoformat(), 'to': cur[1].isoformat()},
        'previous_range': {'from': prev[0].isoformat(), 'to': prev[1].isoformat()},
        'months': [m.isoformat() for m in month_starts],
        'sede_id': sede_id,
        'score': center['score'],
        'perspectives': center['perspectives'],
        'pulse': center['kpis'],
        'flow': _flow(sede_id, month_starts, today),
        'today': _today(sede_id, today, names),
        'risks': _risks(patients, today, data.now),
        'team': _team(sede_id, cur[0], cur[1], data.now, names),
        'sedes': sedes,
        'data_quality': _data_quality(patients),
        'active_patients_now': len(patients),
    }
