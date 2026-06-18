import logging
import os
import secrets
from datetime import datetime, timedelta

from flask import current_app

from app.auth_compat import current_user
from app.extensions import bcrypt, db
from app.models import AIChatMessage, Appointment, ContactMessage, Notification, Payment, Sede, User
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
        resp = current_app.test_client().post(
            '/api/admin/assign-therapist',
            json={'patient_id': patient_id, 'therapist_ids': therapist_ids},
        )
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
        resp = current_app.test_client().get('/admin/api/overview')
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
        resp = current_app.test_client().get(f'/admin/api/expenses?{qs}')
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
        resp = current_app.test_client().post(
            '/api/admin/messages/broadcast',
            json=payload,
        )
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
        resp = current_app.test_client().get(f'/admin/api/weekly-summary{params}')
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
        resp = current_app.test_client().get(f'/admin/api/reports/monthly?{qs}')
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
        resp = current_app.test_client().post('/admin/generate-ia-report')
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
