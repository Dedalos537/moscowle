"""Balanced Scorecard por sede, calculado solo con datos registrados (nada estimado ni inventado).

Atribución a una sede (una sola regla, la misma en todas las cifras):
- Pacientes: `User.sede_id` del paciente.
- Sesiones, pagos, cuotas y métricas de juegos: la sede del paciente al que pertenecen.
- Terapeutas: los asignados a la sede (`therapist_sede`); un terapeuta puede estar en varias.
- Incidentes: los ligados a una sesión de un paciente de la sede o reportados por un usuario de la sede.

Periodos en días locales de Lima. Cada indicador trae el valor del periodo, el del periodo anterior de igual
duración, una serie de 6 meses y su meta; el estado sale de comparar valor y meta en la dirección correcta.
Cuando no hay datos para calcular un indicador, el valor es `None` (se muestra «Sin datos», nunca un 0 falso).
"""

import json
from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from app.models import Appointment, Payment, Sede, User, db
from app.models.appointment import SessionMetrics
from app.models.contract import Contract, Installment
from app.models.incidente import Incidente
from app.models.system_setting import SystemSetting
from app.services.report_service import lima_today, utc_bounds

TARGETS_KEY = 'bsc_targets'
PERIODS = {'month': 'Este mes', 'quarter': 'Este trimestre', 'year': 'Este año'}
CLOSED_INCIDENTS = ('RESUELTO', 'CERRADO')

# key, perspectiva, etiqueta, unidad, dirección (up = más es mejor), meta por defecto, cómo se calcula
KPIS = [
    ('revenue', 'financial', 'Ingresos cobrados', 'money', 'up', None, 'Pagos confirmados de pacientes de la sede.'),
    (
        'collection',
        'financial',
        'Cobranza de cuotas',
        'pct',
        'up',
        90,
        'Monto pagado de las cuotas que vencían en el periodo, sobre el monto que vencía.',
    ),
    (
        'overdue',
        'financial',
        'Deuda vencida',
        'money',
        'down',
        None,  # en soles depende del tamaño de cada centro: la fija el admin en «Metas»
        'Saldo de cuotas vencidas sin pagar al cierre del periodo.',
    ),
    ('ticket', 'financial', 'Ingreso por sesión', 'money', 'up', None, 'Ingresos cobrados entre sesiones realizadas.'),
    (
        'active_patients',
        'patients',
        'Pacientes atendidos',
        'int',
        'up',
        None,
        'Pacientes con al menos una sesión realizada.',
    ),
    ('new_patients', 'patients', 'Pacientes nuevos', 'int', 'up', None, 'Pacientes registrados en el periodo.'),
    (
        'attendance',
        'patients',
        'Asistencia',
        'pct',
        'up',
        85,
        'Sesiones con asistencia marcada como presente, sobre las que tienen asistencia registrada.',
    ),
    (
        'retention',
        'patients',
        'Continuidad',
        'pct',
        'up',
        80,
        'Pacientes atendidos en el periodo anterior que siguieron atendiéndose en este.',
    ),
    ('sessions_done', 'process', 'Sesiones realizadas', 'int', 'up', None, 'Sesiones con estado completada.'),
    (
        'cancel_rate',
        'process',
        'Cancelaciones',
        'pct',
        'down',
        10,
        'Sesiones canceladas sobre todas las programadas en el periodo.',
    ),
    (
        'closure',
        'process',
        'Agenda cerrada',
        'pct',
        'up',
        95,
        'Sesiones ya pasadas que quedaron cerradas (realizadas o canceladas) en lugar de seguir «programadas».',
    ),
    (
        'incidents_sla',
        'process',
        'Incidentes en plazo',
        'pct',
        'up',
        90,
        'Incidentes resueltos dentro de su plazo, sobre los resueltos en el periodo.',
    ),
    ('therapists', 'growth', 'Terapeutas asignados', 'int', 'up', None, 'Terapeutas activos asignados a la sede.'),
    (
        'load',
        'growth',
        'Pacientes por terapeuta',
        'dec',
        'down',
        12,
        'Pacientes atendidos entre terapeutas asignados.',
    ),
    (
        'accuracy',
        'growth',
        'Precisión en juegos',
        'pct',
        'up',
        70,
        'Promedio de precisión de los pacientes en los juegos terapéuticos.',
    ),
    (
        'open_incidents',
        'growth',
        'Incidentes abiertos',
        'int',
        'down',
        0,
        'Incidentes sin resolver al cierre del periodo.',
    ),
]
KPI_INDEX = {k[0]: k for k in KPIS}
PERSPECTIVES = [
    ('financial', 'Financiera', '¿La sede se sostiene y cobra lo que factura?'),
    ('patients', 'Pacientes', '¿Atendemos a más pacientes y vuelven?'),
    ('process', 'Procesos internos', '¿La agenda y la operación funcionan sin fricción?'),
    ('growth', 'Aprendizaje y crecimiento', '¿El equipo y los pacientes avanzan?'),
]


# ── metas ────────────────────────────────────────────────────────────────────


def get_targets():
    defaults = {k[0]: k[5] for k in KPIS}
    row = db.session.get(SystemSetting, TARGETS_KEY)
    if row and row.value:
        try:
            saved = json.loads(row.value)
            for key, val in saved.items():
                if key in defaults:
                    defaults[key] = None if val in (None, '') else float(val)
        except (ValueError, TypeError):
            pass
    return defaults


def save_targets(values, user_id=None):
    clean = {}
    for key, val in (values or {}).items():
        if key not in KPI_INDEX:
            continue
        if val in (None, ''):
            clean[key] = None
            continue
        num = float(val)
        if num < 0 or (KPI_INDEX[key][3] == 'pct' and num > 100):
            raise ValueError(f'Meta fuera de rango para «{KPI_INDEX[key][2]}».')
        clean[key] = num
    current = get_targets()
    current.update(clean)
    row = db.session.get(SystemSetting, TARGETS_KEY) or SystemSetting(key=TARGETS_KEY)
    row.value = json.dumps(current)
    row.updated_by_id = user_id
    db.session.add(row)
    db.session.commit()
    return current


# ── periodos ─────────────────────────────────────────────────────────────────


def _add_months(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def period_bounds(period, today=None):
    """(inicio, fin) del periodo en curso hasta hoy, y el periodo anterior de igual duración."""
    today = today or lima_today()
    if period == 'year':
        first = date(today.year, 1, 1)
    elif period == 'quarter':
        first = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
    else:
        first = date(today.year, today.month, 1)
    length = (today - first).days
    prev_last = first - timedelta(days=1)
    months = {'year': 12, 'quarter': 3}.get(period, 1)
    prev_first = _add_months(first, -months)
    # Mismo tramo transcurrido: el día 9 del mes se compara con los primeros 9 días del mes anterior.
    prev_last = min(prev_last, prev_first + timedelta(days=length))
    return (first, today), (prev_first, prev_last)


# ── cálculo ──────────────────────────────────────────────────────────────────


def _pct(num, den):
    return round(100.0 * num / den, 1) if den else None


class _Data:
    """Filas de la ventana de tiempo, cargadas una vez y repartidas por sede en memoria."""

    def __init__(self, start_day, end_day):
        self.today = end_day
        # «Pasada» = antes de este instante: una sesión de esta tarde todavía no debe contar como sin cerrar.
        self.now = min(utc_bounds(end_day)[1], datetime.now(UTC).replace(tzinfo=None))
        start, end = utc_bounds(start_day, end_day)
        self.patient_sede = {
            pid: sid
            for pid, sid in db.session.query(User.id, User.sede_id).filter(
                User.role == 'jugador', User.sede_id.isnot(None)
            )
        }
        self.new_patients = [
            (sid, created)
            for sid, created in db.session.query(User.sede_id, User.created_at).filter(
                User.role == 'jugador', User.sede_id.isnot(None), User.created_at >= start, User.created_at < end
            )
        ]
        self.appointments = (
            db.session.query(Appointment.patient_id, Appointment.start_time, Appointment.status, Appointment.attendance)
            .filter(Appointment.start_time >= start, Appointment.start_time < end, Appointment.is_active.isnot(False))
            .all()
        )
        self.payments = (
            db.session.query(Payment.patient_id, Payment.date, Payment.amount)
            .filter(
                Payment.date >= start,
                Payment.date < end,
                Payment.status == 'completed',
                Payment.is_active.isnot(False),
            )
            .all()
        )
        self.installments = (
            db.session.query(
                Contract.patient_id,
                Installment.due_date,
                Installment.amount,
                Installment.paid_amount,
                Installment.paid_date,
            )
            .join(Contract, Contract.id == Installment.contract_id)
            .filter(
                Installment.is_active.isnot(False),
                Contract.is_active.isnot(False),
                Installment.due_date <= end_day,
                Installment.status != 'cancelled',
            )
            .all()
        )
        self.metrics = (
            db.session.query(SessionMetrics.user_id, SessionMetrics.date, SessionMetrics.accurracy)
            .filter(SessionMetrics.date >= start, SessionMetrics.date < end, SessionMetrics.is_active.isnot(False))
            .all()
        )
        user_sede = dict(db.session.query(User.id, User.sede_id).filter(User.sede_id.isnot(None)).all())
        appt_patient = {}
        incidents = (
            db.session.query(
                Incidente.appointment_id,
                Incidente.user_id,
                Incidente.estado,
                Incidente.fecha_creacion,
                Incidente.fecha_resolucion,
                Incidente.fecha_limite_sla,
            )
            .filter(Incidente.fecha_creacion < end, Incidente.is_active.isnot(False))
            .all()
        )
        ids = [i.appointment_id for i in incidents if i.appointment_id]
        if ids:
            appt_patient = dict(
                db.session.query(Appointment.id, Appointment.patient_id).filter(Appointment.id.in_(ids))
            )
        self.incidents = []
        for i in incidents:
            sid = self.patient_sede.get(appt_patient.get(i.appointment_id)) or user_sede.get(i.user_id)
            if sid:
                self.incidents.append((sid, i))
        self.therapists = defaultdict(int)
        rows = (
            db.session.query(User.id, Sede.id)
            .join(User.assigned_sedes)
            .filter(User.role == 'terapista', User.is_active.isnot(False))
            .all()
        )
        for _uid, sid in rows:
            self.therapists[sid] += 1

    def sede_of(self, patient_id):
        return self.patient_sede.get(patient_id)


def _in(ts, start, end):
    return ts is not None and start <= ts < end


def _compute(data, sede_id, first_day, last_day, previous_active=None):
    start, end = utc_bounds(first_day, last_day)
    cutoff = min(end, data.now)
    own = data.sede_of

    appts = [a for a in data.appointments if own(a.patient_id) == sede_id and _in(a.start_time, start, end)]
    done = [a for a in appts if a.status == 'completed']
    cancelled = [a for a in appts if a.status in ('cancelled', 'canceled')]
    past = [a for a in appts if a.start_time < cutoff and a.status not in ('cancelled', 'canceled')]
    marked = [a for a in appts if a.attendance in ('present', 'absent')]
    active = {a.patient_id for a in done}

    revenue = sum(p.amount or 0 for p in data.payments if own(p.patient_id) == sede_id and _in(p.date, start, end))
    due = [i for i in data.installments if own(i.patient_id) == sede_id and first_day <= i.due_date <= last_day]
    due_amount = sum(i.amount or 0 for i in due)
    # Deuda tal como estaba al cierre del periodo: lo pagado después de esa fecha todavía se debía.
    overdue = sum(
        max(0.0, (i.amount or 0) - ((i.paid_amount or 0) if i.paid_date is None or i.paid_date < end else 0))
        for i in data.installments
        if own(i.patient_id) == sede_id and i.due_date < min(last_day, data.today)
    )

    acc = [
        m.accurracy * 100 if m.accurracy is not None and m.accurracy <= 1 else m.accurracy
        for m in data.metrics
        if own(m.user_id) == sede_id and _in(m.date, start, end) and m.accurracy is not None
    ]

    incidents = [i for sid, i in data.incidents if sid == sede_id]
    resolved = [i for i in incidents if _in(i.fecha_resolucion, start, end)]
    on_time = [i for i in resolved if i.fecha_limite_sla is None or i.fecha_resolucion <= i.fecha_limite_sla]
    open_now = [
        i
        for i in incidents
        if i.fecha_creacion < end
        and (i.fecha_resolucion is None or i.fecha_resolucion >= end)
        and i.estado not in CLOSED_INCIDENTS
    ]
    therapists = data.therapists.get(sede_id, 0)

    values = {
        'revenue': round(revenue, 2),
        'collection': _pct(sum(min(i.paid_amount or 0, i.amount or 0) for i in due), due_amount),
        'overdue': round(overdue, 2),
        'ticket': round(revenue / len(done), 2) if done else None,
        'active_patients': len(active),
        'new_patients': sum(1 for sid, c in data.new_patients if sid == sede_id and _in(c, start, end)),
        'attendance': _pct(sum(1 for a in marked if a.attendance == 'present'), len(marked)),
        'retention': _pct(len(previous_active & active), len(previous_active)) if previous_active else None,
        'sessions_done': len(done),
        'cancel_rate': _pct(len(cancelled), len(appts)),
        'closure': _pct(sum(1 for a in past if a.status == 'completed'), len(past)),
        'incidents_sla': _pct(len(on_time), len(resolved)),
        'therapists': therapists,
        'load': round(len(active) / therapists, 1) if therapists and active else None,
        'accuracy': round(sum(acc) / len(acc), 1) if acc else None,
        'open_incidents': len(open_now),
    }
    counts = {
        'sessions': len(appts),
        'cancelled': len(cancelled),
        'marked': len(marked),
        'installments_due': len(due),
        'games': len(acc),
        'resolved_incidents': len(resolved),
    }
    return values, counts, active


def _status(value, target, direction):
    if value is None or target is None:
        return 'none'
    if direction == 'up':
        if value >= target:
            return 'good'
        return 'warn' if value >= target * 0.85 else 'bad'
    if value <= target:
        return 'good'
    slack = max(target * 0.25, 1 if target == 0 else 0)
    return 'warn' if value <= target + slack else 'bad'


def scorecard(period='month', today=None):
    """Scorecard de todas las sedes activas: indicadores del periodo, el anterior y 6 meses de tendencia."""
    period = period if period in PERIODS else 'month'
    today = today or lima_today()
    (first, last), (pfirst, plast) = period_bounds(period, today)
    month_starts = [_add_months(date(today.year, today.month, 1), -n) for n in range(5, -1, -1)]
    # Ventana: lo más antiguo que se necesita (periodo anterior, tendencia y el mes previo a la tendencia).
    window_start = min(pfirst, _add_months(month_starts[0], -1), _add_months(pfirst, -12 if period == 'year' else -3))
    data = _Data(window_start, today)
    targets = get_targets()

    sedes = Sede.query.filter(db.or_(Sede.is_active.is_(True), Sede.is_active.is_(None))).order_by(Sede.name).all()
    out = []
    for sede in sedes:
        # Para la continuidad del periodo anterior hace falta el periodo previo a ese.
        span = (last - first).days
        pp_last = pfirst - timedelta(days=1)
        _, _, pp_active = _compute(data, sede.id, pp_last - timedelta(days=span), pp_last)
        prev_values, _, prev_active = _compute(data, sede.id, pfirst, plast, pp_active)
        values, counts, _ = _compute(data, sede.id, first, last, prev_active)

        trend = {k[0]: [] for k in KPIS}
        before = None
        for i, ms in enumerate(month_starts):
            me = today if i == len(month_starts) - 1 else _add_months(ms, 1) - timedelta(days=1)
            if before is None:
                pm = _add_months(ms, -1)
                _, _, before = _compute(data, sede.id, pm, ms - timedelta(days=1))
            mv, _, before = _compute(data, sede.id, ms, me, before)
            for key, series in trend.items():
                series.append(mv[key])

        kpis = []
        for key, persp, label, unit, direction, _default, how in KPIS:
            kpis.append(
                {
                    'key': key,
                    'perspective': persp,
                    'label': label,
                    'unit': unit,
                    'direction': direction,
                    'value': values[key],
                    'previous': prev_values[key],
                    'target': targets.get(key),
                    'status': _status(values[key], targets.get(key), direction),
                    'trend': trend[key],
                    'how': how,
                }
            )
        scored = [k for k in kpis if k['status'] != 'none']
        points = {'good': 1.0, 'warn': 0.5, 'bad': 0.0}
        perspectives = []
        for pkey, plabel, question in PERSPECTIVES:
            mine = [k for k in scored if k['perspective'] == pkey]
            perspectives.append(
                {
                    'key': pkey,
                    'label': plabel,
                    'question': question,
                    'score': round(100 * sum(points[k['status']] for k in mine) / len(mine)) if mine else None,
                }
            )
        out.append(
            {
                'id': sede.id,
                'name': sede.name,
                'address': sede.address,
                'score': round(100 * sum(points[k['status']] for k in scored) / len(scored)) if scored else None,
                'perspectives': perspectives,
                'kpis': kpis,
                'counts': counts,
            }
        )

    return {
        'period': period,
        'period_label': PERIODS[period],
        'range': {'from': first.isoformat(), 'to': last.isoformat()},
        'previous_range': {'from': pfirst.isoformat(), 'to': plast.isoformat()},
        'months': [m.isoformat() for m in month_starts],
        'perspectives': [{'key': k, 'label': lbl, 'question': q} for k, lbl, q in PERSPECTIVES],
        'targets': targets,
        'sedes': out,
    }
