import logging
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import Payment, User
from app.services.financial_service import FinancialService
from app.services.payment_service import PaymentService

logger = logging.getLogger('app')

TOOL_REGISTRY = {}


def tool(name, description, parameters, category='read'):
    """Decorator to register a tool."""

    def decorator(func):
        TOOL_REGISTRY[name] = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'category': category,
            'handler': func,
        }
        return func

    return decorator


def get_tools_for_mode(mode):
    """Return list of tool dicts for Groq API based on mode."""
    tools = []
    for _, t in TOOL_REGISTRY.items():
        if mode == 'chiquito' and t['category'] == 'write':
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
        resp = current_app.test_client().get('/admin/api/financial-summary')
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
        resp = current_app.test_client().get(f'/api/admin/deudores?month={month}')
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
        resp = current_app.test_client().get(f'/admin/api/sessions?{qs}')
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
        resp = current_app.test_client().get(f'/admin/api/therapist-efficiency{params}')
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
    description='Registra un pago para un paciente. SOLO cuando tengas patient_id y amount confirmados.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'amount': {'type': 'number', 'description': 'Monto del pago en soles'},
            'method': {
                'type': 'string',
                'description': 'Metodo de pago',
                'enum': ['Efectivo', 'Yape', 'Transferencia', 'IA/Copilot', 'IA/Copilot + OCR'],
                'default': 'IA/Copilot',
            },
            'reference': {'type': 'string', 'description': 'Referencia del pago'},
        },
        'required': ['patient_id', 'amount'],
    },
    category='write',
)
def handle_register_payment(patient_id, amount, method='IA/Copilot', reference=''):
    patient = User.query.get(patient_id)
    if not patient:
        return {'error': 'Paciente no encontrado'}
    try:
        success, result = _payment_service.register_payment(
            patient_id=patient_id,
            amount=float(amount),
            method=method,
            reference=reference or 'Copilot',
            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
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
        resp = current_app.test_client().get(f'/admin/api/payment-info/{patient_id}')
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
        resp = current_app.test_client().get('/admin/api/payments/all')
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
        resp = current_app.test_client().get('/admin/yape/pending')
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
        resp = current_app.test_client().get(f'/admin/yape/search?q={query}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}
