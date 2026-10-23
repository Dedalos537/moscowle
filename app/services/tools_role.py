"""Herramientas del asistente para terapeutas y pacientes.

Antes el terapeuta tenía herramientas pensadas para el admin y el paciente casi ninguna (fecha y avisos), así que
las respuestas eran pobres. Estas trabajan SIEMPRE sobre el usuario con sesión (`_user_id`): un terapeuta solo ve
a sus pacientes y un paciente solo lo suyo.

Terapeuta: resumen de sus pacientes (quién no tiene sesión agendada), solicitudes de alta y de sesiones (las aprueba
coordinación, con las mismas reglas que el formulario de Solicitudes) y el estado de sus solicitudes.
Paciente: sus sesiones, sus cuotas y pagos, y los juegos de su sesión.
"""

from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Appointment, User
from app.services.tools_registry import CORE_TOOL_NAMES, tool

THERAPIST = {'terapista'}
PATIENT = {'jugador'}
CANCELLED = ('cancelled', 'canceled')


def _me(user_id):
    return db.session.get(User, int(user_id)) if user_id else None


def _iso(dt):
    return dt.isoformat() if dt else None


# ── terapeuta ───────────────────────────────────────────────────────────────
@tool(
    name='my_patients_overview',
    description=(
        'Mis pacientes (los del terapeuta que pregunta) con su próxima y última sesión. Sirve para: «qué alumnos '
        'no tienen sesiones agendadas», «a quién no veo hace tiempo», «cuántos pacientes tengo». '
        'only_without_upcoming=true deja solo a los que no tienen ninguna sesión futura.'
    ),
    parameters={
        'type': 'object',
        'properties': {
            'only_without_upcoming': {'type': 'boolean', 'description': 'Solo los que no tienen sesión agendada'}
        },
    },
    roles=THERAPIST,
)
def handle_my_patients_overview(only_without_upcoming=False, _user_id=None, **kwargs):
    me = _me(_user_id)
    if not me:
        return {'error': 'Sin usuario'}
    patients = [p for p in me.associated_patients.filter_by(role='jugador').all() if p.is_active is not False]
    now = datetime.utcnow()
    rows = []
    for p in patients:
        nxt = (
            Appointment.query.filter(
                Appointment.patient_id == p.id, Appointment.start_time >= now, Appointment.status.notin_(CANCELLED)
            )
            .order_by(Appointment.start_time)
            .first()
        )
        last = (
            Appointment.query.filter(Appointment.patient_id == p.id, Appointment.status == 'completed')
            .order_by(Appointment.start_time.desc())
            .first()
        )
        rows.append(
            {
                'patient_id': p.id,
                'name': p.username,
                'code': p.login_code,
                'next_session': _iso(nxt.start_time) if nxt else None,
                'last_session': _iso(last.start_time) if last else None,
                'days_since_last': (now - last.start_time).days if last else None,
            }
        )
    without = [r for r in rows if not r['next_session']]
    shown = without if only_without_upcoming else rows
    return {
        'success': True,
        'total_patients': len(rows),
        'without_upcoming_session': len(without),
        'patients': shown,
        'hint': 'Para agendarles, usa request_sessions (lo aprueba coordinación).',
    }


@tool(
    name='request_patient_signup',
    description=(
        'Envía a coordinación una SOLICITUD de alta de paciente nuevo (el terapeuta no crea usuarios directo). '
        'Queda asignado al terapeuta que lo pide cuando se aprueba. Pide nombre completo; apoderado y teléfono si los hay.'
    ),
    parameters={
        'type': 'object',
        'properties': {
            'username': {'type': 'string', 'description': 'Nombre completo del paciente'},
            'guardian_name': {'type': 'string', 'description': 'Nombre del apoderado'},
            'guardian_contact': {'type': 'string', 'description': 'Teléfono o correo del apoderado'},
            'phone': {'type': 'string'},
            'email': {'type': 'string'},
            'notes': {'type': 'string', 'description': 'Comentarios para coordinación'},
        },
        'required': ['username'],
    },
    category='write',
    roles=THERAPIST,
)
def handle_request_patient_signup(_user_id=None, **payload):
    return _create_request('patient', payload, _user_id)


@tool(
    name='request_sessions',
    description=(
        'Envía a coordinación una SOLICITUD para programar sesiones a uno de mis pacientes (de 1 a 10 fechas, '
        'mismo horario). Fechas YYYY-MM-DD, horas HH:MM. Coordinación la aprueba y se crean con choques y feriados '
        'revisados. Si no sabes el id del paciente, usa my_patients_overview.'
    ),
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer'},
            'dates': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Fechas YYYY-MM-DD (1 a 10)'},
            'start_time': {'type': 'string', 'description': 'HH:MM'},
            'end_time': {'type': 'string', 'description': 'HH:MM'},
            'title_prefix': {'type': 'string', 'description': 'Título, p. ej. «Terapia de lenguaje»'},
            'notes': {'type': 'string'},
        },
        'required': ['patient_id', 'dates', 'start_time', 'end_time'],
    },
    category='write',
    roles=THERAPIST,
)
def handle_request_sessions(_user_id=None, **payload):
    return _create_request('sessions', payload, _user_id)


def _create_request(kind, payload, user_id):
    from app.models.action_request import ActionRequest
    from app.services.action_requests import RequestError, notify_staff, validate

    me = _me(user_id)
    if not me or me.role != 'terapista':
        return {'error': 'Solo los terapeutas envían solicitudes.'}
    payload = {k: v for k, v in payload.items() if not k.startswith('_')}
    try:
        clean, summary = validate(kind, payload, me)
    except RequestError as exc:
        return {'error': str(exc)}
    req = ActionRequest(requester_id=me.id, kind=kind, payload=clean, summary=summary)
    db.session.add(req)
    db.session.commit()
    notify_staff(req)
    return {
        'success': True,
        'request_id': req.id,
        'summary': summary,
        'message': 'Solicitud enviada a coordinación. Te aviso cuando la aprueben o rechacen.',
    }


@tool(
    name='list_my_requests',
    description='Mis solicitudes a coordinación (altas, sesiones, grupos) y en qué estado están.',
    parameters={'type': 'object', 'properties': {}},
    roles=THERAPIST,
)
def handle_list_my_requests(_user_id=None, **kwargs):
    from app.models.action_request import ActionRequest

    rows = (
        ActionRequest.query.filter_by(requester_id=int(_user_id or 0))
        .order_by(ActionRequest.created_at.desc())
        .limit(20)
        .all()
    )
    labels = {'pending': 'en revisión', 'approved': 'aprobada', 'rejected': 'rechazada'}
    return {
        'success': True,
        'requests': [
            {
                'id': r.id,
                'summary': r.summary,
                'status': labels.get(r.status, r.status),
                'note': r.review_note,
                'created_at': _iso(r.created_at),
            }
            for r in rows
        ],
    }


# ── paciente ────────────────────────────────────────────────────────────────
@tool(
    name='my_sessions',
    description='Mis próximas sesiones y las últimas que tuve (fecha, hora, terapeuta y si hay juegos para jugar).',
    parameters={'type': 'object', 'properties': {}},
    roles=PATIENT,
)
def handle_my_sessions(_user_id=None, **kwargs):
    now = datetime.utcnow()
    me_id = int(_user_id or 0)
    upcoming = (
        Appointment.query.filter(
            Appointment.patient_id == me_id,
            Appointment.start_time >= now - timedelta(hours=2),
            Appointment.status.notin_(CANCELLED),
        )
        .order_by(Appointment.start_time)
        .limit(10)
        .all()
    )
    recent = (
        Appointment.query.filter(Appointment.patient_id == me_id, Appointment.start_time < now)
        .order_by(Appointment.start_time.desc())
        .limit(5)
        .all()
    )

    def row(a):
        return {
            'date': _iso(a.start_time),
            'title': a.title,
            'therapist': a.therapist.username if a.therapist else None,
            'status': a.status,
            'games': a.games_list,
        }

    return {'success': True, 'upcoming': [row(a) for a in upcoming], 'recent': [row(a) for a in recent]}


@tool(
    name='my_payments',
    description='Mis cuotas (vencidas y próximas) y mis últimos pagos.',
    parameters={'type': 'object', 'properties': {}},
    roles=PATIENT,
)
def handle_my_payments(_user_id=None, **kwargs):
    from app.models.contract import Contract, Installment
    from app.models.payment import Payment

    me_id = int(_user_id or 0)
    today = date.today()
    inst = (
        db.session.query(Installment)
        .join(Contract, Contract.id == Installment.contract_id)
        .filter(
            Contract.patient_id == me_id,
            Contract.is_active.isnot(False),
            Installment.is_active.isnot(False),
            Installment.status != 'cancelled',
        )
        .order_by(Installment.due_date)
        .all()
    )
    pending = [i for i in inst if (i.paid_amount or 0) < (i.amount or 0)]
    overdue = [i for i in pending if i.due_date < today]
    upcoming = [i for i in pending if i.due_date >= today][:3]
    payments = (
        Payment.query.filter(Payment.patient_id == me_id, Payment.is_active.isnot(False))
        .order_by(Payment.date.desc())
        .limit(5)
        .all()
    )

    def irow(i):
        return {
            'due_date': i.due_date.isoformat(),
            'amount': i.amount,
            'pending': round((i.amount or 0) - (i.paid_amount or 0), 2),
        }

    return {
        'success': True,
        'overdue_total': round(sum((i.amount or 0) - (i.paid_amount or 0) for i in overdue), 2),
        'overdue': [irow(i) for i in overdue],
        'upcoming': [irow(i) for i in upcoming],
        'recent_payments': [{'date': _iso(p.date), 'amount': p.amount, 'method': p.method} for p in payments],
        'hint': 'Puedes pagar por Yape/Plin o en el centro; el comprobante se sube en Pagos.',
    }


for _name in (
    'my_patients_overview',
    'request_patient_signup',
    'request_sessions',
    'list_my_requests',
    'my_sessions',
    'my_payments',
):
    if _name not in CORE_TOOL_NAMES:
        CORE_TOOL_NAMES.append(_name)
