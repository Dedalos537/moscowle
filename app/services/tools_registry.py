import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app

from app.auth_compat import current_user
from app.extensions import bcrypt, db
from app.models import Appointment, Payment, User
from app.services.appointment_service import AppointmentService
from app.services.contract_service import ContractService
from app.services.email_service import EmailService
from app.services.payment_service import PaymentService
from app.utils.sanitizer import sanitize_text

ROLES_ADMIN = {'admin'}
ROLES_SUPERVISOR = {'admin', 'supervisor'}
ROLES_THERAPIST = {'admin', 'supervisor', 'terapista'}
ROLES_ALL = {'admin', 'supervisor', 'terapista', 'jugador'}

logger = logging.getLogger('app')

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

LIMA_TZ = ZoneInfo('America/Lima')


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


# Write tools that are safe to run without an explicit confirmation gate.
SAFE_WRITE_TOOLS = {'mark_notifications_read', 'generate_weekly_report'}


def _today_lima():
    return datetime.now(LIMA_TZ).strftime('%Y-%m-%d')


@tool(
    name='get_server_logs',
    description='Lee las últimas líneas de los logs del servidor para diagnosticar errores (ej: 404, 500). Solo para administradores.',
    parameters={
        'type': 'object',
        'properties': {
            'lines': {'type': 'integer', 'description': 'Cantidad de líneas a leer (default: 100)', 'default': 100},
        },
    },
    category='read',
    roles=ROLES_ADMIN,
)
def handle_get_server_logs(lines=100, **kwargs):
    import subprocess

    try:
        # Intentamos leer via journalctl (estándar en Ubuntu para servicios systemd)
        # Asumimos que el servicio se llama 'moscowle'
        result = subprocess.run(  # noqa: S603
            ['journalctl', '-u', 'moscowle', '-n', str(lines), '--no-pager'],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.stdout:
            return {'success': True, 'logs': result.stdout}

        # Fallback: intentar leer syslog si journalctl falló o no devolvió nada
        with open('/var/log/syslog') as f:
            content = f.readlines()
            return {'success': True, 'logs': ''.join(content[-lines:])}
    except Exception as e:
        return {'error': f'No se pudieron leer los logs: {str(e)}'}


def _valid_date(value):
    return bool(DATE_RE.match(str(value)))


def _last_day_of_month(year, month):
    next_month = datetime(year, month, 1) + timedelta(days=31)
    return (next_month.replace(day=1) - timedelta(days=1)).day


# No change here, just removing the old definition block


CORE_TOOL_NAMES = [
    'search_patients',
    'list_patients',
    'list_users',
    'get_therapist_patients',
    'get_patient_detail',
    'get_user_detail',
    'create_user',
    'create_full_patient',
    'update_patient_profile',
    'delete_user',
    'assign_therapist',
    'assign_therapist_to_sede',
    'get_current_datetime',
    'get_sessions',
    'get_sessions_day',
    'schedule_programmed_session',
    'update_session_plan',
    'cancel_session',
    'complete_session',
    'batch_create_sessions',
    'get_financial_summary',
    'get_payment_history',
    'register_payment',
    'cancel_payment',
    'edit_payment',
    'get_debtors',
    'send_payment_reminder',
    'compare_periods',
    'get_user_growth',
    'toggle_user_status',
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
    'create_service_contract',
    'get_contract_detail',
    'get_contracts_filtered',
    'get_due_installments',
    'update_contract',
    'register_payment_with_evidence',
    'cancel_contract',
    'reactivate_contract',
    'get_monthly_collection',
    'get_upcoming_installments',
    'get_patient_stats',
    'update_patient_details',
    'get_server_logs',
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
        tools.append(
            {
                'type': 'function',
                'function': {
                    'name': t['name'],
                    'description': t['description'],
                    'parameters': t['parameters'],
                },
            }
        )
    return tools


def execute_tool(name, args, user_id=None, role=None):
    t = TOOL_REGISTRY.get(name)
    if not t:
        return {'error': f'Unknown tool: {name}'}
    if role and t.get('roles') and role not in t['roles']:
        return {
            'error': f'No tienes permisos ({role}) para usar {name}. Acceso requerido: {", ".join(sorted(t["roles"]))}.'
        }
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


def _api_put(endpoint, json=None, user_id=None, role=None):
    with current_app.test_client() as c:
        token = _make_auth_cookie(user_id, role)
        c.set_cookie('localhost', 'access_token', token)
        return c.put(endpoint, json=json or {}, headers={'Authorization': f'Bearer {token}'})


@tool(
    name='search_patients',
    description='Busca pacientes por nombre o email. Retorna lista con ID y nombre, e incluye el terapeuta asignado.',
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
        return {
            'error': 'Parametro "query" requerido (minimo 2 caracteres). Ejemplo: search_patients({"query": "nombre"})'
        }
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
            {
                'id': p.id,
                'username': p.username,
                'email': p.email,
                'role': p.role,
                'assigned_therapist_id': p.assigned_therapist_id,
                'assigned_therapist': p.assigned_therapist.username if p.assigned_therapist else None,
                'sede_id': p.sede_id,
            }
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
    name='get_therapist_patients',
    description=(
        'Cantidad y lista de pacientes (jugadores) que tiene asignados un terapeuta. '
        'Uso tipico: "cuantos usuarios tiene el terapeuta Milagros" '
        '-> get_therapist_patients({"therapist_name": "Milagros"})'
    ),
    parameters={
        'type': 'object',
        'properties': {
            'therapist_name': {
                'type': 'string',
                'description': 'Nombre o email del terapeuta (minimo 2 caracteres)',
            },
        },
        'required': ['therapist_name'],
    },
    category='read',
    roles=ROLES_SUPERVISOR | {'terapista'},
)
def handle_get_therapist_patients(therapist_name=None, **kwargs):
    name = (str(therapist_name or '')).strip()
    if len(name) < 2:
        return {
            'error': 'Parametro "therapist_name" requerido (minimo 2 caracteres). '
            'Ejemplo: get_therapist_patients({"therapist_name": "Milagros"})'
        }
    therapist = User.query.filter(
        User.role == 'terapista',
        db.or_(User.username.ilike(f'%{name}%'), User.email.ilike(f'%{name}%')),
    ).first()
    if not therapist:
        return {'error': 'No se encontro un terapeuta con ese nombre.'}
    patients = (
        User.query.filter_by(role='jugador', assigned_therapist_id=therapist.id, is_active=True)
        .order_by(User.username)
        .all()
    )
    return {
        'success': True,
        'therapist': {'id': therapist.id, 'username': therapist.username, 'email': therapist.email},
        'count': len(patients),
        'patients': [{'id': p.id, 'username': p.username, 'email': p.email} for p in patients],
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
    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return {
            'error': 'patient_id debe ser un número entero (el ID del paciente). '
            'Para buscar un paciente por su nombre usa SIEMPRE search_patients({"query": "nombre"}) y toma el id de su resultado.'
        }
    patient = User.query.get(patient_id)
    if not patient or patient.role != 'jugador':
        return {'error': 'Paciente no encontrado'}
    age = None
    if patient.date_of_birth:
        today = datetime.now(LIMA_TZ).date()
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
            'assigned_therapist_id': patient.assigned_therapist_id,
            'assigned_therapist': patient.assigned_therapist.username if patient.assigned_therapist else None,
            'sessions_total': patient.sessions_total,
            'sessions_attended': patient.sessions_attended,
            'sessions_remaining': patient.sessions_remaining,
        },
        'recent_sessions': [
            {'id': s.id, 'start_time': str(s.start_time), 'status': s.status, 'title': s.title} for s in sessions
        ],
        'recent_payments': [
            {'id': p.id, 'amount': float(p.amount), 'date': str(p.date), 'method': p.method} for p in payments
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
        if start is not None and not _valid_date(start):
            return {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}
        if end is not None and not _valid_date(end):
            return {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}
        if not start and not end:
            now = datetime.now(LIMA_TZ)
            start = now.strftime('%Y-%m-01')
            end = now.strftime(f'%Y-%m-{_last_day_of_month(now.year, now.month)}')
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
    description='Resumen financiero del mes: ingresos, egresos, ganancia, cobranza. Puede consultar cualquier mes.',
    parameters={
        'type': 'object',
        'properties': {
            'month': {'type': 'integer', 'description': 'Mes (1-12). Default: mes actual'},
            'year': {'type': 'integer', 'description': 'Ano (ej: 2026). Default: ano actual'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_financial_summary(month=None, year=None, **kwargs):
    try:
        url = '/admin/api/financial-summary'
        params = []
        if month:
            params.append(f'month={month}')
        if year:
            params.append(f'year={year}')
        if params:
            url += '?' + '&'.join(params)
        resp = _api_get(url, user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
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
            'receipt_url': {
                'type': 'string',
                'description': 'Ruta o URL del voucher/comprobante de pago (ej: vouchers/xxx.jpg)',
            },
        },
        'required': ['patient_id', 'amount', 'method', 'payment_date'],
    },
    category='write',
)
def handle_register_payment(patient_id, amount, method, payment_date, reference='', **kwargs):
    patient = User.query.get(patient_id) if patient_id else None
    if not patient and kwargs.get('patient_name'):
        from sqlalchemy import or_

        name = str(kwargs['patient_name']).strip().lower()
        patient = User.query.filter(
            or_(
                User.username.ilike(f'%{name}%'),
                User.name.ilike(f'%{name}%'),
            )
        ).first()
    if not patient:
        return {'error': 'Paciente no encontrado. Usa search_patients para encontrar el ID.'}
    try:
        try:
            payment_dt = datetime.strptime(payment_date, '%Y-%m-%d') if payment_date else datetime.now(LIMA_TZ)
        except ValueError:
            payment_dt = datetime.now(LIMA_TZ)
        svc = PaymentService()
        success, result = svc.register_payment(
            patient_id=patient.id,
            amount=float(amount),
            method=method,
            reference=reference or method,
            next_due_date_str=(payment_dt + timedelta(days=30)).strftime('%Y-%m-%d'),
            discount=0.0,
            payment_date=payment_dt,
            receipt_path=kwargs.get('receipt_url'),
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
    name='cancel_payment',
    description='Elimina un pago registrado. Requiere el ID del pago (usa get_payment_history para encontrarlo). Confirma con el usuario antes de eliminar.',
    parameters={
        'type': 'object',
        'properties': {
            'payment_id': {
                'type': 'integer',
                'description': 'ID del pago a eliminar (usa get_payment_history para encontrarlo)',
            },
        },
        'required': ['payment_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_cancel_payment(payment_id, **kwargs):
    try:
        resp = _api_post(
            f'/admin/api/payments/delete/{payment_id}', user_id=kwargs.get('_user_id'), role=kwargs.get('_role')
        )
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': data.get('message', 'Pago eliminado')}
        return {'error': data.get('error', 'Error al eliminar pago')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='edit_payment',
    description='Modifica un pago existente. Puede cambiar monto, metodo, fecha o estado. Usa get_payment_history para encontrar el ID.',
    parameters={
        'type': 'object',
        'properties': {
            'payment_id': {'type': 'integer', 'description': 'ID del pago a modificar'},
            'amount': {'type': 'number', 'description': 'Nuevo monto (opcional)'},
            'method': {'type': 'string', 'description': 'Nuevo metodo: Efectivo, Yape, Plin, Transferencia (opcional)'},
            'payment_date': {'type': 'string', 'description': 'Nueva fecha YYYY-MM-DD (opcional)'},
            'status': {'type': 'string', 'description': 'Nuevo estado: pendiente, completado, cancelado (opcional)'},
            'description': {'type': 'string', 'description': 'Nueva descripcion (opcional)'},
            'receipt_url': {'type': 'string', 'description': 'URL del comprobante de pago (opcional)'},
        },
        'required': ['payment_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_edit_payment(payment_id, **kwargs):
    try:
        updates = {}
        for field in ('amount', 'method', 'payment_date', 'status', 'description', 'receipt_url'):
            if field in kwargs and kwargs[field] is not None:
                updates[field] = kwargs[field]
        if not updates:
            return {
                'error': 'No hay campos para actualizar. Proporcione amount, method, payment_date, status, description o receipt_url.'
            }
        resp = _api_put(
            f'/admin/api/payments/{payment_id}', json=updates, user_id=kwargs.get('_user_id'), role=kwargs.get('_role')
        )
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': data.get('message', 'Pago actualizado'), 'payment': data.get('payment')}
        return {'error': data.get('error', 'Error al actualizar pago')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='toggle_user_status',
    description='Cambia el estado de un usuario: activar, desactivar, marcar como retirado o deudor.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
            'status': {
                'type': 'string',
                'description': 'Nuevo estado',
                'enum': ['active', 'inactive', 'retired', 'debtor'],
            },
        },
        'required': ['user_id', 'status'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_toggle_user_status(user_id, status, **kwargs):
    try:
        resp = _api_post(
            f'/admin/api/users/{user_id}/toggle-status',
            json={'status': status},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {
                'success': True,
                'message': data.get('message', 'Estado actualizado'),
                'old_status': data.get('old_status'),
                'new_status': data.get('new_status'),
            }
        return {'error': data.get('error', 'Error al cambiar estado')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='schedule_programmed_session',
    description='Programa una sesión con un plan terapéutico: incluye fecha, hora, notas de programación y una lista de juegos asignados.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'therapist_id': {'type': 'integer', 'description': 'ID del terapeuta'},
            'start_time': {'type': 'string', 'description': 'Fecha y hora de inicio YYYY-MM-DD HH:MM'},
            'title': {'type': 'string', 'description': 'Título de la sesión (opcional)'},
            'programming_notes': {'type': 'string', 'description': 'Notas de programación y objetivos de la sesión'},
            'games_list': {
                'type': 'array',
                'items': {'type': 'string', 'description': 'Nombre del archivo del juego (ej: "memoria_colores.html")'},
                'description': 'Lista de juegos a asignar a la sesión',
            },
            'duration_minutes': {'type': 'integer', 'description': 'Duración en minutos', 'default': 60},
        },
        'required': ['patient_id', 'therapist_id', 'start_time', 'programming_notes', 'games_list'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_schedule_programmed_session(patient_id, therapist_id, start_time, programming_notes, games_list, **kwargs):
    try:
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        duration = kwargs.get('duration_minutes', 60)
        end_dt = start_dt + timedelta(minutes=duration)

        therapist = User.query.get(therapist_id)
        if not therapist:
            return {'error': 'Terapeuta no encontrado'}

        svc = AppointmentService()
        data = {
            'patient_id': patient_id,
            'start_time': start_dt,
            'end_time': end_dt,
            'title': kwargs.get('title'),
            'notes': programming_notes,
            'games': games_list,
        }

        appt = svc.create_session(therapist_id, data, therapist.username)

        return {
            'success': True,
            'session_id': appt.id,
            'message': f'Sesión programada con éxito para el paciente ID {patient_id} el {start_time}, con {len(games_list)} juegos asignados.',
        }
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='update_session_plan',
    description='Actualiza el plan de una sesión existente: cambia las notas de programación y/o la lista de juegos.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesión'},
            'new_notes': {'type': 'string', 'description': 'Nuevas notas de programación'},
            'new_games': {
                'type': 'array',
                'items': {'type': 'string', 'description': 'Nombre del archivo del juego'},
                'description': 'Nueva lista de juegos asignados',
            },
        },
        'required': ['session_id'],
    },
    category='write',
    roles=ROLES_THERAPIST,
)
def handle_update_session_plan(session_id, **kwargs):
    try:
        svc = AppointmentService()
        updated = []

        # Update notes
        if 'new_notes' in kwargs and kwargs['new_notes'] is not None:
            svc.update_session(session_id, {'notes': kwargs['new_notes']})
            updated.append('notes')

        # Update games
        if 'new_games' in kwargs and kwargs['new_games'] is not None:
            svc.set_session_games(session_id, kwargs['new_games'])
            updated.append('games')

        if not updated:
            return {'error': 'No se proporcionaron notas ni juegos para actualizar'}

        return {
            'success': True,
            'message': f'Plan de la sesión {session_id} actualizado correctamente.',
            'updated': updated,
        }
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='create_incident',
    description='Crea una incidencia: titulo, descripcion, categoria (TECNICO, OPERATIVO, SERVICIO, SEGURIDAD).',
    parameters={
        'type': 'object',
        'properties': {
            'titulo': {'type': 'string', 'description': 'Titulo de la incidencia'},
            'descripcion': {'type': 'string', 'description': 'Descripcion detallada'},
            'categoria': {
                'type': 'string',
                'description': 'Categoria',
                'enum': ['TECNICO', 'OPERATIVO', 'SERVICIO', 'SEGURIDAD'],
            },
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
        resp = _api_post(
            '/api/admin/messages/broadcast',
            json={'subject': subject, 'body': body, 'target': target},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
                'id': p.id,
                'username': p.username,
                'email': p.email,
                'sede_id': p.sede_id,
                'is_active': p.is_active,
                'phone': p.phone,
                'sessions_remaining': p.sessions_remaining,
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
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'phone': user.phone,
            'sex': user.sex,
            'sede_id': user.sede_id,
            'is_active': user.is_active,
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
    name='create_full_patient',
    description='Registra un paciente nuevo con perfil completo: datos personales, DNI, apoderado y metas. Crea la cuenta y el perfil en un solo paso.',
    parameters={
        'type': 'object',
        'properties': {
            'username': {'type': 'string', 'description': 'Nombre completo'},
            'email': {'type': 'string', 'description': 'Email (opcional, si se omite se crea cuenta presencial)'},
            'password': {'type': 'string', 'description': 'Contrasena temporal (opcional)'},
            'role': {'type': 'string', 'description': 'Rol (siempre jugador)', 'default': 'jugador'},
            'sede_id': {'type': 'integer', 'description': 'ID de la sede'},
            'phone': {'type': 'string', 'description': 'Telefono'},
            'document_number': {'type': 'string', 'description': 'DNI del paciente'},
            'date_of_birth': {'type': 'string', 'description': 'Fecha de nacimiento YYYY-MM-DD'},
            'sex': {'type': 'string', 'description': 'Sexo (M/F/Otro)'},
            'guardian_name': {'type': 'string', 'description': 'Nombre del apoderado'},
            'guardian_type': {'type': 'string', 'description': 'Tipo de apoderado (padre/madre/tutor/otro)'},
            'guardian_dni': {'type': 'string', 'description': 'DNI del apoderado'},
            'guardian_contact': {'type': 'string', 'description': 'Contacto del apoderado'},
            'preliminary_diagnosis': {'type': 'string', 'description': 'Diagnostico preliminar'},
            'therapy_goals': {'type': 'string', 'description': 'Objetivos de terapia'},
            'notes': {'type': 'string', 'description': 'Notas adicionales'},
            'assigned_therapist_id': {'type': 'integer', 'description': 'ID del terapeuta asignado'},
        },
        'required': ['username', 'sede_id', 'assigned_therapist_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_full_patient(username, sede_id, assigned_therapist_id, **kwargs):
    import uuid

    email = (kwargs.get('email') or '').strip().lower()
    password = kwargs.get('password')

    is_full_account = False
    if not email:
        email = f'noemail_{uuid.uuid4().hex[:8]}@local'
        password = uuid.uuid4().hex
        is_full_account = False
    else:
        # Basic validation
        password = password or EmailService.generate_password()
        is_full_account = True

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        new_patient = User(
            username=username,
            email=email,
            password=hashed_pw,
            role='jugador',
            is_active=is_full_account,
            sede_id=sede_id,
            phone=sanitize_text(kwargs.get('phone', ''), 20),
            assigned_therapist_id=assigned_therapist_id,
            document_number=sanitize_text(kwargs.get('document_number', ''), 15),
            date_of_birth=datetime.strptime(kwargs['date_of_birth'], '%Y-%m-%d').date()
            if kwargs.get('date_of_birth')
            else None,
            sex=sanitize_text(kwargs.get('sex', ''), 20),
            guardian_name=sanitize_text(kwargs.get('guardian_name', ''), 200),
            guardian_type=sanitize_text(kwargs.get('guardian_type', ''), 50),
            guardian_dni=sanitize_text(kwargs.get('guardian_dni', ''), 15),
            guardian_contact=sanitize_text(kwargs.get('guardian_contact', ''), 200),
            preliminary_diagnosis=sanitize_text(kwargs.get('preliminary_diagnosis', ''), 2000),
            therapy_goals=sanitize_text(kwargs.get('therapy_goals', ''), 2000),
            notes=sanitize_text(kwargs.get('notes', ''), 2000),
        )
        new_patient.login_code = User.generate_login_code('jugador')

        # therapist relationship
        therapist = User.query.get(assigned_therapist_id)
        if therapist:
            new_patient.therapists.append(therapist)

        db.session.add(new_patient)
        db.session.commit()

        if is_full_account:
            EmailService.send_welcome_email(email, password, new_patient.username)

        return {
            'success': True,
            'patient_id': new_patient.id,
            'username': new_patient.username,
            'message': f'Paciente {new_patient.username} creado con perfil completo.',
            'credentials': {'email': email, 'password': password} if is_full_account else None,
        }
    except Exception as e:
        db.session.rollback()
        return {'error': str(e)}


@tool(
    name='create_user',
    description='Crea un usuario nuevo en el sistema (rol: admin, supervisor, terapista o jugador). Tipico para registrar un paciente (rol jugador) o un terapeuta. Si se provee email, la cuenta queda activa y se envia clave temporal por email.',
    parameters={
        'type': 'object',
        'properties': {
            'username': {'type': 'string', 'description': 'Nombre completo del usuario'},
            'email': {'type': 'string', 'description': 'Email (si se omite, se crea cuenta presencial sin acceso)'},
            'role': {
                'type': 'string',
                'description': "Rol: admin, supervisor, terapista o jugador (si dicen 'paciente' usar jugador)",
            },
            'phone': {'type': 'string', 'description': 'Telefono (opcional)'},
            'sede_id': {'type': 'integer', 'description': 'ID de la sede (opcional)'},
            'guardian': {'type': 'string', 'description': 'Nombre del apoderado (si es menor, opcional)'},
        },
        'required': ['username', 'role'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_user(username, role, email=None, **kwargs):
    from app.services.admin_service import AdminService

    ROLE_ALIASES = {'paciente': 'jugador'}
    role = (role or '').strip().lower()
    role = ROLE_ALIASES.get(role, role)
    if role not in ROLES_ALL:
        return {'error': f'Rol invalido: {role}. Roles validos: admin, supervisor, terapista o jugador (paciente).'}

    if not username or not str(username).strip():
        return {'error': 'El nombre (username) es obligatorio para crear el usuario.'}

    svc = AdminService()
    ok, result = svc.create_user(
        {
            'username': str(username).strip(),
            'email': (email or '').strip() or None,
            'role': role,
            'phone': (kwargs.get('phone') or '').strip() or None,
            'guardian': (kwargs.get('guardian') or '').strip() or None,
            'sede_id': kwargs.get('sede_id'),
        }
    )
    if not ok:
        return {'error': str(result)}

    user = result['user']
    return {
        'success': True,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'temp_password': result.get('temp_password'),
        'contract_created': result.get('contract_created', False),
        'message': f'Usuario {user.username} creado correctamente (ID: {user.id}).',
    }


@tool(
    name='get_current_datetime',
    description='Devuelve la fecha y hora actuales del centro en la zona horaria de Lima (America/Lima). Usa esta herramienta SIEMPRE que el usuario pregunte qué hora es, qué fecha es, qué día es hoy o cuánto falta para algo. Nunca calcules ni adivines la hora.',
    parameters={'type': 'object', 'properties': {}, 'required': []},
    category='read',
    roles=ROLES_ALL,
)
def handle_get_current_datetime(**kwargs):
    now = datetime.now(LIMA_TZ)
    day_names = {
        'Monday': 'lunes',
        'Tuesday': 'martes',
        'Wednesday': 'miércoles',
        'Thursday': 'jueves',
        'Friday': 'viernes',
        'Saturday': 'sábado',
        'Sunday': 'domingo',
    }
    return {
        'fecha': now.strftime('%Y-%m-%d'),
        'hora': now.strftime('%H:%M'),
        'fecha_hora': now.strftime('%Y-%m-%d %H:%M'),
        'dia_semana': day_names.get(now.strftime('%A'), now.strftime('%A')),
        'zona': 'America/Lima',
    }


@tool(
    name='update_patient_profile',
    description='Actualiza el perfil detallado de un paciente: DNI, datos del apoderado, diagnostico y metas.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'document_number': {'type': 'string', 'description': 'DNI del paciente'},
            'phone': {'type': 'string', 'description': 'Telefono'},
            'date_of_birth': {'type': 'string', 'description': 'Fecha de nacimiento YYYY-MM-DD'},
            'sex': {'type': 'string', 'description': 'Sexo (M/F/Otro)'},
            'guardian_name': {'type': 'string', 'description': 'Nombre del apoderado'},
            'guardian_type': {'type': 'string', 'description': 'Tipo de apoderado'},
            'guardian_dni': {'type': 'string', 'description': 'DNI del apoderado'},
            'guardian_contact': {'type': 'string', 'description': 'Contacto del apoderado'},
            'preliminary_diagnosis': {'type': 'string', 'description': 'Diagnostico preliminar'},
            'therapy_goals': {'type': 'string', 'description': 'Objetivos de terapia'},
            'notes': {'type': 'string', 'description': 'Notas adicionales'},
            'email': {'type': 'string', 'description': 'Nuevo email (si se añade, activa la cuenta)'},
        },
        'required': ['patient_id'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_update_patient_profile(patient_id, **kwargs):
    patient = User.query.get(patient_id)
    if not patient or patient.role != 'jugador':
        return {'error': 'Paciente no encontrado'}

    try:
        updated = []
        # Detailed fields
        fields = {
            'document_number': 15,
            'phone': 20,
            'guardian_name': 200,
            'guardian_type': 50,
            'guardian_dni': 15,
            'guardian_contact': 200,
            'preliminary_diagnosis': 2000,
            'therapy_goals': 2000,
            'notes': 2000,
            'sex': 20,
        }
        for field, length in fields.items():
            if field in kwargs and kwargs[field] is not None:
                setattr(patient, field, sanitize_text(kwargs[field], length))
                updated.append(field)

        if 'date_of_birth' in kwargs and kwargs['date_of_birth']:
            try:
                patient.date_of_birth = datetime.strptime(kwargs['date_of_birth'], '%Y-%m-%d').date()
                updated.append('date_of_birth')
            except ValueError:
                return {'error': 'Formato de fecha invalido para date_of_birth. Use YYYY-MM-DD'}

        # Email activation logic
        if 'email' in kwargs and kwargs['email']:
            new_email = kwargs['email'].strip().lower()
            if new_email != patient.email and new_email:
                exists = User.query.filter_by(email=new_email).first()
                if exists:
                    return {'error': 'El correo ya está registrado por otro usuario'}

                was_placeholder = patient.email.startswith('noemail_') or patient.email.startswith('temp_')
                patient.email = new_email

                if was_placeholder:
                    password = EmailService.generate_password()
                    patient.password = bcrypt.generate_password_hash(password).decode('utf-8')
                    patient.is_active = True
                    EmailService.send_welcome_email(new_email, password, patient.username)
                    updated.append('email (cuenta activada)')
                else:
                    updated.append('email')

        if not updated:
            return {'error': 'No se proporcionaron campos para actualizar'}

        db.session.commit()
        return {'success': True, 'message': f'Perfil de {patient.username} actualizado', 'updated_fields': updated}
    except Exception as e:
        db.session.rollback()
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
        resp = _api_post(
            '/api/admin/delete-user',
            json={'user_id': user_id},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
        resp = _api_post(
            '/api/admin/assign-therapist',
            json={
                'patient_id': patient_id,
                'therapist_id': therapist_id,
            },
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': 'Terapeuta asignado correctamente', 'data': data}
        return {'error': data.get('message', 'Error al asignar')}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='assign_therapist_to_sede',
    description='Asigna (o remueve) un terapeuta a una o varias sedes del centro. Sirve para decir "asigna a X como terapeuta de la sede Y". Puedes buscar por ID o por nombre del terapeuta y de la sede.',
    parameters={
        'type': 'object',
        'properties': {
            'therapist_id': {
                'type': 'integer',
                'description': 'ID del terapeuta (o usa therapist_name si no lo conoces)',
            },
            'therapist_name': {
                'type': 'string',
                'description': 'Nombre del terapeuta a buscar (si no aportaste therapist_id)',
            },
            'sede_id': {
                'type': 'integer',
                'description': 'ID de la sede (o usa sede_name si no lo conoces). Usa 0 para quitar TODAS las sedes del terapeuta.',
            },
            'sede_name': {'type': 'string', 'description': 'Nombre de la sede a buscar (si no aportaste sede_id)'},
            'action': {'type': 'string', 'description': '"asignar" (por defecto) o "remover" para sacarlo de la sede'},
        },
        'required': [],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_assign_therapist_to_sede(
    therapist_id=None,
    therapist_name=None,
    sede_id=None,
    sede_name=None,
    action='asignar',
    **kwargs,
):
    from app.models import Sede, User, db

    action = (action or 'asignar').strip().lower()
    if action not in ('asignar', 'remover'):
        return {'error': 'Acción inválida. Usa "asignar" o "remover".'}

    therapist = None
    if therapist_id or therapist_name:
        if therapist_id:
            therapist = User.query.filter_by(id=int(therapist_id), role='terapista').first()
            if not therapist:
                return {'error': f'No existe un terapeuta con ID {therapist_id}.'}
        elif therapist_name:
            matches = (
                User.query.filter(User.role == 'terapista', User.username.ilike(f'%{therapist_name.strip()}%'))
                .order_by(User.id)
                .all()
            )
            if not matches:
                return {
                    'error': f'No encontré ningún terapeuta llamado "{therapist_name}". Usa list_users/role para verificar.'
                }
            if len(matches) > 1:
                candidatos = ', '.join(f'{m.id}: {m.username}' for m in matches)
                return {
                    'error': f'Varios terapeutas coinciden con "{therapist_name}": {candidatos}. Pide que indique el ID exacto.'
                }
            therapist = matches[0]
    else:
        return {'error': 'Necesito el terapeuta: proporciona therapist_id o therapist_name.'}

    if action == 'remover' and not sede_id and not sede_name:
        therapist.assigned_sedes = []
        db.session.commit()
        return {
            'success': True,
            'message': f'{therapist.username} fue removido de todas sus sedes.',
            'therapist': {'id': therapist.id, 'username': therapist.username},
            'sedes': [],
        }

    if sede_id:
        if int(sede_id) == 0:
            therapist.assigned_sedes = []
            db.session.commit()
            return {
                'success': True,
                'message': f'{therapist.username} fue removido de todas sus sedes.',
                'therapist': {'id': therapist.id, 'username': therapist.username},
                'sedes': [],
            }
        sede = Sede.query.filter_by(id=int(sede_id)).first()
        if not sede or not sede.is_active:
            return {'error': f'No existe una sede activa con ID {sede_id}.'}
    elif sede_name:
        sedes = Sede.query.filter(Sede.name.ilike(f'%{sede_name.strip()}%'), Sede.is_active).all()
        if not sedes:
            return {'error': f'No encontré ninguna sede llamada "{sede_name}". Usa list_sedes para ver la lista.'}
        if len(sedes) > 1:
            candidatos = ', '.join(f'{s.id}: {s.name}' for s in sedes)
            return {'error': f'Varias sedes coinciden: {candidatos}. Pide que confirme el ID.'}
        sede = sedes[0]
    else:
        return {'error': 'Necesito la sede: proporciona sede_id o sede_name.'}

    current = list(therapist.assigned_sedes)
    if action == 'remover':
        if sede in current:
            therapist.assigned_sedes.remove(sede)
            msg = f'{therapist.username} fue removido de la sede {sede.name}.'
        else:
            msg = f'{therapist.username} ya no estaba asignado a la sede {sede.name}.'
    elif sede in current:
        msg = f'{therapist.username} ya estaba asignado a la sede {sede.name}.'
    else:
        therapist.assigned_sedes.append(sede)
        msg = f'{therapist.username} fue asignado como terapeuta de la sede {sede.name}.'

    db.session.commit()

    sedes = [{'id': s.id, 'name': s.name} for s in sorted(therapist.assigned_sedes, key=lambda x: x.id)]
    return {
        'success': True,
        'message': msg,
        'therapist': {'id': therapist.id, 'username': therapist.username, 'role': therapist.role},
        'sedes': sedes,
        'count': len(sedes),
    }


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
        if date is not None and not _valid_date(date):
            return {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}
        target = date or _today_lima()
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
        resp = _api_post(
            f'/api/sessions/{session_id}/complete', user_id=kwargs.get('_user_id'), role=kwargs.get('_role')
        )
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
        resp = _api_post(
            '/admin/api/sessions/batch',
            json={'sessions': sessions},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
            'status': {
                'type': 'string',
                'enum': ['NUEVO', 'EN_PROCESO', 'RESUELTO', 'CERRADO'],
                'description': 'Nuevo estado',
            },
        },
        'required': ['incident_id', 'status'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_update_incident_status(incident_id, status, **kwargs):
    try:
        resp = _api_post(
            f'/api/incidents/{incident_id}/status',
            json={'status': status},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
        resp = _api_post(
            f'/api/incidents/{incident_id}/assign',
            json={'assignee_id': assignee_id},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
        resp = _api_post(
            '/api/admin/patient-groups',
            json={'name': name, 'description': description},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
        resp = _api_post(
            '/api/admin/send-payment-reminder',
            json={'patient_id': patient_id},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
        payload = resp.get_json() if resp else {}
        data = payload.get('data', []) if isinstance(payload, dict) else []
        return {'success': True, 'count': len(data), 'expenses': data}
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
            'category': {
                'type': 'string',
                'description': 'Categoria: therapist_payment, operational, bonus, other (default: operational)',
            },
        },
        'required': ['description', 'amount'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_create_expense(description, amount, category='operational', **kwargs):
    try:
        from datetime import datetime as _dt

        from app.services.financial_service import normalize_expense_category

        resp = _api_post(
            '/admin/api/expenses/create',
            json={
                'description': description,
                'amount': float(amount),
                'category': normalize_expense_category(category),
                'date': _dt.now().strftime('%Y-%m-%d'),
                'method': 'other',
            },
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
        data = resp.get_json() if resp else {}
        if resp and resp.status_code < 400:
            return {'success': True, 'message': f'Gasto de S/. {amount:.2f} registrado', 'data': data}
        return {'error': data.get('error') or data.get('message') or 'Error al registrar gasto'}
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


@tool(
    name='compare_periods',
    description='Compara ingresos, egresos y ganancia entre dos meses. Muestra diferencia absoluta y porcentual.',
    parameters={
        'type': 'object',
        'properties': {
            'month1': {'type': 'integer', 'description': 'Mes inicial (1-12)'},
            'year1': {'type': 'integer', 'description': 'Ano inicial'},
            'month2': {'type': 'integer', 'description': 'Mes final (1-12)'},
            'year2': {'type': 'integer', 'description': 'Ano final'},
        },
        'required': ['month1', 'year1', 'month2', 'year2'],
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_compare_periods(month1, year1, month2, year2, **kwargs):
    import calendar
    from datetime import datetime as dt

    def _get_month_data(m, y):
        start = dt(y, m, 1)
        last_day = calendar.monthrange(y, m)[1]
        end = dt(y, m, last_day, 23, 59, 59)
        from sqlalchemy import func

        from app.models import Expense, Payment

        income = (
            db.session.query(func.sum(Payment.amount)).filter(Payment.date >= start, Payment.date <= end).scalar()
            or 0.0
        )
        expenses = (
            db.session.query(func.sum(Expense.amount)).filter(Expense.date >= start, Expense.date <= end).scalar()
            or 0.0
        )
        payments_count = Payment.query.filter(Payment.date >= start, Payment.date <= end).count()
        return {
            'income': float(income),
            'expenses': float(expenses),
            'net': float(income) - float(expenses),
            'payments_count': payments_count,
        }

    d1 = _get_month_data(month1, year1)
    d2 = _get_month_data(month2, year2)

    def _pct(old, new):
        if old == 0:
            return None if new == 0 else 100.0
        return round(((new - old) / old) * 100, 1)

    return {
        'success': True,
        'period1': {'month': month1, 'year': year1, **d1},
        'period2': {'month': month2, 'year': year2, **d2},
        'diff': {
            'income': round(d2['income'] - d1['income'], 2),
            'expenses': round(d2['expenses'] - d1['expenses'], 2),
            'net': round(d2['net'] - d1['net'], 2),
            'income_pct': _pct(d1['income'], d2['income']),
            'expenses_pct': _pct(d1['expenses'], d2['expenses']),
            'payments_count': d2['payments_count'] - d1['payments_count'],
        },
    }


@tool(
    name='get_user_growth',
    description='Metricas de crecimiento de usuarios: registros por mes, activos, inactivos, distribucion por rol.',
    parameters={
        'type': 'object',
        'properties': {
            'months': {'type': 'integer', 'description': 'Meses a analizar (default: 6)'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_user_growth(months=6, **kwargs):
    from datetime import datetime as dt
    from datetime import timedelta

    from sqlalchemy import extract

    from app.models import User

    today = dt.now(LIMA_TZ).date()
    results = []

    for i in range(months - 1, -1, -1):
        target_date = today.replace(day=1) - timedelta(days=i * 28)
        m, y = target_date.month, target_date.year

        total = User.query.filter(extract('month', User.created_at) == m, extract('year', User.created_at) == y).count()
        by_role = {}
        for role in ['jugador', 'terapista', 'admin', 'supervisor']:
            cnt = User.query.filter(
                User.role == role, extract('month', User.created_at) == m, extract('year', User.created_at) == y
            ).count()
            if cnt > 0:
                by_role[role] = cnt
        results.append(
            {'month': m, 'year': y, 'month_name': dt(y, m, 1).strftime('%B'), 'new_users': total, 'by_role': by_role}
        )

    active = User.query.filter_by(is_active=True).count()
    inactive = User.query.filter_by(is_active=False).count()
    total_users = User.query.count()
    by_role_total = {}
    for role in ['jugador', 'terapista', 'admin', 'supervisor']:
        cnt = User.query.filter_by(role=role).count()
        by_role_total[role] = cnt

    return {
        'success': True,
        'summary': {
            'total_users': total_users,
            'active': active,
            'inactive': inactive,
            'by_role': by_role_total,
        },
        'monthly': results,
    }


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
        from app.services.report_service import ReportService

        week_start, _ = ReportService().get_this_week_range()
        resp = _api_post(
            '/api/reports/generate-weekly',
            json={'patient_id': patient_id, 'week_start': week_start.isoformat()},
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
        resp = _api_post(
            '/api/messages/send',
            json={
                'receiver_id': receiver_id,
                'content': content,
            },
            user_id=kwargs.get('_user_id'),
            role=kwargs.get('_role'),
        )
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
        _api_post('/api/notifications/mark-read', user_id=kwargs.get('_user_id'), role=kwargs.get('_role'))
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


@tool(
    name='create_service_contract',
    description='Crea un contrato de servicio para un paciente con generación automática de cuotas. Requiere monto total y fecha de inicio.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'total_amount': {'type': 'number', 'description': 'Monto total del contrato en soles'},
            'installment_count': {'type': 'integer', 'description': 'Número de cuotas (default: 4)', 'default': 4},
            'billing_type': {
                'type': 'string',
                'description': 'Tipo de facturación',
                'enum': ['Mensual', 'Anual', 'Quincenal', 'Semanal'],
                'default': 'Mensual',
            },
            'start_date': {'type': 'string', 'description': 'Fecha de inicio del servicio YYYY-MM-DD'},
            'name': {'type': 'string', 'description': 'Nombre personalizado del contrato (opcional)'},
            'notes': {'type': 'string', 'description': 'Notas adicionales sobre el contrato'},
            'implementation_cost': {
                'type': 'number',
                'description': 'Costo de evaluación inicial (Cuota 0)',
                'default': 0,
            },
        },
        'required': ['patient_id', 'total_amount', 'start_date'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_service_contract(patient_id, total_amount, start_date, **kwargs):
    try:
        svc = ContractService()
        success, result = svc.create_contract(
            patient_id=patient_id,
            total_amount=float(total_amount),
            start_date=start_date,
            installment_count=kwargs.get('installment_count', 4),
            billing_type=kwargs.get('billing_type', 'Mensual'),
            name=kwargs.get('name'),
            notes=kwargs.get('notes'),
            implementation_cost=float(kwargs.get('implementation_cost', 0)),
        )
        if success:
            return {
                'success': True,
                'contract_id': result.id,
                'name': result.name,
                'installments_generated': result.installment_count,
                'message': f'Contrato "{result.name}" creado con éxito y cuotas generadas.',
            }
        return {'error': str(result)}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_contract_detail',
    description='Detalle completo de un contrato incluyendo todas las cuotas con estado.',
    parameters={
        'type': 'object',
        'properties': {
            'contract_id': {'type': 'integer', 'description': 'ID del contrato'},
        },
        'required': ['contract_id'],
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_contract_detail(contract_id, **kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    detail = svc.get_contract_detail(contract_id)
    if not detail:
        return {'error': 'Contrato no encontrado'}
    return {'success': True, 'contract': detail}


@tool(
    name='get_contracts_filtered',
    description='Lista contratos con filtros avanzados: búsqueda por nombre, estado, mes/año, sede.',
    parameters={
        'type': 'object',
        'properties': {
            'search': {'type': 'string', 'description': 'Buscar por nombre del paciente'},
            'status': {
                'type': 'string',
                'description': 'Filtrar por estado',
                'enum': ['active', 'cancelled', 'deudor', 'todos'],
            },
            'month': {'type': 'integer', 'description': 'Mes (1-12) para filtrar cuotas'},
            'year': {'type': 'integer', 'description': 'Año para filtrar cuotas'},
            'sede_id': {'type': 'integer', 'description': 'ID de sede'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_contracts_filtered(**kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    contracts = svc.get_contracts_filtered(
        search=kwargs.get('search'),
        status=kwargs.get('status'),
        month=kwargs.get('month'),
        year=kwargs.get('year'),
        sede_id=kwargs.get('sede_id'),
    )
    return {'success': True, 'count': len(contracts), 'contracts': contracts}


@tool(
    name='register_payment_with_evidence',
    description='Registra el pago de una cuota específica incluyendo la evidencia (URL del comprobante).',
    parameters={
        'type': 'object',
        'properties': {
            'installment_id': {'type': 'integer', 'description': 'ID de la cuota a pagar'},
            'amount': {'type': 'number', 'description': 'Monto pagado'},
            'method': {
                'type': 'string',
                'description': 'Método de pago',
                'enum': ['Efectivo', 'Yape', 'Transferencia', 'Plin', 'Tarjeta'],
            },
            'payment_date': {'type': 'string', 'description': 'Fecha del pago YYYY-MM-DD'},
            'receipt_url': {'type': 'string', 'description': 'URL o ruta de la imagen del voucher'},
            'reference': {'type': 'string', 'description': 'Número de operación o referencia'},
            'payment_notes': {'type': 'string', 'description': 'Notas adicionales sobre el pago'},
        },
        'required': ['installment_id', 'amount', 'method', 'payment_date', 'receipt_url'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_register_payment_with_evidence(installment_id, amount, method, payment_date, receipt_url, **kwargs):
    try:
        svc = ContractService()
        success, result = svc.pay_installment(
            installment_id=installment_id,
            amount=float(amount),
            method=method,
            payment_date=payment_date,
            reference=kwargs.get('reference'),
            payment_notes=kwargs.get('payment_notes'),
            receipt_path=receipt_url,
        )
        if success:
            return {
                'success': True,
                'payment_id': result.id if result else None,
                'message': f'Pago de S/. {amount} registrado exitosamente con evidencia.',
            }
        return {'error': str(result)}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='cancel_contract',
    description='Cancela un contrato. Requiere confirmación. Puede generar reembolso, crédito o nada.',
    parameters={
        'type': 'object',
        'properties': {
            'contract_id': {'type': 'integer', 'description': 'ID del contrato'},
            'cancellation_date': {'type': 'string', 'description': 'Fecha de cancelación YYYY-MM-DD'},
            'reason': {'type': 'string', 'description': 'Razón de cancelación'},
            'comment': {'type': 'string', 'description': 'Comentario adicional'},
            'disposition': {
                'type': 'string',
                'description': 'Disposition del dinero pagado',
                'enum': ['none', 'refund', 'credit'],
                'default': 'none',
            },
        },
        'required': ['contract_id', 'reason'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_cancel_contract(contract_id, reason, **kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    success, result = svc.cancel_contract(
        contract_id=contract_id,
        cancellation_date=kwargs.get('cancellation_date'),
        reason=reason,
        comment=kwargs.get('comment'),
        disposition=kwargs.get('disposition', 'none'),
    )
    if success:
        return {
            'success': True,
            'message': f'Contrato #{contract_id} cancelado',
            'disposition': kwargs.get('disposition', 'none'),
        }
    return {'error': str(result)}


@tool(
    name='reactivate_contract',
    description='Reactiva un contrato cancelado. Genera nuevas cuotas con fechas desde next_payment_date.',
    parameters={
        'type': 'object',
        'properties': {
            'contract_id': {'type': 'integer', 'description': 'ID del contrato'},
            'reactivation_date': {'type': 'string', 'description': 'Fecha de reactivación YYYY-MM-DD'},
            'next_payment_date': {'type': 'string', 'description': 'Fecha de próxima cuota YYYY-MM-DD'},
        },
        'required': ['contract_id', 'next_payment_date'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_reactivate_contract(contract_id, next_payment_date, **kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    success, result = svc.reactivate_contract(
        contract_id=contract_id,
        reactivation_date=kwargs.get('reactivation_date'),
        next_payment_date=next_payment_date,
    )
    if success:
        return {
            'success': True,
            'message': f'Contrato #{contract_id} reactivado',
        }
    return {'error': str(result)}


@tool(
    name='get_monthly_collection',
    description='Resumen de cobranza del mes: cuotas pagadas, pendientes, vencidas, monto total.',
    parameters={
        'type': 'object',
        'properties': {
            'month': {'type': 'integer', 'description': 'Mes (1-12). Default: mes actual'},
            'year': {'type': 'integer', 'description': 'Año. Default: año actual'},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_monthly_collection(**kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    breakdown = svc.get_monthly_breakdown(
        month=kwargs.get('month'),
        year=kwargs.get('year'),
    )
    return {'success': True, 'data': breakdown}


@tool(
    name='get_upcoming_installments',
    description='Cuotas próximas a vencer en los próximos N días. Útil para recordatorios.',
    parameters={
        'type': 'object',
        'properties': {
            'days_ahead': {'type': 'integer', 'description': 'Días hacia adelante (default 7)', 'default': 7},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_upcoming_installments(**kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    upcoming = svc.get_upcoming_installments(days_ahead=kwargs.get('days_ahead', 7))
    return {'success': True, 'count': len(upcoming), 'installments': upcoming}


@tool(
    name='get_due_installments',
    description='Cuotas vencidas (atrasadas). Retorna lista de cuotas pendientes con días de atraso.',
    parameters={
        'type': 'object',
        'properties': {},
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_get_due_installments(**kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    due = svc.get_due_installments()
    return {'success': True, 'count': len(due), 'installments': due}


@tool(
    name='update_contract',
    description='Actualiza campos de un contrato existente (nombre, notas, tipo de facturación, moneda, regla).',
    parameters={
        'type': 'object',
        'properties': {
            'contract_id': {'type': 'integer', 'description': 'ID del contrato'},
            'name': {'type': 'string', 'description': 'Nombre del contrato'},
            'notes': {'type': 'string', 'description': 'Notas'},
            'billing_type': {
                'type': 'string',
                'description': 'Tipo de facturación',
                'enum': ['Mensual', 'Quincenal', 'Semanal', 'Anual'],
            },
            'currency': {'type': 'string', 'description': 'Moneda', 'default': 'PEN'},
            'billing_rule': {
                'type': 'string',
                'description': 'Regla de facturación',
                'enum': ['standard', 'sign-date'],
            },
        },
        'required': ['contract_id'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_update_contract(contract_id, **kwargs):
    from app.services.contract_service import ContractService

    svc = ContractService()
    fields = {k: v for k, v in kwargs.items() if k != 'contract_id' and v is not None}
    success, result = svc.update_contract(contract_id, **fields)
    if success:
        return {'success': True, 'message': f'Contrato #{contract_id} actualizado'}
    return {'error': str(result)}


@tool(
    name='get_patient_stats',
    description='Obtener estadisticas demograficas de pacientes: distribucion por edades, sexo, sede, fecha de ingreso, guardianes, diagnosticos, contratos activos.',
    parameters={
        'type': 'object',
        'properties': {},
    },
    category='read',
    roles=ROLES_ADMIN,
)
def handle_get_patient_stats():

    from app.routes.admin.users import patient_stats

    with current_app.test_request_context('/api/patient-stats'):
        result = patient_stats()
        return result.get_json()


@tool(
    name='update_patient_details',
    description='Actualizar datos personales de un paciente (DNI, telefono, fecha de nacimiento, sexo, apoderado, diagnostico, etc). Sincroniza con contratos automaticamente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {
                'type': 'integer',
                'description': 'ID del paciente',
            },
            'document_number': {
                'type': 'string',
                'description': 'DNI del paciente',
            },
            'phone': {
                'type': 'string',
                'description': 'Telefono del paciente',
            },
            'date_of_birth': {
                'type': 'string',
                'description': 'Fecha de nacimiento (YYYY-MM-DD)',
            },
            'sex': {
                'type': 'string',
                'description': 'Sexo del paciente',
                'enum': ['M', 'F', 'Otro'],
            },
            'guardian_name': {
                'type': 'string',
                'description': 'Nombre del apoderado/tutor',
            },
            'guardian_type': {
                'type': 'string',
                'description': 'Tipo de apoderado',
                'enum': ['padre', 'madre', 'tutor', 'otro'],
            },
            'guardian_dni': {
                'type': 'string',
                'description': 'DNI del apoderado',
            },
            'guardian_contact': {
                'type': 'string',
                'description': 'Contacto del apoderado (telefono/email)',
            },
            'preliminary_diagnosis': {
                'type': 'string',
                'description': 'Diagnostico preliminar',
            },
            'therapy_goals': {
                'type': 'string',
                'description': 'Objetivos de terapia',
            },
            'notes': {
                'type': 'string',
                'description': 'Notas adicionales',
            },
        },
        'required': ['patient_id'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_update_patient_details(patient_id, **kwargs):
    from datetime import datetime

    from app.extensions import db as _db
    from app.models import User

    user = User.query.get(patient_id)
    if not user:
        return {'error': 'Paciente no encontrado'}

    allowed_fields = [
        'document_number',
        'phone',
        'date_of_birth',
        'sex',
        'guardian_name',
        'guardian_type',
        'guardian_dni',
        'guardian_contact',
        'preliminary_diagnosis',
        'therapy_goals',
        'notes',
    ]

    updated = []
    for field in allowed_fields:
        if field in kwargs and kwargs[field] is not None:
            value = kwargs[field]
            if field == 'date_of_birth' and isinstance(value, str):
                try:
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    return {'error': f'Formato de fecha invalido para {field}'}
            setattr(user, field, value if value != '' else None)
            updated.append(field)

    if not updated:
        return {'error': 'No hay campos para actualizar'}

    _db.session.commit()
    return {'success': True, 'message': f'Paciente #{patient_id} actualizado', 'updated_fields': updated}
