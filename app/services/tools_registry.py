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
    """Decorator to register a tool."""

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


def get_tools_for_mode(mode, user_role=None):
    """Return list of tool dicts for Groq API based on mode and role."""
    tools = []
    for _, t in TOOL_REGISTRY.items():
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


def execute_tool(name, args):
    """Execute a tool by name with given args. Returns dict result."""
    t = TOOL_REGISTRY.get(name)
    if not t:
        return {'error': f'Unknown tool: {name}'}
    try:
        return t['handler'](**args)
    except Exception as e:
        logger.error(f'Tool {name} error: {e}', exc_info=True)
        return {'error': str(e)}


def _api_get(endpoint):
    """Make authenticated GET via test_client, forwarding current session."""
    with current_app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = session.get('user_id')
            sess['role'] = session.get('role', 'admin')
        return c.get(endpoint)


def _api_post(endpoint, json=None):
    """Make authenticated POST via test_client, forwarding current session."""
    with current_app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = session.get('user_id')
            sess['role'] = session.get('role', 'admin')
        return c.post(endpoint, json=json or {})


@tool(
    name='search_patients',
    description='Busca pacientes por nombre, email o telefono. MINIMO 2 caracteres.',
    parameters={
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Termino de busqueda (min 2 caracteres)'},
            'limit': {'type': 'integer', 'description': 'Maximo resultados', 'default': 10},
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
                User.phone.ilike(f'%{query}%'),
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
                'is_active': p.is_active,
                'phone': getattr(p, 'phone', ''),
            }
            for p in patients
        ],
    }


@tool(
    name='list_users',
    description='Lista todos los usuarios del sistema. Opcionalmente filtrar por rol.',
    parameters={
        'type': 'object',
        'properties': {
            'role': {
                'type': 'string',
                'description': 'Filtrar por rol: admin, terapista, jugador, supervisor',
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
    users = q.order_by(User.username).limit(100).all()
    return {
        'success': True,
        'count': len(users),
        'users': [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'is_active': u.is_active,
            }
            for u in users
        ],
    }


@tool(
    name='get_user',
    description='Obtiene detalle completo de un usuario por ID.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
        },
        'required': ['user_id'],
    },
    category='read',
)
def handle_get_user(user_id):
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
            'is_active': user.is_active,
            'phone': getattr(user, 'phone', ''),
            'sede_id': getattr(user, 'sede_id', None),
            'created_at': str(user.created_at) if hasattr(user, 'created_at') else '',
        },
    }


_finance_service = FinancialService()
_payment_service = PaymentService()


@tool(
    name='get_financial_summary',
    description='Resumen financiero del mes actual: ingresos, egresos, ganancia, cobranza.',
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
    name='get_debt_report',
    description='Reporte de deudores. Muestra pacientes con pagos pendientes agrupados por sede.',
    parameters={
        'type': 'object',
        'properties': {
            'month': {
                'type': 'string',
                'description': 'Mes en formato YYYY-MM o "all" para todos',
                'default': 'current',
            },
        },
    },
    category='read',
)
def handle_debt_report(month='current'):
    try:
        resp = _api_get(f'/api/admin/deudores?month={month}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_sessions',
    description='Obtiene sesiones del calendario en un rango de fechas.',
    parameters={
        'type': 'object',
        'properties': {
            'start': {'type': 'string', 'description': 'Fecha inicio (YYYY-MM-DD)'},
            'end': {'type': 'string', 'description': 'Fecha fin (YYYY-MM-DD)'},
            'therapist_id': {'type': 'integer', 'description': 'Filtrar por terapeuta'},
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
    name='get_therapist_efficiency',
    description='Metricas de eficiencia de terapeutas: sesiones, accuracy, audit compliance.',
    parameters={
        'type': 'object',
        'properties': {
            'therapist_id': {'type': 'integer', 'description': 'Filtrar por terapeuta especifico'},
        },
    },
    category='read',
)
def handle_therapist_efficiency(therapist_id=None):
    try:
        params = f'?therapist_id={therapist_id}' if therapist_id else ''
        resp = _api_get(f'/admin/api/therapist-efficiency{params}')
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
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).limit(50).all()
    return {
        'success': True,
        'patient': {'id': patient.id, 'username': patient.username},
        'payments': [
            {
                'id': p.id,
                'amount': float(p.amount),
                'date': str(p.date),
                'method': p.method,
                'reference': p.reference,
            }
            for p in payments
        ],
    }


@tool(
    name='register_payment',
    description='Registra pago para paciente. Usa patient_id (de search_patients) o patient_name + amount.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {
                'type': 'integer',
                'description': 'ID numerico del paciente (obtenido via search_patients)',
            },
            'patient_name': {
                'type': 'string',
                'description': 'Nombre del paciente (alternativa a patient_id)',
            },
            'amount': {'type': 'number', 'description': 'Monto del pago en soles (numerico, sin simbolos)'},
            'method': {
                'type': 'string',
                'description': 'Metodo de pago',
                'enum': ['Efectivo', 'Yape', 'Transferencia', 'IA/Copilot', 'IA/Copilot + OCR'],
            },
            'reference': {'type': 'string', 'description': 'Referencia opcional del pago'},
            'discount': {
                'type': 'number',
                'description': 'Descuento opcional (en soles)',
            },
            'payment_date': {
                'type': 'string',
                'description': 'Fecha del pago opcional (YYYY-MM-DD)',
            },
        },
        'required': ['amount'],
    },
    category='write',
)
def handle_register_payment(
    amount, patient_id=None, patient_name=None, method='IA/Copilot', reference='', discount=0.0, payment_date=None
):
    if not patient_id and not patient_name:
        return {'error': 'Debes proporcionar patient_id o patient_name'}
    if patient_id:
        patient = User.query.get(patient_id)
    else:
        patient = User.query.filter(User.username.ilike(f'%{patient_name}%')).first()
    if not patient:
        return {'error': 'Paciente no encontrado. Usa search_patients para encontrar el ID correcto.'}
    try:
        success, result = _payment_service.register_payment(
            patient_id=patient.id,
            amount=float(amount),
            method=method,
            reference=reference or 'Copilot',
            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            discount=float(discount),
            payment_date=payment_date,
        )
        if success:
            return {
                'success': True,
                'message': f'Pago de S/. {amount:.2f} registrado para {patient.username}',
                'payment_id': result.id if hasattr(result, 'id') else None,
            }
        else:
            return {'error': str(result)}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_payment_info',
    description='Obtiene configuracion de pago de un paciente (monto, fecha de vencimiento, plan).',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='read',
)
def handle_get_payment_info(patient_id):
    try:
        resp = _api_get(f'/admin/api/payment-info/{patient_id}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_all_payments',
    description='Lista los ultimos pagos registrados en el sistema.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_all_payments():
    try:
        resp = _api_get('/admin/api/payments/all')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_yape_pending',
    description='Transacciones Yape pendientes de asignar a pacientes.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_yape_pending():
    try:
        resp = _api_get('/admin/yape/pending')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='search_yape_transactions',
    description='Busca transacciones Yape por query (operacion, monto, etc).',
    parameters={
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Termino de busqueda'},
        },
        'required': ['query'],
    },
    category='read',
)
def handle_search_yape(query):
    try:
        resp = _api_get(f'/admin/yape/search?q={query}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='create_user',
    description='Crea un nuevo usuario en el sistema.',
    parameters={
        'type': 'object',
        'properties': {
            'username': {'type': 'string', 'description': 'Nombre completo del usuario'},
            'role': {
                'type': 'string',
                'description': 'Rol del usuario',
                'enum': ['jugador', 'terapista', 'admin'],
                'default': 'jugador',
            },
            'email': {'type': 'string', 'description': 'Email del usuario'},
        },
        'required': ['username'],
    },
    category='write',
)
def handle_create_user(username, role='jugador', email=None):
    if current_user.role != 'admin':
        return {'error': 'Solo administradores pueden crear usuarios'}
    _DEFAULT_USER_PASSWORD = os.environ.get('DEFAULT_USER_PASSWORD') or secrets.token_urlsafe(12)
    if not email:
        email = f'{username.lower().replace(" ", ".")}@centrojuanpabloii.com'
    existing = User.query.filter(db.or_(User.username.ilike(username), User.email == email)).first()
    if existing:
        return {'error': f'Ya existe un usuario: {existing.username}'}
    user = User(
        username=username,
        email=email,
        password=bcrypt.generate_password_hash(_DEFAULT_USER_PASSWORD).decode('utf-8'),
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return {
        'success': True,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'temp_password': _DEFAULT_USER_PASSWORD,
        'message': f'Usuario {username} creado como {role}',
    }


@tool(
    name='toggle_user_status',
    description='Activa o desactiva un usuario. El estado cambia al opuesto del actual.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
        },
        'required': ['user_id'],
    },
    category='write',
)
def handle_toggle_user_status(user_id):
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activado' if user.is_active else 'desactivado'
    return {
        'success': True,
        'user_id': user.id,
        'username': user.username,
        'is_active': user.is_active,
        'message': f'Usuario {user.username} {status}',
    }


@tool(
    name='delete_user',
    description='ELIMINA un usuario permanentemente. Solo ejecutar tras confirmacion explicita.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario a eliminar'},
        },
        'required': ['user_id'],
    },
    category='write',
)
def handle_delete_user(user_id):
    if current_user.role != 'admin':
        return {'error': 'Solo administradores pueden eliminar usuarios'}
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    if user.id == current_user.id:
        return {'error': 'No puedes eliminarte a ti mismo'}
    for model in [AIChatMessage, Appointment, Payment, ContactMessage, Notification]:
        model.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return {'success': True, 'message': f'Usuario {user.username} eliminado'}


@tool(
    name='assign_therapist',
    description='Asigna uno o mas terapeutas a un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'therapist_ids': {
                'type': 'array',
                'items': {'type': 'integer'},
                'description': 'IDs de los terapeutas a asignar',
            },
        },
        'required': ['patient_id', 'therapist_ids'],
    },
    category='write',
)
def handle_assign_therapist(patient_id, therapist_ids):
    if isinstance(therapist_ids, int):
        therapist_ids = [therapist_ids]
    try:
        resp = _api_post('/api/admin/assign-therapist', json={'patient_id': patient_id, 'therapist_ids': therapist_ids})
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='reset_password',
    description='Resetea la contrasena de un usuario a una temporal.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
        },
        'required': ['user_id'],
    },
    category='write',
)
def handle_reset_password(user_id):
    if current_user.role != 'admin':
        return {'error': 'Solo administradores pueden resetear contrasenas'}
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    new_pw = secrets.token_urlsafe(8)
    user.password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    return {
        'success': True,
        'message': f'Contrasena reseteada para {user.username}',
        'temp_password': new_pw,
    }


@tool(
    name='create_appointment',
    description='Crea una sesion para un paciente con un terapeuta.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'patient_name': {'type': 'string', 'description': 'Nombre del paciente (si no sabes el ID)'},
            'day': {'type': 'string', 'description': 'Dia de la sesion (YYYY-MM-DD)'},
            'time': {'type': 'string', 'description': 'Hora (HH:MM)'},
            'duration_minutes': {'type': 'integer', 'description': 'Duracion en minutos', 'default': 60},
        },
    },
    category='write',
)
def handle_create_appointment(patient_id=None, patient_name=None, day=None, time=None, duration_minutes=60):
    if not patient_id and not patient_name:
        return {'error': 'Debes proporcionar patient_id o patient_name'}
    if not patient_id:
        patient = User.query.filter(User.username.ilike(f'%{patient_name}%'), User.role == 'jugador').first()
        if not patient:
            return {'error': f'Paciente "{patient_name}" no encontrado'}
        patient_id = patient.id
    if day and time:
        start_str = f'{day} {time}'
    else:
        start_str = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d %H:%M')
    except ValueError:
        start_dt = datetime.now() + timedelta(hours=1)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    patient = User.query.get(patient_id)
    appt = Appointment(
        therapist_id=current_user.id,
        patient_id=patient_id,
        title=f'Sesion con {patient.username}',
        start_time=start_dt,
        end_time=end_dt,
        status='scheduled',
    )
    db.session.add(appt)
    db.session.commit()
    return {
        'success': True,
        'appointment_id': appt.id,
        'message': f'Sesion creada para {patient.username} el {start_dt.strftime("%d/%m/%Y %H:%M")}',
    }


@tool(
    name='get_dashboard_overview',
    description='Resumen general del dashboard: total terapeutas, pacientes, sesiones, accuracy.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_dashboard_overview():
    try:
        resp = _api_get('/admin/api/overview')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='register_expense',
    description='Registra un gasto del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'category': {'type': 'string', 'description': 'Categoria del gasto'},
            'amount': {'type': 'number', 'description': 'Monto en soles'},
            'description': {'type': 'string', 'description': 'Descripcion del gasto'},
            'date': {'type': 'string', 'description': 'Fecha del gasto (YYYY-MM-DD)'},
        },
        'required': ['category', 'amount'],
    },
    category='write',
)
def handle_register_expense(category, amount, description='', date=None):
    svc = FinancialService()
    try:
        expense_data = {
            'category': category,
            'amount': float(amount),
            'date': date or datetime.now().strftime('%Y-%m-%d'),
            'description': description or 'Gasto via Copilot',
            'method': 'IA/Copilot',
        }
        svc.create_expense(expense_data)
        return {'success': True, 'message': f'Gasto de S/. {amount} registrado en {category}'}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_expenses',
    description='Obtiene lista de gastos del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'start_date': {'type': 'string', 'description': 'Fecha inicio (YYYY-MM-DD)'},
            'end_date': {'type': 'string', 'description': 'Fecha fin (YYYY-MM-DD)'},
            'category': {'type': 'string', 'description': 'Filtrar por categoria'},
        },
    },
    category='read',
)
def handle_get_expenses(start_date=None, end_date=None, category=None):
    try:
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if category:
            params['category'] = category
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = _api_get(f'/admin/api/expenses?{qs}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='broadcast_message',
    description='Envia un mensaje a todos los pacientes, terapeutas, o un usuario especifico.',
    parameters={
        'type': 'object',
        'properties': {
            'subject': {'type': 'string', 'description': 'Asunto del mensaje'},
            'body': {'type': 'string', 'description': 'Cuerpo del mensaje'},
            'target': {
                'type': 'string',
                'description': 'Destinatarios: all, therapists, patients, specific',
                'default': 'all',
            },
            'receiver_id': {'type': 'integer', 'description': 'ID del usuario si target=specific'},
        },
        'required': ['subject', 'body'],
    },
    category='write',
)
def handle_broadcast(subject, body, target='all', receiver_id=None):
    try:
        payload = {'subject': subject, 'body': body, 'target': target}
        if receiver_id:
            payload['receiver_id'] = receiver_id
        resp = _api_post('/api/admin/messages/broadcast', json=payload)
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_weekly_summary',
    description='Resumen semanal por terapeuta.',
    parameters={
        'type': 'object',
        'properties': {
            'week_start': {'type': 'string', 'description': 'Fecha de inicio de la semana (YYYY-MM-DD)'},
        },
    },
    category='read',
)
def handle_weekly_summary(week_start=None):
    try:
        params = f'?week_start={week_start}' if week_start else ''
        resp = _api_get(f'/admin/api/weekly-summary{params}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_monthly_summary',
    description='Resumen mensual del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'year': {'type': 'integer', 'description': 'Ano'},
            'month': {'type': 'integer', 'description': 'Mes (1-12)'},
        },
    },
    category='read',
)
def handle_monthly_summary(year=None, month=None):
    try:
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = _api_get(f'/admin/api/reports/monthly?{qs}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='generate_ai_report',
    description='Genera un reporte estrategico de inteligencia artificial del centro.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_generate_report():
    try:
        resp = _api_post('/admin/generate-ia-report')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_sedes',
    description='Lista todas las sedes del centro.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_get_sedes():
    sedes = Sede.query.all()

    return {
        'success': True,
        'sedes': [
            {
                'id': s.id,
                'name': s.name,
                'address': getattr(s, 'address', ''),
                'patient_count': User.query.filter_by(sede_id=s.id, role='jugador').count(),
            }
            for s in sedes
        ],
    }


# ──────────────────────────────────────────────
#  NEW TOOLS — Patient Detail
# ──────────────────────────────────────────────


@tool(
    name='get_patient_detail',
    description='Obtiene detalle completo de un paciente: datos personales, diagnóstico, apoderado, pagos, sesiones recientes.',
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
        .limit(10)
        .all()
    )
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).limit(10).all()
    return {
        'success': True,
        'patient': {
            'id': patient.id,
            'username': patient.username,
            'email': patient.email,
            'phone': patient.phone,
            'document_number': patient.document_number,
            'date_of_birth': str(patient.date_of_birth) if patient.date_of_birth else None,
            'age': age,
            'sex': patient.sex,
            'preliminary_diagnosis': patient.preliminary_diagnosis,
            'therapy_goals': patient.therapy_goals,
            'notes': patient.notes,
            'guardian_name': patient.guardian_name,
            'guardian_type': patient.guardian_type,
            'guardian_dni': patient.guardian_dni,
            'guardian_contact': patient.guardian_contact,
            'sede_id': patient.sede_id,
            'assigned_therapist_id': patient.assigned_therapist_id,
            'payment_plan': patient.payment_plan,
            'payment_amount': patient.payment_amount,
            'sessions_total': patient.sessions_total,
            'sessions_attended': patient.sessions_attended,
            'sessions_remaining': patient.sessions_remaining,
        },
        'sessions': [
            {
                'id': s.id,
                'start_time': str(s.start_time),
                'end_time': str(s.end_time),
                'status': s.status,
                'title': s.title,
            }
            for s in sessions
        ],
        'payments': [
            {
                'id': p.id,
                'amount': float(p.amount),
                'date': str(p.date),
                'method': p.method,
            }
            for p in payments
        ],
    }


@tool(
    name='update_patient',
    description='Actualiza datos de un paciente: diagnóstico, metas, notas, apoderado, etc.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'preliminary_diagnosis': {'type': 'string', 'description': 'Diagnóstico preliminar'},
            'therapy_goals': {'type': 'string', 'description': 'Objetivos de terapia'},
            'notes': {'type': 'string', 'description': 'Notas adicionales'},
            'guardian_name': {'type': 'string', 'description': 'Nombre del apoderado'},
            'guardian_type': {'type': 'string', 'description': 'Tipo de apoderado (madre, padre, tutor)'},
            'guardian_contact': {'type': 'string', 'description': 'Contacto del apoderado'},
            'phone': {'type': 'string', 'description': 'Teléfono del paciente'},
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
    allowed = {
        'preliminary_diagnosis',
        'therapy_goals',
        'notes',
        'guardian_name',
        'guardian_type',
        'guardian_contact',
        'phone',
    }
    updated = []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            setattr(patient, k, v)
            updated.append(k)
    if updated:
        db.session.commit()
    return {'success': True, 'updated_fields': updated, 'message': f'Paciente {patient.username} actualizado'}


# ──────────────────────────────────────────────
#  NEW TOOLS — Sessions
# ──────────────────────────────────────────────


@tool(
    name='get_session_detail',
    description='Obtiene detalle completo de una sesión: info, paciente, terapeuta, auditoría, juegos.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesión'},
        },
        'required': ['session_id'],
    },
    category='read',
    roles=ROLES_THERAPIST,
)
def handle_get_session_detail(session_id):
    appt = Appointment.query.get(session_id)
    if not appt:
        return {'error': 'Sesión no encontrada'}
    patient = User.query.get(appt.patient_id)
    therapist = User.query.get(appt.therapist_id)
    audit = None
    if hasattr(appt, 'audit') and appt.audit:
        a = appt.audit
        audit = {
            'score': a.audit_score,
            'status': a.audit_status,
            'planned_text': (a.planned_text or '')[:200],
            'transcript_text': (a.transcript_text or '')[:200],
        }
    return {
        'success': True,
        'session': {
            'id': appt.id,
            'title': appt.title,
            'start_time': str(appt.start_time),
            'end_time': str(appt.end_time),
            'status': appt.status,
            'notes': appt.notes,
            'therapy_type': appt.therapy_type,
            'attendance': appt.attendance,
        },
        'patient': {'id': patient.id, 'username': patient.username} if patient else None,
        'therapist': {'id': therapist.id, 'username': therapist.username} if therapist else None,
        'audit': audit,
    }


@tool(
    name='create_session',
    description='Crea una nueva sesión para un paciente con un terapeuta.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'therapist_id': {'type': 'integer', 'description': 'ID del terapeuta'},
            'day': {'type': 'string', 'description': 'Fecha (YYYY-MM-DD)'},
            'time': {'type': 'string', 'description': 'Hora (HH:MM)'},
            'duration_minutes': {'type': 'integer', 'description': 'Duración en minutos', 'default': 60},
            'notes': {'type': 'string', 'description': 'Notas de la sesión'},
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
        title=f'Sesión con {patient.username}',
        start_time=start_dt,
        end_time=end_dt,
        status='scheduled',
        notes=notes,
        duration_minutes=duration_minutes,
    )
    db.session.add(appt)
    db.session.commit()
    return {'success': True, 'session_id': appt.id, 'message': f'Sesión creada para {patient.username} el {day} {time}'}


@tool(
    name='update_session',
    description='Actualiza una sesión existente: cambiar hora, estado, notas, terapeuta.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesión'},
            'status': {'type': 'string', 'description': 'Nuevo estado: scheduled, in_progress, completed, cancelled'},
            'notes': {'type': 'string', 'description': 'Notas actualizadas'},
            'start_time': {'type': 'string', 'description': 'Nueva hora inicio (YYYY-MM-DD HH:MM)'},
            'duration_minutes': {'type': 'integer', 'description': 'Nueva duración en minutos'},
        },
        'required': ['session_id'],
    },
    category='write',
    roles=ROLES_THERAPIST,
)
def handle_update_session(session_id, status=None, notes=None, start_time=None, duration_minutes=None):
    appt = Appointment.query.get(session_id)
    if not appt:
        return {'error': 'Sesión no encontrada'}
    updated = []
    if status:
        appt.status = status
        updated.append('status')
    if notes is not None:
        appt.notes = notes
        updated.append('notes')
    if start_time:
        appt.start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        if duration_minutes:
            appt.end_time = appt.start_time + timedelta(minutes=duration_minutes)
        updated.append('start_time')
    elif duration_minutes:
        appt.end_time = appt.start_time + timedelta(minutes=duration_minutes)
        appt.duration_minutes = duration_minutes
        updated.append('duration_minutes')
    if updated:
        db.session.commit()
    return {'success': True, 'updated_fields': updated, 'message': f'Sesión {session_id} actualizada'}


@tool(
    name='delete_session',
    description='Elimina una sesión permanentemente.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesión a eliminar'},
        },
        'required': ['session_id'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_delete_session(session_id):
    appt = Appointment.query.get(session_id)
    if not appt:
        return {'error': 'Sesión no encontrada'}
    db.session.delete(appt)
    db.session.commit()
    return {'success': True, 'message': f'Sesión {session_id} eliminada'}


@tool(
    name='complete_session',
    description='Marca una sesión como completada.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesión'},
        },
        'required': ['session_id'],
    },
    category='write',
    roles=ROLES_THERAPIST,
)
def handle_complete_session(session_id):
    appt = Appointment.query.get(session_id)
    if not appt:
        return {'error': 'Sesión no encontrada'}
    appt.status = 'completed'
    appt.attendance = 'attended'
    db.session.commit()
    return {'success': True, 'message': f'Sesión {session_id} completada'}


# ──────────────────────────────────────────────
#  NEW TOOLS — Incidents
# ──────────────────────────────────────────────


@tool(
    name='list_incidents',
    description='Lista incidencias con filtros: estado, categoría, responsable, prioridad.',
    parameters={
        'type': 'object',
        'properties': {
            'estado': {'type': 'string', 'description': 'Filtrar por estado: NUEVO, EN_CURSO, RESUELTO, CERRADO'},
            'categoria': {'type': 'string', 'description': 'Filtrar por categoría'},
            'responsable_id': {'type': 'integer', 'description': 'Filtrar por responsable'},
            'limit': {'type': 'integer', 'description': 'Máximo resultados', 'default': 20},
        },
    },
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_list_incidents(estado=None, categoria=None, responsable_id=None, limit=20):
    from app.models.incidente import Incidente

    q = Incidente.query.filter_by(is_active=True)
    if estado:
        q = q.filter_by(estado=estado)
    if categoria:
        q = q.filter_by(categoria=categoria)
    if responsable_id:
        q = q.filter_by(responsable_id=responsable_id)
    incidents = q.order_by(Incidente.created_at.desc()).limit(limit).all()
    return {
        'success': True,
        'count': len(incidents),
        'incidents': [
            {
                'id': i.id_incidente,
                'titulo': i.titulo,
                'categoria': i.categoria,
                'estado': i.estado,
                'prioridad': i.prioridad,
                'impacto': i.impacto,
                'urgencia': i.urgencia,
                'responsable_id': i.responsable_id,
                'created_at': str(i.created_at) if i.created_at else None,
                'fecha_limite_sla': str(i.fecha_limite_sla) if i.fecha_limite_sla else None,
            }
            for i in incidents
        ],
    }


@tool(
    name='create_incident',
    description='Crea una nueva incidencia en el sistema.',
    parameters={
        'type': 'object',
        'properties': {
            'titulo': {'type': 'string', 'description': 'Título de la incidencia'},
            'descripcion': {'type': 'string', 'description': 'Descripción detallada'},
            'categoria': {'type': 'string', 'description': 'Categoría: TECNICO, OPERATIVO, SERVICIO, SEGURIDAD'},
            'impacto': {'type': 'integer', 'description': 'Impacto (1=bajo, 2=medio, 3=alto)', 'default': 2},
            'urgencia': {'type': 'integer', 'description': 'Urgencia (1=baja, 2=media, 3=alta)', 'default': 2},
            'responsable_id': {'type': 'integer', 'description': 'ID del responsable'},
        },
        'required': ['titulo', 'descripcion', 'categoria'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_create_incident(titulo, descripcion, categoria, impacto=2, urgencia=2, responsable_id=None):
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
        responsable_id=responsable_id,
        fecha_creacion=datetime.utcnow(),
        evidencia_original='',
        evidencia_tipo='texto',
    )
    db.session.add(inc)
    db.session.commit()
    return {'success': True, 'incident_id': inc.id_incidente, 'message': f'Incidencia #{inc.id_incidente} creada'}


@tool(
    name='update_incident_status',
    description='Cambia el estado de una incidencia (sigue la máquina de estados ITIL).',
    parameters={
        'type': 'object',
        'properties': {
            'incident_id': {'type': 'integer', 'description': 'ID de la incidencia'},
            'nuevo_estado': {
                'type': 'string',
                'description': 'Nuevo estado: EN_CURSO, PENDIENTE_PROVEEDOR, RESUELTO, CERRADO',
            },
            'comentario': {'type': 'string', 'description': 'Comentario del cambio'},
        },
        'required': ['incident_id', 'nuevo_estado'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_update_incident_status(incident_id, nuevo_estado, comentario=None):
    from app.models.incidente import Incidente, IncidenteHistorial

    inc = Incidente.query.get(incident_id)
    if not inc:
        return {'error': 'Incidencia no encontrada'}
    estado_anterior = inc.estado
    inc.estado = nuevo_estado
    if nuevo_estado == 'RESUELTO':
        inc.fecha_resolucion = datetime.utcnow()
    historial = IncidenteHistorial(
        incidente_id=inc.id_incidente,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        comentario=comentario,
        changed_by_id=current_user.id,
        changed_at=datetime.utcnow(),
    )
    db.session.add(historial)
    db.session.commit()
    return {'success': True, 'message': f'Incidencia #{incident_id} cambiada de {estado_anterior} a {nuevo_estado}'}


@tool(
    name='assign_incident',
    description='Asigna una incidencia a un responsable.',
    parameters={
        'type': 'object',
        'properties': {
            'incident_id': {'type': 'integer', 'description': 'ID de la incidencia'},
            'responsable_id': {'type': 'integer', 'description': 'ID del nuevo responsable'},
        },
        'required': ['incident_id', 'responsable_id'],
    },
    category='write',
    roles=ROLES_ADMIN,
)
def handle_assign_incident(incident_id, responsable_id):
    from app.models.incidente import Incidente

    inc = Incidente.query.get(incident_id)
    if not inc:
        return {'error': 'Incidencia no encontrada'}
    inc.responsable_id = responsable_id
    db.session.commit()
    return {'success': True, 'message': f'Incidencia #{incident_id} asignada al usuario {responsable_id}'}


@tool(
    name='add_incident_comment',
    description='Agrega un comentario a una incidencia.',
    parameters={
        'type': 'object',
        'properties': {
            'incident_id': {'type': 'integer', 'description': 'ID de la incidencia'},
            'contenido': {'type': 'string', 'description': 'Texto del comentario'},
            'es_interno': {
                'type': 'boolean',
                'description': 'Si es comentario interno (solo admin ve)',
                'default': False,
            },
        },
        'required': ['incident_id', 'contenido'],
    },
    category='write',
    roles=ROLES_SUPERVISOR,
)
def handle_add_incident_comment(incident_id, contenido, es_interno=False):
    from app.models.incidente import Incidente, IncidenteComentario

    inc = Incidente.query.get(incident_id)
    if not inc:
        return {'error': 'Incidencia no encontrada'}
    comment = IncidenteComentario(
        incidente_id=inc.id_incidente,
        autor_id=current_user.id,
        contenido=contenido,
        es_interno=es_interno,
        created_at=datetime.utcnow(),
    )
    db.session.add(comment)
    db.session.commit()
    return {'success': True, 'message': f'Comentario agregado a incidencia #{incident_id}'}


# ──────────────────────────────────────────────
#  NEW TOOLS — Notifications
# ──────────────────────────────────────────────


@tool(
    name='list_notifications',
    description='Lista notificaciones del usuario actual.',
    parameters={
        'type': 'object',
        'properties': {
            'category': {
                'type': 'string',
                'description': 'Filtrar por categoría: debt, activity, system, alert, payment',
            },
            'unread_only': {'type': 'boolean', 'description': 'Solo no leídas', 'default': False},
            'limit': {'type': 'integer', 'description': 'Máximo resultados', 'default': 20},
        },
    },
    category='read',
    roles=ROLES_ALL,
)
def handle_list_notifications(category=None, unread_only=False, limit=20):
    q = Notification.query.filter_by(user_id=current_user.id, is_active=True)
    if category:
        q = q.filter_by(category=category)
    if unread_only:
        q = q.filter_by(is_read=False)
    notifs = q.order_by(Notification.timestamp.desc()).limit(limit).all()
    return {
        'success': True,
        'count': len(notifs),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.type,
                'category': n.category,
                'is_read': n.is_read,
                'timestamp': str(n.timestamp),
                'link': n.link,
            }
            for n in notifs
        ],
    }


@tool(
    name='mark_notification_read',
    description='Marca una notificación como leída.',
    parameters={
        'type': 'object',
        'properties': {
            'notification_id': {'type': 'integer', 'description': 'ID de la notificación (0 = todas)'},
        },
        'required': ['notification_id'],
    },
    category='write',
    roles=ROLES_ALL,
)
def handle_mark_notification_read(notification_id):
    if notification_id == 0:
        Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        return {'success': True, 'message': 'Todas las notificaciones marcadas como leídas'}
    notif = Notification.query.get(notification_id)
    if not notif or notif.user_id != current_user.id:
        return {'error': 'Notificación no encontrada'}
    notif.is_read = True
    db.session.commit()
    return {'success': True, 'message': 'Notificación marcada como leída'}


# ──────────────────────────────────────────────
#  NEW TOOLS — Reports
# ──────────────────────────────────────────────


@tool(
    name='get_weekly_report',
    description='Obtiene reporte semanal de un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'week_start': {'type': 'string', 'description': 'Inicio de semana (YYYY-MM-DD)'},
        },
        'required': ['patient_id'],
    },
    category='read',
    roles=ROLES_THERAPIST,
)
def handle_get_weekly_report(patient_id, week_start=None):
    from app.models.report import WeeklyReport

    q = WeeklyReport.query.filter_by(patient_id=patient_id, is_active=True)
    if week_start:
        q = q.filter_by(week_start=week_start)
    reports = q.order_by(WeeklyReport.week_start.desc()).limit(5).all()
    return {
        'success': True,
        'reports': [
            {
                'id': r.id,
                'week_start': str(r.week_start),
                'week_end': str(r.week_end),
                'avg_score': r.avg_score,
                'sessions_count': r.sessions_count,
                'objectives_achieved': r.objectives_achieved,
                'objectives_total': r.objectives_total,
                'report_text': (r.report_text or '')[:300],
            }
            for r in reports
        ],
    }


@tool(
    name='get_monthly_report',
    description='Obtiene reporte mensual de un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'year': {'type': 'integer', 'description': 'Año'},
            'month': {'type': 'integer', 'description': 'Mes (1-12)'},
        },
        'required': ['patient_id'],
    },
    category='read',
    roles=ROLES_THERAPIST,
)
def handle_get_monthly_report(patient_id, year=None, month=None):
    from app.models.report import MonthlyReport

    q = MonthlyReport.query.filter_by(patient_id=patient_id, is_active=True)
    if year:
        q = q.filter_by(year=year)
    if month:
        q = q.filter_by(month=month)
    reports = q.order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc()).limit(6).all()
    return {
        'success': True,
        'reports': [
            {
                'id': r.id,
                'month': r.month,
                'year': r.year,
                'avg_score': r.avg_score,
                'sessions_count': r.sessions_count,
                'objectives_achieved': r.objectives_achieved,
                'objectives_total': r.objectives_total,
                'report_text': (r.report_text or '')[:300],
            }
            for r in reports
        ],
    }


@tool(
    name='get_quarterly_report',
    description='Obtiene reporte trimestral de un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'year': {'type': 'integer', 'description': 'Año'},
            'quarter': {'type': 'integer', 'description': 'Trimestre (1-4)'},
        },
        'required': ['patient_id'],
    },
    category='read',
    roles=ROLES_THERAPIST,
)
def handle_get_quarterly_report(patient_id, year=None, quarter=None):
    from app.models.report import QuarterlyReport

    q = QuarterlyReport.query.filter_by(patient_id=patient_id, is_active=True)
    if year:
        q = q.filter_by(year=year)
    if quarter:
        q = q.filter_by(quarter=quarter)
    reports = q.order_by(QuarterlyReport.year.desc(), QuarterlyReport.quarter.desc()).limit(4).all()
    return {
        'success': True,
        'reports': [
            {
                'id': r.id,
                'quarter': r.quarter,
                'year': r.year,
                'avg_score': r.avg_score,
                'sessions_count': r.sessions_count,
                'objectives_achieved': r.objectives_achieved,
                'objectives_total': r.objectives_total,
                'report_text': (r.report_text or '')[:300],
            }
            for r in reports
        ],
    }


# ──────────────────────────────────────────────
#  NEW TOOLS — Games
# ──────────────────────────────────────────────


@tool(
    name='list_games',
    description='Lista todos los juegos terapéuticos disponibles.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_THERAPIST,
)
def handle_list_games():
    from app.models.game import Game

    games = Game.query.filter_by(is_active=True).all()
    return {
        'success': True,
        'count': len(games),
        'games': [
            {
                'id': g.id,
                'title': g.title,
                'filename': g.filename,
                'description': g.description,
            }
            for g in games
        ],
    }


@tool(
    name='get_session_games',
    description='Obtiene los juegos asignados a una sesión.',
    parameters={
        'type': 'object',
        'properties': {
            'session_id': {'type': 'integer', 'description': 'ID de la sesión'},
        },
        'required': ['session_id'],
    },
    category='read',
    roles=ROLES_THERAPIST,
)
def handle_get_session_games(session_id):
    from app.models.appointment import AppointmentGame
    from app.models.game import Game

    games = (
        db.session.query(AppointmentGame, Game)
        .join(Game, AppointmentGame.game_id == Game.id)
        .filter(AppointmentGame.appointment_id == session_id, AppointmentGame.is_active == True)
        .all()
    )
    return {
        'success': True,
        'games': [
            {
                'id': ag.id,
                'game_id': g.id,
                'title': g.title,
                'status': ag.status,
                'config': ag.config,
            }
            for ag, g in games
        ],
    }


# ──────────────────────────────────────────────
#  NEW TOOLS — Dashboard & Stats
# ──────────────────────────────────────────────


@tool(
    name='get_realtime_stats',
    description='Estadísticas en tiempo real: sesiones de hoy, terapeutas activos, incidencias abiertas.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_realtime_stats():
    from app.models.incidente import Incidente

    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    sessions_today = Appointment.query.filter(
        Appointment.start_time >= datetime.combine(today, datetime.min.time()),
        Appointment.start_time < datetime.combine(tomorrow, datetime.min.time()),
        Appointment.is_active == True,
    ).count()
    active_therapists = User.query.filter_by(role='terapista', is_active=True).count()
    open_incidents = Incidente.query.filter(
        Incidente.estado.in_(['NUEVO', 'EN_CURSO']), Incidente.is_active == True
    ).count()
    total_patients = User.query.filter_by(role='jugador', is_active=True).count()
    return {
        'success': True,
        'stats': {
            'sessions_today': sessions_today,
            'active_therapists': active_therapists,
            'open_incidents': open_incidents,
            'total_patients': total_patients,
        },
    }


@tool(
    name='get_therapist_dashboard',
    description='Dashboard del terapeuta: sesiones pendientes, pacientes asignados, eficiencia.',
    parameters={
        'type': 'object',
        'properties': {
            'therapist_id': {'type': 'integer', 'description': 'ID del terapeuta (vacío = actual)'},
        },
    },
    category='read',
    roles=ROLES_THERAPIST,
)
def handle_therapist_dashboard(therapist_id=None):
    tid = therapist_id or current_user.id
    therapist = User.query.get(tid)
    if not therapist:
        return {'error': 'Terapeuta no encontrado'}
    patients = User.query.filter_by(assigned_therapist_id=tid, role='jugador', is_active=True).all()
    upcoming = (
        Appointment.query.filter(
            Appointment.therapist_id == tid,
            Appointment.status.in_(['scheduled', 'in_progress']),
            Appointment.is_active == True,
        )
        .order_by(Appointment.start_time)
        .limit(10)
        .all()
    )
    return {
        'success': True,
        'therapist': {'id': therapist.id, 'username': therapist.username},
        'patients': [{'id': p.id, 'username': p.username} for p in patients],
        'upcoming_sessions': [
            {
                'id': a.id,
                'patient_id': a.patient_id,
                'start_time': str(a.start_time),
                'status': a.status,
            }
            for a in upcoming
        ],
        'stats': {
            'total_patients': len(patients),
            'upcoming_count': len(upcoming),
        },
    }


# ──────────────────────────────────────────────
#  NEW TOOLS — Contracts
# ──────────────────────────────────────────────


@tool(
    name='get_contract_detail',
    description='Obtiene detalle de contrato de un paciente: cuotas, montos, estado.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='read',
    roles=ROLES_ADMIN,
)
def handle_get_contract_detail(patient_id):
    from app.models.contract import Contract, Installment

    contract = Contract.query.filter_by(patient_id=patient_id, is_active=True).first()
    if not contract:
        return {'success': True, 'contract': None, 'message': 'No hay contrato activo'}
    installments = (
        Installment.query.filter_by(contract_id=contract.id, is_active=True).order_by(Installment.number).all()
    )
    return {
        'success': True,
        'contract': {
            'id': contract.id,
            'total_amount': contract.total_amount,
            'installment_count': contract.installment_count,
            'installment_amount': contract.installment_amount,
            'start_date': str(contract.start_date) if contract.start_date else None,
            'end_date': str(contract.end_date) if contract.end_date else None,
            'status': contract.status,
        },
        'installments': [
            {
                'number': inst.number,
                'due_date': str(inst.due_date),
                'amount': inst.amount,
                'paid_amount': inst.paid_amount,
                'status': inst.status,
            }
            for inst in installments
        ],
    }


# ──────────────────────────────────────────────
#  NEW TOOLS — Patient Groups
# ──────────────────────────────────────────────


@tool(
    name='list_patient_groups',
    description='Lista grupos de pacientes configurados en el sistema.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
    roles=ROLES_SUPERVISOR,
)
def handle_list_patient_groups():
    from app.models.patient_group import PatientGroup

    groups = PatientGroup.query.filter_by(is_active=True).all()
    return {
        'success': True,
        'count': len(groups),
        'groups': [
            {
                'id': g.id,
                'name': g.name,
                'sede_id': g.sede_id,
                'start_time': g.start_time,
                'end_time': g.end_time,
                'work_days': g.work_days,
            }
            for g in groups
        ],
    }
