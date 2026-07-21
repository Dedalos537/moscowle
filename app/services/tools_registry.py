import logging
import os
import secrets
from datetime import datetime, timedelta

from flask import current_app, session

from app.auth_compat import current_user
from app.extensions import bcrypt, db
from app.models import AIChatMessage, Appointment, ContactMessage, Notification, Payment, Sede, User
from app.services.financial_service import FinancialService
from app.services.payment_service import PaymentService

ROLES_ADMIN = {'admin'}
ROLES_SUPERVISOR = {'admin', 'supervisor'}
ROLES_THERAPIST = {'admin', 'supervisor', 'terapista'}
ROLES_ALL = {'admin', 'supervisor', 'terapista', 'jugador'}

logger = logging.getLogger('app')

TOOL_REGISTRY = {}


def tool(name, description, parameters, category='read', roles=None):
    def decorator(func):
        TOOL_REGISTRY[name] = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'category': category,
            'roles': roles or ROLES_ALL,
            'handler': func,
        }
        return func
    return decorator


CORE_TOOL_NAMES = [
    'search_patients',
    'list_users',
    'get_patient_detail',
    'get_sessions',
    'get_financial_summary',
    'get_payment_history',
    'register_payment',
    'create_session',
    'update_session',
    'create_incident',
    'update_patient',
    'broadcast_message',
]


def get_tools_for_mode(mode, user_role=None):
    tools = []
    for name in CORE_TOOL_NAMES:
        t = TOOL_REGISTRY.get(name)
        if not t:
            continue
        if mode == 'chiquito' and t['category'] == 'write':
            continue
        if user_role and user_role not in t['roles']:
            continue
        tools.append({
            'type': 'function',
            'function': {
                'name': t['name'],
                'description': t['description'],
                'parameters': t['parameters'],
            },
        })
    return tools


def execute_tool(name, args):
    t = TOOL_REGISTRY.get(name)
    if not t:
        return {'error': f'Unknown tool: {name}'}
    try:
        return t['handler'](**args)
    except Exception as e:
        logger.error(f'Tool {name} error: {e}', exc_info=True)
        return {'error': str(e)}


def _api_get(endpoint):
    with current_app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = session.get('user_id')
            sess['role'] = session.get('role', 'admin')
        return c.get(endpoint)


def _api_post(endpoint, json=None):
    with current_app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = session.get('user_id')
            sess['role'] = session.get('role', 'admin')
        return c.post(endpoint, json=json or {})


@tool(
    name='search_patients',
    description='Busca pacientes por nombre o email. Retorna lista con ID y nombre.',
    parameters={
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Nombre o email del paciente (min 2 caracteres)'},
        },
        'required': ['query'],
    },
    category='read',
)
def handle_search_patients(query, limit=10):
    if len(query) < 2:
        return {'error': 'Minimo 2 caracteres'}
    patients = (
        User.query.filter(
            db.or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
            )
        )
        .limit(limit)
        .all()
    )
    return {
        'success': True,
        'count': len(patients),
        'patients': [
            {'id': p.id, 'username': p.username, 'email': p.email, 'role': p.role}
            for p in patients
        ],
    }


@tool(
    name='list_users',
    description='Lista usuarios del sistema. Filtrar por rol: admin, terapista, jugador, supervisor.',
    parameters={
        'type': 'object',
        'properties': {
            'role': {
                'type': 'string',
                'description': 'Filtrar por rol',
                'enum': ['admin', 'terapista', 'jugador', 'supervisor'],
            },
        },
    },
    category='read',
)
def handle_list_users(role=None):
    q = User.query
    if role:
        q = q.filter_by(role=role)
    users = q.order_by(User.username).limit(50).all()
    return {
        'success': True,
        'count': len(users),
        'users': [
            {'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role, 'is_active': u.is_active}
            for u in users
        ],
    }


@tool(
    name='get_patient_detail',
    description='Detalle completo de un paciente: datos, diagnostico, apoderado, pagos recientes, sesiones recientes.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_patient_detail(patient_id):
    patient = User.query.get(patient_id)
    if not patient or patient.role != 'jugador':
        return {'error': 'Paciente no encontrado'}
    age = None
    if patient.date_of_birth:
        today = datetime.utcnow().date()
        age = (today - patient.date_of_birth).days // 365
    sessions = (
        Appointment.query.filter_by(patient_id=patient_id, is_active=True)
        .order_by(Appointment.start_time.desc())
        .limit(5)
        .all()
    )
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).limit(5).all()
    return {
        'success': True,
        'patient': {
            'id': patient.id,
            'username': patient.username,
            'email': patient.email,
            'phone': patient.phone,
            'age': age,
            'sex': patient.sex,
            'preliminary_diagnosis': patient.preliminary_diagnosis,
            'therapy_goals': patient.therapy_goals,
            'guardian_name': patient.guardian_name,
            'guardian_contact': patient.guardian_contact,
            'sede_id': patient.sede_id,
            'sessions_total': patient.sessions_total,
            'sessions_attended': patient.sessions_attended,
            'sessions_remaining': patient.sessions_remaining,
        },
        'recent_sessions': [
            {'id': s.id, 'start_time': str(s.start_time), 'status': s.status, 'title': s.title}
            for s in sessions
        ],
        'recent_payments': [
            {'id': p.id, 'amount': float(p.amount), 'date': str(p.date), 'method': p.method}
            for p in payments
        ],
    }


@tool(
    name='get_sessions',
    description='Sesiones del calendario en un rango de fechas. Retorna lista de sesiones con paciente, terapeuta, estado.',
    parameters={
        'type': 'object',
        'properties': {
            'start': {'type': 'string', 'description': 'Fecha inicio YYYY-MM-DD'},
            'end': {'type': 'string', 'description': 'Fecha fin YYYY-MM-DD'},
        },
    },
    category='read',
)
def handle_get_sessions(start=None, end=None, therapist_id=None):
    try:
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        if therapist_id:
            params['therapist_id'] = therapist_id
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = _api_get(f'/admin/api/sessions?{qs}')
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'sessions': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_financial_summary',
    description='Resumen financiero del mes: ingresos, egresos, ganancia, cobranza.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_financial_summary():
    try:
        resp = _api_get('/admin/api/financial-summary')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_payment_history',
    description='Historial de pagos de un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='read',
)
def handle_payment_history(patient_id):
    patient = User.query.get(patient_id)
    if not patient:
        return {'error': 'Paciente no encontrado'}
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).limit(20).all()
    return {
        'success': True,
        'patient': {'id': patient.id, 'username': patient.username},
        'payments': [
            {'id': p.id, 'amount': float(p.amount), 'date': str(p.date), 'method': p.method, 'reference': p.reference}
            for p in payments
        ],
    }


@tool(
    name='register_payment',
    description='Registra un pago para un paciente. Necesita patient_id y amount.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente (usa search_patients si no lo tienes)'},
            'amount': {'type': 'number', 'description': 'Monto en soles'},
            'method': {
                'type': 'string',
                'description': 'Metodo de pago',
                'enum': ['Efectivo', 'Yape', 'Transferencia', 'IA/Copilot'],
                'default': 'IA/Copilot',
            },
            'reference': {'type': 'string', 'description': 'Referencia opcional'},
        },
        'required': ['patient_id', 'amount'],
    },
    category='write',
)
def handle_register_payment(patient_id, amount, method='IA/Copilot', reference='', **kwargs):
    patient = User.query.get(patient_id)
    if not patient:
        return {'error': 'Paciente no encontrado. Usa search_patients para encontrar el ID.'}
    try:
        svc = PaymentService()
        success, result = svc.register_payment(
            patient_id=patient.id,
            amount=float(amount),
            method=method,
            reference=reference or 'Copilot',
            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            discount=0.0,
        )
        if success:
            return {'success': True, 'message': f'Pago de S/. {amount:.2f} registrado para {patient.username}'}
        else:
            return {'error': str(result)}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='create_session',
    description='Crea una sesion para un paciente en una fecha y hora especifica.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'day': {'type': 'string', 'description': 'Fecha YYYY-MM-DD'},
            'time': {'type': 'string', 'description': 'Hora HH:MM'},
            'duration_minutes': {'type': 'integer', 'description': 'Duracion en minutos', 'default': 60},
            'therapist_id': {'type': 'integer', 'description': 'ID del terapeuta (opcional, usa el actual)'},
        },
        'required': ['patient_id', 'day', 'time'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_session(patient_id, day, time, therapist_id=None, duration_minutes=60, notes=None):
    patient = User.query.get(patient_id)
    if not patient:
        return {'error': 'Paciente no encontrado'}
    tid = therapist_id or current_user.id
    start_dt = datetime.strptime(f'{day} {time}', '%Y-%m-%d %H:%M')
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    appt = Appointment(
        therapist_id=tid,
        patient_id=patient_id,
        title=f'Sesion con {patient.username}',
        start_time=start_dt,
        end_time=end_dt,
        status='scheduled',
        notes=notes,
        duration_minutes=duration_minutes,
    )
    db.session.add(appt)
    db.session.commit()
    return {'success': True, 'session_id': appt.id, 'message': f'Sesion creada para {patient.username} el {day} {time}'}


@tool(
    name='update_session',
    description='Actualiza una sesion: cambiar estado, notas, hora.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesion'},
            'status': {'type': 'string', 'description': 'Nuevo estado: scheduled, in_progress, completed, cancelled'},
            'notes': {'type': 'string', 'description': 'Notas actualizadas'},
        },
        'required': ['session_id'],
    },
    category='write',
    roles=ROLES_THERAPIST,
)
def handle_update_session(session_id, status=None, notes=None, **kwargs):
    appt = Appointment.query.get(session_id)
    if not appt:
        return {'error': 'Sesion no encontrada'}
    updated = []
    if status:
        appt.status = status
        updated.append('status')
    if notes is not None:
        appt.notes = notes
        updated.append('notes')
    if updated:
        db.session.commit()
    return {'success': True, 'updated_fields': updated, 'message': f'Sesion {session_id} actualizada'}


@tool(
    name='create_incident',
    description='Crea una incidencia: titulo, descripcion, categoria (TECNICO, OPERATIVO, SERVICIO, SEGURIDAD).',
    parameters={
        'type': 'object',
        'properties': {
            'titulo': {'type': 'string', 'description': 'Titulo de la incidencia'},
            'descripcion': {'type': 'string', 'description': 'Descripcion detallada'},
            'categoria': {'type': 'string', 'description': 'Categoria', 'enum': ['TECNICO', 'OPERATIVO', 'SERVICIO', 'SEGURIDAD']},
            'impacto': {'type': 'integer', 'description': 'Impacto 1=bajo, 2=medio, 3=alto', 'default': 2},
            'urgencia': {'type': 'integer', 'description': 'Urgencia 1=baja, 2=media, 3=alta', 'default': 2},
        },
        'required': ['titulo', 'descripcion', 'categoria'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_incident(titulo, descripcion, categoria, impacto=2, urgencia=2, **kwargs):
    from app.models.incidente import Incidente
    inc = Incidente(
        titulo=titulo,
        descripcion=descripcion,
        categoria=categoria,
        impacto=impacto,
        urgencia=urgencia,
        prioridad=impacto * urgencia,
        estado='NUEVO',
        user_id=current_user.id,
        fecha_creacion=datetime.utcnow(),
        evidencia_original='',
        evidencia_tipo='texto',
    )
    db.session.add(inc)
    db.session.commit()
    return {'success': True, 'incident_id': inc.id_incidente, 'message': f'Incidencia #{inc.id_incidente} creada'}


@tool(
    name='update_patient',
    description='Actualiza datos de un paciente: diagnostico, metas, notas, apoderado.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'preliminary_diagnosis': {'type': 'string', 'description': 'Diagnostico preliminar'},
            'therapy_goals': {'type': 'string', 'description': 'Objetivos de terapia'},
            'notes': {'type': 'string', 'description': 'Notas adicionales'},
            'guardian_name': {'type': 'string', 'description': 'Nombre del apoderado'},
            'guardian_contact': {'type': 'string', 'description': 'Contacto del apoderado'},
        },
        'required': ['patient_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_update_patient(patient_id, **kwargs):
    patient = User.query.get(patient_id)
    if not patient or patient.role != 'jugador':
        return {'error': 'Paciente no encontrado'}
    allowed = {'preliminary_diagnosis', 'therapy_goals', 'notes', 'guardian_name', 'guardian_contact'}
    updated = []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            setattr(patient, k, v)
            updated.append(k)
    if updated:
        db.session.commit()
    return {'success': True, 'updated_fields': updated, 'message': f'Paciente {patient.username} actualizado'}


@tool(
    name='broadcast_message',
    description='Envia un mensaje/notificacion a pacientes, terapeutas, o todos.',
    parameters={
        'type': 'object',
        'properties': {
            'subject': {'type': 'string', 'description': 'Asunto del mensaje'},
            'body': {'type': 'string', 'description': 'Cuerpo del mensaje'},
            'target': {'type': 'string', 'description': 'Destinatarios: all, therapists, patients', 'default': 'all'},
        },
        'required': ['subject', 'body'],
    },
    category='write',
)
def handle_broadcast(subject, body, target='all', **kwargs):
    try:
        resp = _api_post('/api/admin/messages/broadcast', json={'subject': subject, 'body': body, 'target': target})
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}
