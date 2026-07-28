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
    'list_patients',
    'list_users',
    'get_patient_detail',
    'get_user_detail',
    'create_user',
    'update_user',
    'delete_user',
    'assign_therapist',
    'get_sessions',
    'get_sessions_day',
    'create_session',
    'update_session',
    'cancel_session',
    'complete_session',
    'batch_create_sessions',
    'get_financial_summary',
    'get_payment_history',
    'register_payment',
    'get_debtors',
    'send_payment_reminder',
    'create_incident',
    'list_incidents',
    'get_incident_detail',
    'update_incident_status',
    'assign_incident',
    'update_patient',
    'broadcast_message',
    'send_direct_message',
    'get_notifications',
    'mark_notifications_read',
    'list_sedes',
    'get_sede_stats',
    'list_patient_groups',
    'create_patient_group',
    'list_expenses',
    'create_expense',
    'generate_weekly_report',
    'get_weekly_summary',
    'get_monthly_reports',
    'get_therapist_efficiency',
    'get_therapist_financials',
    'list_contracts',
    'get_debt_summary',
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


def execute_tool(name, args, user_id=None, role=None):
    t = TOOL_REGISTRY.get(name)
    if not t:
        return {'error': f'Unknown tool: {name}'}
    required = t['parameters'].get('required', [])
    if required:
        missing = [r for r in required if r not in args or args.get(r) is None or args.get(r) == '']
        if missing:
            return {
                'error': f'Faltan parametros requeridos para {name}: {", ".join(missing)}. '
                f'Usa el formato: <function={name}{{"param1": "valor1"}}' + '</function>'
            }
    try:
        return t['handler'](**args, _user_id=user_id, _role=role)
    except TypeError as e:
        return {
            'error': f'Parametros incorrectos para {name}: {str(e)}. '
            f'Usa el formato: <function={name}{{...}}' + '</function>'
        }
    except Exception as e:
        logger.error(f'Tool {name} error: {e}', exc_info=True)
        return {'error': str(e)}


def _make_auth_cookie(user_id, role=None):
    """Generate a JWT access token cookie for internal API calls."""
    from flask_jwt_extended import create_access_token

    identity = str(user_id) if user_id else '1'
    token = create_access_token(identity=identity)
    return token


def _api_get(endpoint, user_id=None, role=None):
    with current_app.test_client() as c:
        token = _make_auth_cookie(user_id, role)
        c.set_cookie('localhost', 'access_token', token)
        return c.get(endpoint, headers={'Authorization': f'Bearer {token}'})


def _api_post(endpoint, json=None, user_id=None, role=None):
    with current_app.test_client() as c:
        token = _make_auth_cookie(user_id, role)
        c.set_cookie('localhost', 'access_token', token)
        return c.post(endpoint, json=json or {}, headers={'Authorization': f'Bearer {token}'})


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
def handle_search_patients(query=None, limit=10, **kwargs):
    if not query or len(query) < 2:
        return {'error': 'Parametro "query" requerido (minimo 2 caracteres). Ejemplo: search_patients({"query": "nombre"})'}
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
def handle_list_users(role=None, **kwargs):
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
def handle_get_patient_detail(patient_id, **kwargs):
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
def handle_get_sessions(start=None, end=None, therapist_id=None, **kwargs):
    try:
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        if therapist_id:
            params['therapist_id'] = therapist_id
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = _api_get(f'/admin/api/sessions?{qs}', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
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
def handle_financial_summary(**kwargs):
    try:
        resp = _api_get('/admin/api/financial-summary', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
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
def handle_payment_history(patient_id, **kwargs):
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
    description='Registra un pago para un paciente. Antes de registrar, DEBES preguntar: paciente, monto, metodo de pago, y fecha. Si el paciente no tiene ID, usa search_patients primero.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente (usa search_patients si no lo tienes)'},
            'amount': {'type': 'number', 'description': 'Monto en soles'},
            'method': {
                'type': 'string',
                'description': 'Metodo de pago',
                'enum': ['Efectivo', 'Yape', 'Transferencia', 'IA/Copilot'],
            },
            'reference': {'type': 'string', 'description': 'Numero de operacion o referencia'},
            'payment_date': {'type': 'string', 'description': 'Fecha del pago en formato YYYY-MM-DD'},
        },
        'required': ['patient_id', 'amount', 'method', 'payment_date'],
    },
    category='write',
)
def handle_register_payment(patient_id, amount, method, payment_date, reference='', **kwargs):
    patient = User.query.get(patient_id)
    if not patient:
        return {'error': 'Paciente no encontrado. Usa search_patients para encontrar el ID.'}
    try:
        payment_dt = datetime.strptime(payment_date, '%Y-%m-%d') if payment_date else datetime.utcnow()
        svc = PaymentService()
        success, result = svc.register_payment(
            patient_id=patient.id,
            amount=float(amount),
            method=method,
            reference=reference or method,
            next_due_date_str=(payment_dt + timedelta(days=30)).strftime('%Y-%m-%d'),
            discount=0.0,
            payment_date=payment_dt,
        )
        if success:
            return {
                'success': True,
                'message': f'Pago de S/. {amount:.2f} registrado para {patient.username}',
                'patient': patient.username,
                'amount': amount,
                'method': method,
                'date': payment_date,
            }
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
def handle_create_session(patient_id, day, time, therapist_id=None, duration_minutes=60, notes=None, **kwargs):
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
        resp = _api_post('/api/admin/messages/broadcast', json={'subject': subject, 'body': body, 'target': target}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE A: GESTIÓN DE USUARIOS
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='list_patients',
    description='Lista TODOS los pacientes con filtros opcionales: sede, estado activo/inactivo. Retorna lista completa.',
    parameters={
        'type': 'object',
        'properties': {
            'sede_id': {'type': 'integer', 'description': 'Filtrar por ID de sede'},
            'is_active': {'type': 'boolean', 'description': 'true=activos, false=inactivos. Sin filtro = todos'},
            'limit': {'type': 'integer', 'description': 'Max resultados (default 50)'},
        },
    },
    category='read',
)
def handle_list_patients(sede_id=None, is_active=None, limit=50, **kwargs):
    q = User.query.filter_by(role='jugador')
    if sede_id:
        q = q.filter_by(sede_id=sede_id)
    if is_active is not None:
        q = q.filter_by(is_active=is_active)
    patients = q.order_by(User.username).limit(limit).all()
    return {
        'success': True,
        'count': len(patients),
        'patients': [
            {
                'id': p.id, 'username': p.username, 'email': p.email,
                'sede_id': p.sede_id, 'is_active': p.is_active,
                'phone': p.phone, 'sessions_remaining': p.sessions_remaining,
            }
            for p in patients
        ],
    }


@tool(
    name='get_user_detail',
    description='Detalle completo de un usuario (cualquier rol): datos personales, sede, estado, sesiones.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
        },
        'required': ['user_id'],
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_user_detail(user_id, **kwargs):
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    return {
        'success': True,
        'user': {
            'id': user.id, 'username': user.username, 'email': user.email,
            'role': user.role, 'phone': user.phone, 'sex': user.sex,
            'sede_id': user.sede_id, 'is_active': user.is_active,
            'preliminary_diagnosis': user.preliminary_diagnosis,
            'therapy_goals': user.therapy_goals,
            'guardian_name': user.guardian_name,
            'guardian_contact': user.guardian_contact,
            'sessions_total': user.sessions_total,
            'sessions_attended': user.sessions_attended,
            'sessions_remaining': user.sessions_remaining,
        },
    }


@tool(
    name='create_user',
    description='Crea un usuario nuevo (paciente, terapeuta, supervisor).',
    parameters={
        'type': 'object',
        'properties': {
            'username': {'type': 'string', 'description': 'Nombre completo'},
            'email': {'type': 'string', 'description': 'Email unico'},
            'password': {'type': 'string', 'description': 'Contrasena temporal'},
            'role': {'type': 'string', 'enum': ['jugador', 'terapista', 'supervisor', 'admin'], 'description': 'Rol del usuario'},
            'sede_id': {'type': 'integer', 'description': 'ID de sede'},
            'phone': {'type': 'string', 'description': 'Telefono'},
        },
        'required': ['username', 'email', 'password', 'role'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_user(username, email, password, role, sede_id=None, phone=None, **kwargs):
    if User.query.filter_by(email=email).first():
        return {'error': f'Ya existe un usuario con email {email}'}
    try:
        resp = _api_post('/api/admin/create-user', json={
            'username': username, 'email': email, 'password': password,
            'role': role, 'sede_id': sede_id, 'phone': phone,
        }, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Usuario {username} creado como {role}', 'data': data}
        return {'error': data.get('message', 'Error al crear usuario')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='update_user',
    description='Actualiza datos de un usuario: nombre, email, sede, telefono, estado activo.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
            'username': {'type': 'string', 'description': 'Nuevo nombre'},
            'email': {'type': 'string', 'description': 'Nuevo email'},
            'sede_id': {'type': 'integer', 'description': 'Nueva sede'},
            'phone': {'type': 'string', 'description': 'Nuevo telefono'},
            'is_active': {'type': 'boolean', 'description': 'Activar/desactivar'},
        },
        'required': ['user_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_update_user(user_id, username=None, email=None, sede_id=None, phone=None, is_active=None, **kwargs):
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    try:
        payload = {'user_id': user_id}
        if username: payload['username'] = username
        if email: payload['email'] = email
        if sede_id: payload['sede_id'] = sede_id
        if phone: payload['phone'] = phone
        if is_active is not None: payload['is_active'] = is_active
        resp = _api_post('/api/admin/update-user', json=payload, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Usuario {user.username} actualizado', 'data': data}
        return {'error': data.get('message', 'Error al actualizar')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='delete_user',
    description='Elimina un usuario del sistema. Requiere confirmacion.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario a eliminar'},
        },
        'required': ['user_id'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_delete_user(user_id, **kwargs):
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    try:
        resp = _api_post('/api/admin/delete-user', json={'user_id': user_id}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Usuario {user.username} eliminado'}
        return {'error': data.get('message', 'Error al eliminar')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='assign_therapist',
    description='Asigna un terapeuta a un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'therapist_id': {'type': 'integer', 'description': 'ID del terapeuta'},
        },
        'required': ['patient_id', 'therapist_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_assign_therapist(patient_id, therapist_id, **kwargs):
    try:
        resp = _api_post('/api/admin/assign-therapist', json={
            'patient_id': patient_id, 'therapist_id': therapist_id,
        }, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': 'Terapeuta asignado correctamente', 'data': data}
        return {'error': data.get('message', 'Error al asignar')}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE C: SESIONES AVANZADAS
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='get_sessions_day',
    description='Sesiones de un dia especifico. Retorna todas las sesiones de esa fecha.',
    parameters={
        'type': 'object',
        'properties': {
            'date': {'type': 'string', 'description': 'Fecha YYYY-MM-DD (default: hoy)'},
        },
    },
    category='read',
)
def handle_get_sessions_day(date=None, **kwargs):
    try:
        target = date or datetime.utcnow().strftime('%Y-%m-%d')
        resp = _api_get(f'/api/sessions/day?date={target}', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'date': target, 'count': len(data) if isinstance(data, list) else 0, 'sessions': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='cancel_session',
    description='Cancela una sesion existente.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesion'},
        },
        'required': ['session_id'],
    },
    category='write',
    roles=ROLES_THERAPIST,
)
def handle_cancel_session(session_id, **kwargs):
    try:
        resp = _api_post(f'/api/sessions/{session_id}/cancel', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Sesion {session_id} cancelada'}
        return {'error': data.get('message', 'Error al cancelar sesion')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='complete_session',
    description='Marca una sesion como completada y actualiza estadisticas del paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesion'},
        },
        'required': ['session_id'],
    },
    category='write',
    roles=ROLES_THERAPIST,
)
def handle_complete_session(session_id, **kwargs):
    try:
        resp = _api_post(f'/api/sessions/{session_id}/complete', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Sesion {session_id} completada'}
        return {'error': data.get('message', 'Error al completar sesion')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='batch_create_sessions',
    description='Crea multiples sesiones de una vez. Utile para programar la semana.',
    parameters={
        'type': 'object',
        'properties': {
            'sessions': {
                'type': 'array',
                'description': 'Lista de sesiones a crear',
                'items': {
                    'type': 'object',
                    'properties': {
                        'patient_id': {'type': 'integer'},
                        'day': {'type': 'string', 'description': 'YYYY-MM-DD'},
                        'time': {'type': 'string', 'description': 'HH:MM'},
                        'therapist_id': {'type': 'integer'},
                        'duration_minutes': {'type': 'integer', 'default': 60},
                    },
                    'required': ['patient_id', 'day', 'time'],
                },
            },
        },
        'required': ['sessions'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_batch_create_sessions(sessions=None, **kwargs):
    if not sessions:
        return {'error': 'Se requiere una lista de sesiones'}
    try:
        resp = _api_post('/admin/api/sessions/batch', json={'sessions': sessions}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'{len(sessions)} sesiones creadas', 'data': data}
        return {'error': data.get('message', 'Error al crear sesiones')}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE B: INCIDENCIAS
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='list_incidents',
    description='Lista incidencias con filtros opcionales.',
    parameters={
        'type': 'object',
        'properties': {
            'status': {'type': 'string', 'description': 'Filtrar por estado: NUEVO, EN_PROCESO, RESUELTO, CERRADO'},
            'limit': {'type': 'integer', 'description': 'Max resultados (default 20)'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_list_incidents(status=None, limit=20, **kwargs):
    try:
        params = f'?per_page={limit}'
        if status:
            params += f'&estado={status}'
        resp = _api_get(f'/api/incidents{params}', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'incidents': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_incident_detail',
    description='Detalle completo de una incidencia incluyendo comentarios.',
    parameters={
        'type': 'object',
        'properties': {
            'incident_id': {'type': 'integer', 'description': 'ID de la incidencia'},
        },
        'required': ['incident_id'],
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_incident_detail(incident_id, **kwargs):
    try:
        resp = _api_get(f'/api/incidents/{incident_id}', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'incident': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='update_incident_status',
    description='Cambia el estado de una incidencia.',
    parameters={
        'type': 'object',
        'properties': {
            'incident_id': {'type': 'integer', 'description': 'ID de la incidencia'},
            'status': {'type': 'string', 'enum': ['NUEVO', 'EN_PROCESO', 'RESUELTO', 'CERRADO'], 'description': 'Nuevo estado'},
        },
        'required': ['incident_id', 'status'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_update_incident_status(incident_id, status, **kwargs):
    try:
        resp = _api_post(f'/api/incidents/{incident_id}/status', json={'status': status}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Incidencia #{incident_id} actualizada a {status}'}
        return {'error': data.get('message', 'Error al actualizar incidencia')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='assign_incident',
    description='Asigna o reasigna una incidencia a un usuario.',
    parameters={
        'type': 'object',
        'properties': {
            'incident_id': {'type': 'integer', 'description': 'ID de la incidencia'},
            'assignee_id': {'type': 'integer', 'description': 'ID del usuario asignado'},
        },
        'required': ['incident_id', 'assignee_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_assign_incident(incident_id, assignee_id, **kwargs):
    try:
        resp = _api_post(f'/api/incidents/{incident_id}/assign', json={'assignee_id': assignee_id}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Incidencia #{incident_id} asignada'}
        return {'error': data.get('message', 'Error al asignar incidencia')}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE D: SEDES Y GRUPOS
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='list_sedes',
    description='Lista todas las sedes del centro.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_list_sedes(**kwargs):
    try:
        resp = _api_get('/api/admin/sedes', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'sedes': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_sede_stats',
    description='Estadisticas de una sede: pacientes, terapeutas, sesiones, ingresos.',
    parameters={
        'type': 'object',
        'properties': {
            'sede_id': {'type': 'integer', 'description': 'ID de la sede (opcional, todas si se omite)'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_sede_stats(sede_id=None, **kwargs):
    try:
        url = '/api/admin/sedes/stats'
        if sede_id:
            url += f'?sede_id={sede_id}'
        resp = _api_get(url, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'stats': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='list_patient_groups',
    description='Lista grupos de pacientes (ej: "Talara", "Lima Norte").',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_list_patient_groups(**kwargs):
    try:
        resp = _api_get('/api/admin/patient-groups', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'groups': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='create_patient_group',
    description='Crea un grupo de pacientes nuevo.',
    parameters={
        'type': 'object',
        'properties': {
            'name': {'type': 'string', 'description': 'Nombre del grupo'},
            'description': {'type': 'string', 'description': 'Descripcion del grupo'},
        },
        'required': ['name'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_patient_group(name, description='', **kwargs):
    try:
        resp = _api_post('/api/admin/patient-groups', json={'name': name, 'description': description}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Grupo "{name}" creado', 'data': data}
        return {'error': data.get('message', 'Error al crear grupo')}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE E: FINANZAS
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='get_debtors',
    description='Reporte de deudores por sede. Pacientes con pagos pendientes.',
    parameters={
        'type': 'object',
        'properties': {
            'month': {'type': 'string', 'description': 'Mes YYYY-MM (default: todos)'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_debtors(month=None, **kwargs):
    try:
        url = '/api/admin/deudores'
        if month:
            url += f'?month={month}'
        resp = _api_get(url, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'debtors': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='send_payment_reminder',
    description='Envia un recordatorio de pago a un paciente por email/WhatsApp.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_send_payment_reminder(patient_id, **kwargs):
    try:
        resp = _api_post('/api/admin/send-payment-reminder', json={'patient_id': patient_id}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': 'Recordatorio enviado', 'data': data}
        return {'error': data.get('message', 'Error al enviar recordatorio')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='list_expenses',
    description='Lista gastos del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'month': {'type': 'string', 'description': 'Mes YYYY-MM (default: actual)'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_list_expenses(month=None, **kwargs):
    try:
        url = '/admin/api/expenses'
        if month:
            url += f'?month={month}'
        resp = _api_get(url, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'expenses': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='create_expense',
    description='Registra un gasto del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'description': {'type': 'string', 'description': 'Descripcion del gasto'},
            'amount': {'type': 'number', 'description': 'Monto en soles'},
            'category': {'type': 'string', 'description': 'Categoria: alquiler, servicios, suministros, personal, otro'},
        },
        'required': ['description', 'amount'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_create_expense(description, amount, category='otro', **kwargs):
    try:
        resp = _api_post('/admin/api/expenses/create', json={
            'description': description, 'amount': float(amount), 'category': category,
        }, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Gasto de S/. {amount:.2f} registrado', 'data': data}
        return {'error': data.get('message', 'Error al registrar gasto')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_therapist_financials',
    description='Resumen financiero por terapeuta: sesiones, pagos, eficiencia.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_therapist_financials(**kwargs):
    try:
        resp = _api_get('/admin/api/therapist-financials', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE F: REPORTES
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='generate_weekly_report',
    description='Genera reporte semanal de un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='write',
    roles=ROLES_THERAPIST,
)
def handle_generate_weekly_report(patient_id, **kwargs):
    try:
        resp = _api_post('/api/reports/generate-weekly', json={'patient_id': patient_id}, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': 'Reporte semanal generado', 'data': data}
        return {'error': data.get('message', 'Error al generar reporte')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_weekly_summary',
    description='Resumen semanal del centro: sesiones, pagos, pacientes activos.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_weekly_summary(**kwargs):
    try:
        resp = _api_get('/api/weekly-summary', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'summary': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_monthly_reports',
    description='Reportes mensuales acumulados del centro.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_monthly_reports(**kwargs):
    try:
        resp = _api_get('/api/reports/monthly', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'reports': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_therapist_efficiency',
    description='Metricas de eficiencia de terapeutas: asistencia, puntualidad, resultados.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_therapist_efficiency(**kwargs):
    try:
        resp = _api_get('/api/therapist/efficiency', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'efficiency': data}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE G: MENSAJERÍA Y NOTIFICACIONES
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='send_direct_message',
    description='Envia un mensaje directo a un usuario especifico.',
    parameters={
        'type': 'object',
        'properties': {
            'receiver_id': {'type': 'integer', 'description': 'ID del destinatario'},
            'content': {'type': 'string', 'description': 'Mensaje a enviar'},
        },
        'required': ['receiver_id', 'content'],
    },
    category='write',
)
def handle_send_direct_message(receiver_id, content, **kwargs):
    try:
        resp = _api_post('/api/messages/send', json={
            'receiver_id': receiver_id, 'content': content,
        }, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': 'Mensaje enviado', 'data': data}
        return {'error': data.get('message', 'Error al enviar mensaje')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_notifications',
    description='Lista notificaciones del usuario actual.',
    parameters={
        'type': 'object',
        'properties': {
            'category': {'type': 'string', 'description': 'Filtrar por categoria'},
        },
    },
    category='read',
)
def handle_get_notifications(category=None, **kwargs):
    try:
        url = '/api/notifications'
        if category:
            url += f'/category/{category}'
        resp = _api_get(url, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'notifications': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='mark_notifications_read',
    description='Marca todas las notificaciones como leidas.',
    parameters={'type': 'object', 'properties': {}},
    category='write',
)
def handle_mark_notifications_read(**kwargs):
    try:
        resp = _api_post('/api/notifications/mark-read', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'message': 'Notificaciones marcadas como leidas'}
    except Exception as e:
        return {'error': str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# FASE H: CONTRATOS
# ═══════════════════════════════════════════════════════════════════════════════


@tool(
    name='list_contracts',
    description='Lista contratos del centro.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_list_contracts(**kwargs):
    try:
        resp = _api_get('/admin/api/contracts', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'contracts': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_debt_summary',
    description='Resumen de deudas: total pendiente, por sede, por paciente.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_debt_summary(**kwargs):
    try:
        resp = _api_get('/admin/api/debt-summary', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
        data = resp.get_json() if resp else {}
        return {'success': True, 'summary': data}
    except Exception as e:
        return {'error': str(e)}
