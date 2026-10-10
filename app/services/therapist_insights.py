"""Reportes del terapeuta (sesiones + analíticas de la IA en una sola vista), con datos registrados.

Reemplaza dos pantallas que mostraban cifras falsas o vacías: «Analíticas IA» (confianza de modelos fija en el
código, «adaptaciones» que eran partidas jugadas, columnas que el backend no enviaba) y «Reportes» (tendencia de
precisión siempre en 0).

Alcance: sesiones donde el terapeuta es el responsable; pacientes = vínculo N:M (patient_therapist) más los que
atendió en el periodo. Periodo en días locales de Lima.
"""

from collections import defaultdict
from datetime import date, timedelta

from app.models import Appointment, User
from app.models.appointment import SessionMetrics
from app.services.report_service import lima_today, utc_bounds

RECOMMENDATION = {1: 'avanzar', 0: 'mantener', 2: 'apoyo'}
RECOMMENDATION_LABEL = {'avanzar': 'Subir dificultad', 'mantener': 'Mantener nivel', 'apoyo': 'Necesita apoyo'}
CANCELLED = ('cancelled', 'canceled')


def _acc(v):
    if v is None:
        return None
    return float(v) * 100 if float(v) <= 1 else float(v)


def _pct(num, den):
    return round(100.0 * num / den, 1) if den else None


def _avg(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 1) if values else None


def _monday(d):
    return d - timedelta(days=d.weekday())


def _lima_date(dt_utc):
    # utc_bounds convierte días locales a UTC; aquí el camino inverso (Lima = UTC-5, sin horario de verano).
    return (dt_utc - timedelta(hours=5)).date()


def build_insights(therapist, first_day=None, last_day=None):
    today = lima_today()
    last_day = last_day or today
    first_day = first_day or (last_day - timedelta(days=27))
    if first_day > last_day:
        first_day, last_day = last_day, first_day
    start, end = utc_bounds(first_day, last_day)

    appts = (
        Appointment.query.filter(
            Appointment.therapist_id == therapist.id,
            Appointment.start_time >= start,
            Appointment.start_time < end,
            Appointment.is_active.isnot(False),
        )
        .order_by(Appointment.start_time)
        .all()
    )
    linked = {p.id for p in therapist.associated_patients.filter_by(role='jugador').all()}
    patient_ids = linked | {a.patient_id for a in appts}
    users = {u.id: u for u in User.query.filter(User.id.in_(patient_ids)).all()} if patient_ids else {}

    metrics = (
        SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(patient_ids),
            SessionMetrics.date >= start,
            SessionMetrics.date < end,
            SessionMetrics.is_active.isnot(False),
        )
        .order_by(SessionMetrics.date)
        .all()
        if patient_ids
        else []
    )

    done = [a for a in appts if a.status == 'completed']
    held = [a for a in appts if a.status not in CANCELLED]
    marked = [a for a in appts if a.attendance in ('present', 'absent')]
    durations = [
        (a.end_time - a.start_time).total_seconds() / 60 for a in done if a.end_time and a.end_time > a.start_time
    ]

    kpis = {
        'sessions_done': len(done),
        'sessions_scheduled': len(held),
        'completion': _pct(len(done), len([a for a in held if a.start_time < end])),
        'attendance': _pct(sum(1 for a in marked if a.attendance == 'present'), len(marked)),
        'cancelled': len(appts) - len(held),
        'patients_seen': len({a.patient_id for a in done}),
        'avg_minutes': round(sum(durations) / len(durations)) if durations else None,
        'games_played': len(metrics),
        'accuracy': _avg([_acc(m.accurracy) for m in metrics]),
    }

    # Semanas (lunes a domingo, Lima) del periodo.
    weeks = []
    w = _monday(first_day)
    while w <= last_day:
        weeks.append(w)
        w += timedelta(days=7)
    by_week = {wk: {'done': 0, 'held': 0, 'present': 0, 'marked': 0, 'acc': []} for wk in weeks}
    for a in appts:
        wk = _monday(_lima_date(a.start_time))
        if wk not in by_week:
            continue
        if a.status not in CANCELLED:
            by_week[wk]['held'] += 1
        if a.status == 'completed':
            by_week[wk]['done'] += 1
        if a.attendance in ('present', 'absent'):
            by_week[wk]['marked'] += 1
            by_week[wk]['present'] += a.attendance == 'present'
    for m in metrics:
        wk = _monday(_lima_date(m.date))
        if wk in by_week:
            by_week[wk]['acc'].append(_acc(m.accurracy))
    weekly = [
        {
            'week': wk.isoformat(),
            'sessions_done': v['done'],
            'sessions_scheduled': v['held'],
            'attendance': _pct(v['present'], v['marked']),
            'accuracy': _avg(v['acc']),
            'games': len(v['acc']),
        }
        for wk, v in by_week.items()
    ]

    # Por paciente.
    appts_by_patient = defaultdict(list)
    for a in appts:
        appts_by_patient[a.patient_id].append(a)
    metrics_by_patient = defaultdict(list)
    for m in metrics:
        metrics_by_patient[m.user_id].append(m)
    patients = []
    for pid in patient_ids:
        u = users.get(pid)
        if not u or u.role != 'jugador':
            continue
        pa = appts_by_patient.get(pid, [])
        pm = metrics_by_patient.get(pid, [])
        accs = [_acc(m.accurracy) for m in pm]
        half = len(accs) // 2
        trend = None
        if len(accs) >= 4:
            trend = round(_avg(accs[half:]) - _avg(accs[:half]), 1)
        p_marked = [a for a in pa if a.attendance in ('present', 'absent')]
        attendance = _pct(sum(1 for a in p_marked if a.attendance == 'present'), len(p_marked))
        last_rec = RECOMMENDATION.get(pm[-1].prediction) if pm else None
        accuracy = _avg(accs)
        reasons = []
        if accuracy is not None and accuracy < 60:
            reasons.append('precisión baja')
        if trend is not None and trend <= -5:
            reasons.append('precisión en descenso')
        if attendance is not None and attendance < 70:
            reasons.append('faltas frecuentes')
        if last_rec == 'apoyo':
            reasons.append('la IA sugiere apoyo')
        last_done = max((a.start_time for a in pa if a.status == 'completed'), default=None)
        patients.append(
            {
                'id': pid,
                'name': u.username or u.email,
                'linked': pid in linked,
                'sessions_done': sum(1 for a in pa if a.status == 'completed'),
                'sessions_scheduled': sum(1 for a in pa if a.status not in CANCELLED),
                'attendance': attendance,
                'games': len(pm),
                'accuracy': accuracy,
                'trend': trend,
                'recommendation': last_rec,
                'last_session': _lima_date(last_done).isoformat() if last_done else None,
                'attention': reasons,
            }
        )
    patients.sort(key=lambda p: (-len(p['attention']), p['name'].lower()))

    # Recomendaciones de la IA (modelo de los juegos).
    rec_counts = defaultdict(int)
    for m in metrics:
        key = RECOMMENDATION.get(m.prediction)
        if key:
            rec_counts[key] += 1
    rec_total = sum(rec_counts.values())
    recommendations = [
        {
            'key': k,
            'label': RECOMMENDATION_LABEL[k],
            'count': rec_counts.get(k, 0),
            'pct': _pct(rec_counts.get(k, 0), rec_total),
        }
        for k in ('avanzar', 'mantener', 'apoyo')
    ]
    games = defaultdict(list)
    for m in metrics:
        games[m.game_name or 'Sin nombre'].append(m)
    by_game = []
    for name, ms in games.items():
        counts = defaultdict(int)
        for m in ms:
            if RECOMMENDATION.get(m.prediction):
                counts[RECOMMENDATION[m.prediction]] += 1
        top = max(counts.items(), key=lambda x: x[1])[0] if counts else None
        by_game.append(
            {
                'game': name,
                'plays': len(ms),
                'patients': len({m.user_id for m in ms}),
                'accuracy': _avg([_acc(m.accurracy) for m in ms]),
                'avg_time': _avg([m.avg_time for m in ms]),
                'recommendation': top,
            }
        )
    by_game.sort(key=lambda g: -g['plays'])
    recent = [
        {
            'patient': (users.get(m.user_id).username if users.get(m.user_id) else '') or '',
            'patient_id': m.user_id,
            'game': m.game_name,
            'accuracy': round(_acc(m.accurracy), 1) if m.accurracy is not None else None,
            'recommendation': RECOMMENDATION.get(m.prediction),
            'date': _lima_date(m.date).isoformat() if m.date else None,
        }
        for m in reversed(metrics[-12:])
    ]

    return {
        'range': {'from': first_day.isoformat(), 'to': last_day.isoformat()},
        'kpis': kpis,
        'weekly': weekly,
        'patients': patients,
        'ai': {
            'recommendations': recommendations,
            'total': rec_total,
            'by_game': by_game,
            'recent': recent,
            'labels': RECOMMENDATION_LABEL,
        },
    }


def parse_day(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None
