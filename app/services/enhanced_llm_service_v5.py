import logging
import os
import re
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore', message='.*google.generativeai.*has ended.*')
from app.extensions import db
from app.models import Appointment, Payment, User
from app.services.context_loader_service import context_loader
from app.services.workflow_intelligence_service import predict_next_action, track_workflow
from app.utils.cache_utils import CONTEXT_CACHE_KEY, invalidate_context


def get_cached_context():
    from app.utils.cache_utils import cache_get

    return cache_get(CONTEXT_CACHE_KEY, loader_func=context_loader.get_full_context)


def get_cached_context_text():
    context = get_cached_context()
    if context:
        return context_loader.format_context_for_llama(context)
    return ''


logger = logging.getLogger('app')

_RE_AMOUNT = re.compile(r'S/?\.?\s*(\d+(?:[.,]\d{3})*(?:[.,]\d{2})?)')
_RE_PATIENT = re.compile(
    r'(?:para|con|de|alumno|paciente|Sr|Sra|Dr)\s+([A-Za-záéíóúÁÉÍÓÚ]+(?:\s+[A-Za-záéíóúÁÉÍÓÚ]+)*)'
)
_RE_NAME_CAPS = re.compile(r'\b([A-Z][a-záéíóú]+(?:\s+[A-Z][a-záéíóú]+)*)\b')
_RE_DATE = re.compile(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})')
_RE_DAY = re.compile(r'(lunes|martes|miércoles|jueves|viernes|sábado|domingo)')
_RE_RELATIVE = re.compile(r'(mañana|hoy|esta semana|próxima semana|pronto)')
_RE_HOUR = re.compile(r'(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m|p\.m)?', re.IGNORECASE)

SEMANTIC_MAPS = {
    'unpaid_users': {
        'keywords': [
            'no han pagado',
            'moroso',
            'deuda',
            'sin pagar',
            'deudor',
            'no pagó',
            'vencido',
            'atrasado',
            'incobrable',
            'debe',
            'debe pagar',
            'morosos',
            'deudores',
            'sin cobrar',
            'impago',
            'adeudado',
        ],
        'alternatives': ['quién', 'cuáles', 'cuántos', 'lista', 'listar'],
        'example': '¿Cuántos alumnos no han pagado este mes?',
    },
    'weekly_due': {
        'keywords': [
            'próxima semana',
            'próximos días',
            'vencer',
            'próximo',
            'esta semana',
            'deben pagar',
            'vencimiento',
            'próxima fecha',
            '7 días',
            'dentro de',
            'vencen',
            'vencerá',
            'vence pronto',
            'próximas fechas',
            'pendiente pago',
            'paga próximo',
            'pagar pronto',
        ],
        'alternatives': ['quién', 'cuáles', 'cuántos', 'lista', 'detalles', 'pago'],
        'example': '¿Quiénes tienen que pagar próxima semana?',
    },
    'revenue_metrics': {
        'keywords': [
            'finanzas',
            'ganancias',
            'ingresos',
            'egresos',
            'ganancia',
            'balance',
            'cómo van',
            'estado financiero',
            'utilidad',
            'beneficio',
            'profit',
            'revenue',
            'margen',
            'cobranza',
            'cuentas',
            'cómo andan',
            'económico',
            'dinero',
            'fondos',
            'capital',
            'activos',
            'pasivos',
        ],
        'alternatives': ['estado', 'cómo', 'qué tal', 'informe', 'reporte'],
        'example': '¿Cómo están las finanzas?',
    },
    'breakeven_analysis': {
        'keywords': [
            'necesito',
            'cuántos alumnos',
            'breakeven',
            'ganancia de',
            'profit',
            'objetivo',
            'meta',
            'para ganar',
            'para lograr',
            'rentabilidad',
            'punto equilibrio',
            'proyección',
        ],
        'alternatives': ['cuántos', 'cantidad', 'número'],
        'example': 'Necesito ganar 15000 soles, ¿cuántos alumnos necesito?',
    },
    'schedule_optimization': {
        'keywords': [
            'mejorar horarios',
            'optimize',
            'optimar',
            'reorganizar',
            'recomendación horarios',
            'sugerencia horarios',
            'cómo mejoro',
            'agendar mejor',
            'programación óptima',
            'conflictos horarios',
        ],
        'alternatives': ['cómo', 'mejora', 'propuesta', 'idea'],
        'example': '¿Cómo mejoro los horarios?',
    },
    'generate_report': {
        'keywords': [
            'informe',
            'reporte',
            'report',
            'resumen',
            'análisis',
            'data',
            'estadísticas',
            'métricas',
            'gráficos',
            'datos',
            'síntesis',
            'compilar',
            'reunir datos',
        ],
        'alternatives': ['dame', 'muestra', 'envía', 'crea', 'genera'],
        'example': 'Dame un informe completo',
    },
    'register_payment': {
        'keywords': [
            'registra',
            'pagar',
            'payment',
            'cobrar',
            'pagó',
            'registrar pago',
            'recibió',
            'cobrado',
            'acreditado',
            'confirmado',
            'ingresó',
            'pagó',
            'abonó',
            'depositó',
            'transferencia',
            'pago',
            'ingreso',
            'recibí pago',
            'cobré',
            'se pagó',
            'fue pagado',
            'me pagó',
            'metió',
            'metí',
            'entró dinero',
            'llegó dinero',
            'entró pago',
        ],
        'alternatives': ['recibí', 'cobré', 'metí', 'ingresó', 'soles', 'cantidad'],
        'example': 'Registra S/. 500 para Juan',
    },
    'upload_voucher': {
        'keywords': [
            'boleta',
            'foto',
            'comprobante',
            'recibo',
            'voucher',
            'imagen',
            'screenshot',
            'evidencia',
            'descarga',
            'sube',
            'adjunta',
            'factura',
            'documento',
            'comprobación',
        ],
        'alternatives': ['envía', 'carga', 'procesa', 'analiza'],
        'example': 'Sube la foto de la boleta',
    },
    'create_appointment': {
        'keywords': [
            'agendar',
            'crear sesión',
            'nueva cita',
            'programar',
            'schedule session',
            'crear appointment',
            'nueva sesión',
            'sesión',
            'cita',
            'appointment',
            'reservar',
            'agendá',
            'cita con',
        ],
        'alternatives': ['para', 'con', 'entre', 'el', 'la'],
        'example': 'Agendar sesión con Juan el lunes',
    },
    'update_session': {
        'keywords': [
            'actualizar sesión',
            'cambiar sesión',
            'modificar',
            'reprogramar',
            'cambiar horario',
            'movimiento',
            'rescheduled',
            'mover sesión',
        ],
        'alternatives': ['de', 'a', 'nueva', 'sesión'],
        'example': 'Mueve la sesión de Juan a las 3pm',
    },
    'delete_session': {
        'keywords': [
            'cancelar sesión',
            'eliminar sesión',
            'borrar cita',
            'canceled',
            'quitar',
            'remover',
            'eliminar cita',
        ],
        'alternatives': ['sesión', 'cita', 'appointment'],
        'example': 'Cancela la sesión de María',
    },
    'create_expense': {
        'keywords': [
            'crear gasto',
            'nuevo gasto',
            'gastar',
            'egreso',
            'costo',
            'expense',
            'invertir',
            'pagar proveedor',
            'registra gasto',
            'registrar costo',
            'registrar egreso',
        ],
        'alternatives': ['por', 'categoría', 'descripción', 'útiles'],
        'example': 'Registra un gasto de S/.200 para útiles',
    },
    'assign_therapist': {
        'keywords': [
            'asignar terapeuta',
            'assign therapist',
            'terapeuta',
            'psicólogo',
            'especialista',
            'cuenta con',
            'asigna',
            'asignación',
        ],
        'alternatives': ['para', 'a', 'con'],
        'example': 'Asigna a Juan con el Dr. García',
    },
    'create_user': {
        'keywords': [
            'crear usuario',
            'nuevo paciente',
            'nuevo alumno',
            'registrar',
            'nuevo usuario',
            'agregar usuario',
            'crear cuenta',
            'dar de alta',
            'nuevo cliente',
            'registra alumno',
            'agrega paciente',
        ],
        'alternatives': ['nombre', 'email', 'teléfono', 'rol', 'crear'],
        'example': 'Crear usuario María García',
    },
    'list_users': {
        'keywords': [
            'listar usuarios',
            'mostrar usuarios',
            'ver usuarios',
            'todos los usuarios',
            'usuarios activos',
            'lista de',
            'quiénes',
            'cuáles usuarios',
            'cuántos pacientes',
            'pacientes activos',
            'cuántos tengo',
            'cuántos alumnos',
            'pacientes registrados',
            'alumnos activos',
            'cuántos hay',
        ],
        'alternatives': ['usuarios', 'pacientes', 'alumnos'],
        'example': 'Lista todos los usuarios',
    },
    'list_sessions': {
        'keywords': [
            'ver sesiones',
            'sesiones',
            'citas',
            'agenda',
            'calendario',
            'appointments',
            'horarios',
            'próximas sesiones',
            'mis sesiones',
            'todas las sesiones',
            'listar sesiones',
            'mostrar sesiones',
        ],
        'alternatives': ['de', 'para', 'con'],
        'example': 'Ver todas las sesiones',
    },
    'broadcast_message': {
        'keywords': [
            'enviar mensaje',
            'broadcast',
            'notificar',
            'anunciar',
            'comunicar',
            'aviso',
            'mensaje a todos',
            'mensajes',
        ],
        'alternatives': ['a', 'para', 'tema'],
        'example': 'Envía mensaje a todos los pacientes',
    },
    'navigation': {
        'keywords': ['llévame', 'navega', 'ir a', 'voy a', 'go to', 'abre', 'vamos a', 'acceder', 'ingresar', 'vaya a'],
        'sections': [
            'deudores',
            'pagos',
            'sesiones',
            'reportes',
            'usuarios',
            'sedes',
            'gastos',
            'mensajes',
            'juegos',
            'dashboard',
            'panel',
        ],
        'example': 'Llévame a ver los deudores',
    },
    'list_payments': {
        'keywords': [
            'Ver pagos',
            'historial de pagos',
            'payment history',
            'transacciones',
            'comprobantes',
            'recibos',
            'ingresos',
            'pagos registrados',
            'pagos de',
            'mis pagos',
            'qué pagos',
            'pagos registrados',
            'quién pagó',
            'últimos pagos',
            'historial pago',
            'revisión pagos',
        ],
        'alternatives': ['de', 'para', 'usuario', 'pago'],
        'example': 'Ver historial de pagos de Juan',
    },
}

CRITICAL_PARAMS = {
    'register_payment': ['patient_name', 'amount'],
    'create_appointment': ['patient_name', 'day', 'time'],
    'create_expense': ['amount', 'category'],
    'assign_therapist': ['patient_name'],
    'create_user': ['patient_name'],
}

CLARIFICATION_QUESTIONS = {
    'register_payment': '¿Para quién es el pago y cuál es el monto? ej: "S/. 500 para Juan"',
    'create_appointment': '¿Cuál es el nombre del paciente y qué día/hora prefieres?',
    'create_expense': '¿Cuál es el monto y la categoría del gasto?',
    'assign_therapist': '¿Cuál es el nombre del paciente para asignarle terapeuta?',
    'create_user': '¿Cuál es el nombre completo del nuevo usuario?',
}

NAV_URL_MAP = {
    'dashboard': 'admin.dashboard',
    'pacientes': 'admin.users',
    'patients': 'admin.users',
    'cobros': 'admin.dashboard',
    'payments': 'admin.dashboard',
    'reportes': 'admin.reports',
    'reports': 'admin.reports',
    'sesiones': 'admin.dashboard',
    'sessions': 'admin.dashboard',
    'juegos': 'admin.games',
    'games': 'admin.games',
    'gastos': 'admin.expenses',
    'expenses': 'admin.expenses',
    'sedes': 'admin.sedes',
}

INTENTS_WITH_DATA = {
    'unpaid_users',
    'weekly_due',
    'revenue_metrics',
    'breakeven_analysis',
    'schedule_optimization',
    'generate_report',
    'list_sessions',
    'list_payments',
    'list_users',
}

MUTATION_INTENTS = {'register_payment', 'create_user'}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_semantic_confidence(message: str, intent_key: str) -> float:
    msg_lower = message.lower()
    keywords = SEMANTIC_MAPS.get(intent_key, {}).get('keywords', [])
    keyword_matches = sum(1 for kw in keywords if kw in msg_lower)
    if keyword_matches > 0:
        return min(0.98, 0.5 + (keyword_matches * 0.1))
    return 0.0


def detect_user_intent_v5(message: str) -> tuple:
    message.lower()
    scores = {k: get_semantic_confidence(message, k) for k in SEMANTIC_MAPS}
    valid_intents = [(k, v) for k, v in scores.items() if v > 0.0]
    valid_intents.sort(key=lambda x: x[1], reverse=True)

    if valid_intents and valid_intents[0][1] >= 0.5:
        best_intent, best_confidence = valid_intents[0]
    else:
        best_intent = 'general_chat'
        best_confidence = max(valid_intents[0][1] if valid_intents else 0.3, 0.3)

    params = extract_parameters_v5(message, best_intent)

    if best_intent != 'general_chat' and should_ask_clarification(best_intent, params):
        return (
            best_intent,
            params,
            best_confidence,
            CLARIFICATION_QUESTIONS.get(best_intent, '¿Puedes dar más detalles?'),
        )

    return best_intent, params, best_confidence, None


def extract_parameters_v5(message: str, intent: str) -> dict:
    msg_lower = message.lower()
    params = {}
    amount_match = _RE_AMOUNT.search(message)
    if amount_match:
        params['amount'] = safe_float(amount_match.group(1).replace(',', '').replace('.', ''))

    patient_match = _RE_PATIENT.search(message)
    if patient_match:
        params['patient_name'] = patient_match.group(1).strip()

    if 'patient_name' not in params:
        name_matches = _RE_NAME_CAPS.findall(message)
        if name_matches:
            params['patient_name'] = name_matches[0]

    all_names = re.findall(r'\b([A-Za-záéíóúÁÉÍÓÚ]+(?:\s+[A-Za-záéíóúÁÉÍÓÚ]+)*)\b', message)
    params['mentioned_names'] = all_names

    date_match = _RE_DATE.search(message) or _RE_DAY.search(message) or _RE_RELATIVE.search(message)
    if date_match:
        params['date_reference'] = date_match.group(0)

    if intent == 'breakeven_analysis' and amount_match:
        params['target_profit'] = safe_float(amount_match.group(1).replace(',', '').replace('.', ''))

    elif intent == 'navigation':
        for section in SEMANTIC_MAPS['navigation']['sections']:
            if section in msg_lower:
                params['target_section'] = section
                break

    elif intent == 'create_appointment':
        for day in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']:
            if day in msg_lower:
                params['day'] = day
                break
        hour_match = _RE_HOUR.search(message)
        if hour_match:
            params['time'] = hour_match.group(0)

    elif intent == 'create_expense':
        for categ in ['útiles', 'servicios', 'salarios', 'rent', 'mantenimiento', 'otros']:
            if categ in msg_lower:
                params['category'] = categ
                break

    return params


def should_ask_clarification(intent: str, params: dict) -> bool:
    required = CRITICAL_PARAMS.get(intent, [])
    return any(p not in params or not params[p] for p in required)


def process_intent_with_data_v5(intent: str, params: dict, message: str):
    from app.services.business_analytics_service import (
        answer_business_question,
        calculate_revenue_metrics,
        estimate_breakeven_point,
        generate_business_report,
        get_schedule_recommendations,
        get_unpaid_users,
        get_weekly_due_payments,
    )

    try:
        if intent == 'unpaid_users':
            data = get_unpaid_users()
            response = f"""ALUMNOS SIN PAGAR - ESTE MES

Resumen:
  - Total de deudores: {data['total_unpaid']} alumno(s)
  - Deuda acumulada: S/. {data['total_debt']:.2f}

Top Deudores:"""
            for i, user in enumerate(data['users'][:5], 1):
                response += f'\n  {i}. {user["name"]}\n     - Deuda: S/. {user["amount_due"]:.2f}'
            return response

        elif intent == 'weekly_due':
            data = get_weekly_due_payments()
            response = f"""PAGOS PROXIMA SEMANA

Resumen:
  - Alumnos que vencen: {data['count']}
  - Ingresos esperados: S/. {data['total_amount']:.2f}

Proximos a Pagar:"""
            for i, p in enumerate(data['payments'][:5], 1):
                response += f'\n  {i}. {p["name"]}\n     - Monto: S/. {p["amount"]}'
            return response

        elif intent == 'revenue_metrics':
            data = calculate_revenue_metrics()
            verdict = 'Ganando dinero' if data['net_profit'] > 0 else 'Gastos superiores a ingresos - Requiere atencion'
            return f"""METRICAS FINANCIERAS - ESTE MES

Estado General:
  - Ingresos totales: S/. {data['total_income']:.2f}
  - Egresos totales: S/. {data['total_expenses']:.2f}

Rentabilidad:
  - Ganancia neta: S/. {data['net_profit']:.2f}
  - Margen de ganancia: {data['profit_margin_percent']:.1f}%

Cobranza:
  - Tasa de cobranza: {data['collection_rate']:.1f}%

Analisis: {verdict}"""

        elif intent == 'breakeven_analysis':
            be = estimate_breakeven_point(params.get('target_profit', 5000))
            if be:
                return f"""Punto de Equilibrio para S/. {params['target_profit']:,.0f}
Alumnos actuales: {be['current_students']}
Necesarios: {be['students_needed']}
Adicionales: {be['additional_students']}
Factibilidad: {be['feasibility'].upper()}"""
            return 'Error en cálculo'

        elif intent == 'schedule_optimization':
            rec = get_schedule_recommendations()
            return f'Recomendaciones para Horarios\n{rec["recommendations"][:500]}'

        elif intent == 'generate_report':
            return generate_business_report()

        elif intent == 'list_sessions':
            tomorrow = datetime.now() + timedelta(days=1)
            sessions = (
                Appointment.query.filter(
                    Appointment.start_time >= tomorrow,
                    Appointment.start_time <= tomorrow + timedelta(days=7),
                    Appointment.status.in_(['pending', 'confirmed']),
                )
                .order_by(Appointment.start_time)
                .limit(10)
                .all()
            )
            if not sessions:
                return 'No hay sesiones programadas para la proxima semana'
            response = 'Proximas Sesiones\n'
            for s in sessions:
                patient = User.query.get(s.patient_id)
                response += f'\n• {patient.username}: {s.start_time.strftime("%a %d %b %H:%M")}'
            return response

        elif intent == 'list_payments':
            payments = Payment.query.order_by(Payment.date.desc()).limit(10).all()
            if not payments:
                return 'Sin pagos registrados'
            response = 'Ultimos Pagos\n'
            for p in payments:
                patient = User.query.get(p.patient_id)
                response += f'\n• {patient.username}: S/. {p.amount} ({p.date.strftime("%d/%m")})'
            return response

        elif intent == 'list_users':
            context = get_cached_context()
            patients_list = context.get('patients', {}).get('patients', [])
            if not patients_list:
                return 'No hay pacientes registrados'
            response = f'{len(patients_list)} Pacientes Activos\n'
            for p in patients_list[:10]:
                response += f'\n• {p.get("name", "?")}'
                if p.get('days_since_payment'):
                    response += f' (Hace {p["days_since_payment"]} días)'
            return response

        else:
            return answer_business_question(message)

    except Exception as e:
        logger.error(f'Error processing v5 intent {intent}: {e}')
        return f'Error: {str(e)[:60]}'


def _build_result(intent, response, params, confidence, action, **extra):
    result = {
        'intent': intent,
        'response': response,
        'parameters': params,
        'confidence': confidence,
        'action': action,
        'tutorial_steps': [],
    }
    result.update(extra)
    return result


def _llm_fallback_chain(system_prompt: str, msg: str) -> str:
    messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': msg}]

    try:
        from groq import Groq

        groq_key = os.getenv('GROQ_API_KEY')
        if groq_key:
            client = Groq(api_key=groq_key)
            resp = client.chat.completions.create(
                model='llama-3.1-8b-instant', messages=messages, temperature=0.3, max_tokens=2000
            )
            if resp.choices[0].message.content:
                return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f'Groq falló: {e}')

    try:
        import google.generativeai as genai

        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key:
            genai.configure(api_key=gemini_key)
            gemini_resp = genai.GenerativeModel('gemini-1.5-flash').generate_content(
                f'{system_prompt}\n\nUsuario: {msg}'
            )
            if gemini_resp.text:
                return gemini_resp.text
    except Exception as e:
        logger.warning(f'Gemini falló: {e}')

    try:
        import requests

        ollama_resp = requests.post(
            f'{os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")}/api/chat',
            json={'model': os.getenv('OLLAMA_MODEL', 'llama3.1:8b'), 'messages': messages, 'stream': False},
            timeout=30,
        )
        if ollama_resp.ok:
            content = ollama_resp.json().get('message', {}).get('content', '')
            if content:
                return content
    except Exception as e:
        logger.error(f'Ollama falló: {e}')

    return 'Lo siento, no pude conectar con ningún proveedor de IA. Verifica las API keys o la conexión a Internet.'


def process_chat_enhanced_v5(uid: int, msg: str, cid=None, pg='dashboard'):
    try:
        page_ctx = get_page_context_suggestions(pg)

        if msg.strip() == 'context_init':
            return _build_result(
                'context_init',
                page_ctx.get('welcome', '¡Hola! ¿En qué puedo ayudarte?'),
                {},
                0,
                'context_loaded',
            )

        context_text = get_cached_context_text()
        intent, params, confidence, clarification = detect_user_intent_v5(msg)
        logger.info(f'Detected v5: intent={intent}, confidence={confidence:.2f}, params={params}')

        try:
            track_workflow(intent, params)
            next_action = predict_next_action(intent)
        except Exception:
            next_action = None

        if clarification:
            return _build_result(intent, clarification, params, confidence, 'clarification_needed')

        if intent in INTENTS_WITH_DATA:
            response = process_intent_with_data_v5(intent, params, msg)
            result = _build_result(intent, response, params, confidence, 'data_processed')

        elif intent == 'navigation':
            redirect_url = get_navigation_url(params.get('target_section', 'dashboard'), uid)
            result = _build_result(
                intent,
                f'Llevandote a {params.get("target_section", "dashboard")}...',
                params,
                confidence,
                'navigate',
                redirect=redirect_url,
                tutorial_steps=get_tutorial_steps('navigation', params.get('target_section', 'dashboard')),
            )

        elif intent == 'register_payment':
            invalidate_context()
            patient_name = params.get('patient_name', 'alumno')
            amount = params.get('amount', 0)
            result = _build_result(
                intent,
                f'Pago Registrado\n\nCantidad: S/. {amount:.2f}\nAlumno: {patient_name}\n\nContexto actualizado - Proxima consulta tendra datos actualizados',
                params,
                confidence,
                'register_payment',
            )

        elif intent == 'create_appointment':
            result = _build_result(
                intent,
                f'Creando sesión para {params.get("patient_name", "?")} el {params.get("day", "")}...',
                params,
                confidence,
                'create_appointment',
            )

        elif intent == 'create_user':
            invalidate_context()
            user_name = params.get('patient_name', 'usuario')
            result = _build_result(
                intent,
                f"""Nuevo Usuario Creado

Nombre: {user_name}

Pasos Siguientes:
  1. Configura el email del usuario
  2. Asigna un plan de pago
  3. Establece terapeuta responsable
  4. Crea sesiones

Contexto actualizado""",
                params,
                confidence,
                'create_user',
            )

        else:
            from app.services.functions_trainer_service import functions_trainer

            system_prompt = f"""Eres asistente inteligente del Centro de Terapias Juan Pablo II.

{context_text}

{functions_trainer.get_functions_prompt()}

RESPUESTAS:
- Si el usuario pregunta por datos, cita cifras EXACTAS del contexto
- Si pide crear/registrar algo, usa la función apropiada
- Se practico, conciso y util
- Siempre usa los datos reales proporcionados"""

            response = _llm_fallback_chain(system_prompt, msg)
            result = _build_result(intent, response, params, confidence, 'general_chat', context_loaded=True)

        if next_action:
            result['next_predicted_action'] = next_action
            logger.info(f'Proxima accion sugerida: {next_action}')

        result['action_chips'] = page_ctx.get('action_chips', [])
        result['suggestions'] = page_ctx.get('suggestions', [])

        return result

    except Exception as e:
        logger.error(f'Error in v5: {e}', exc_info=True)
        return _build_result('error', f'Error: {str(e)[:50]}', {}, 0, 'error')


def save_chat_message(conversation_id, role, content, intent=None, parameters=None, action_status=None):
    from app.models import AIChatMessage

    result = db.session.execute(
        AIChatMessage.__table__.insert().values(
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            parameters=parameters if isinstance(parameters, dict) else {},
            action_status=action_status,
        )
    )
    db.session.commit()
    return result.inserted_primary_key[0]


def get_navigation_url(section, user_id):
    from flask import url_for

    ep = NAV_URL_MAP.get(section.lower(), 'admin.dashboard')
    try:
        return url_for(ep)
    except Exception:
        return url_for('admin.dashboard')


def get_tutorial_steps(action, section=None):
    if action == 'navigation':
        return [{'step': 1, 'action': f'navegar_a_{section}', 'description': f'Ir a {section}'}]
    if action == 'register_payment':
        return [
            {'step': 1, 'action': 'buscar_paciente', 'description': 'Buscar paciente'},
            {'step': 2, 'action': 'registrar_pago', 'description': 'Registrar pago'},
        ]
    return []


def extract_payment_details(message):
    result = {}
    m_patient = re.search(r'(?:para|de|paciente)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)?)', message, re.I)
    if m_patient:
        result['patient_name'] = m_patient.group(1).strip()
    m_amount = re.search(r'(?:S/?\.?\s*)?(\d+[\.,]?\d*)\s*(?:soles)?', message)
    if m_amount:
        result['amount'] = m_amount.group(1).replace(',', '.')
    m_ref = re.search(r'(?:ref|referencia|voucher)\s*[:\s]+([A-Za-z0-9]+)', message, re.I)
    if m_ref:
        result['reference'] = m_ref.group(1).strip()
    return result


def validate_payment_parameters(params):
    if not params.get('patient_name'):
        return False, 'Falta nombre del paciente'
    if not params.get('amount'):
        return False, 'Falta monto del pago'
    try:
        float(params['amount'])
    except (ValueError, TypeError):
        return False, 'Monto invalido'
    return True, ''


def validate_expense_parameters(params):
    if not params.get('amount'):
        return False, 'Falta monto del gasto'
    if not params.get('category'):
        return False, 'Falta categoria del gasto'
    try:
        float(params['amount'])
    except (ValueError, TypeError):
        return False, 'Monto invalido'
    return True, ''


ADMIN_PAGE_CONTEXT = {
    'dashboard': {
        'welcome': 'Panel de administración del Centro. Puedo ayudarte con finanzas, usuarios, sesiones y más.',
        'suggestions': ['Ver deudores', 'Registrar pago', 'Crear usuario', 'Ir a finanzas', 'Ver reporte'],
        'action_chips': [
            {'id': 'fin', 'label': 'Finanzas', 'icon': 'chart-line', 'type': 'navigation', 'target': '/admin/finanzas'},
            {'id': 'usr', 'label': 'Usuarios', 'icon': 'users', 'type': 'navigation', 'target': '/admin/users'},
            {'id': 'ses', 'label': 'Sesiones', 'icon': 'calendar', 'type': 'navigation', 'target': '/admin/sessions'},
            {'id': 'rep', 'label': 'Reportes', 'icon': 'chart-bar', 'type': 'navigation', 'target': '/admin/reports'},
        ],
    },
    'finanzas': {
        'welcome': 'Gestión financiera del centro. Puedo ayudarte con pagos, gastos y análisis.',
        'suggestions': ['Ver ingresos', 'Deudores', 'Registrar pago', 'Ver gastos', 'Análisis financiero'],
        'action_chips': [
            {
                'id': 'pago',
                'label': 'Registrar Pago',
                'icon': 'dollar-sign',
                'type': 'modal',
                'target': 'registerPayment',
            },
            {'id': 'gast', 'label': 'Ver Gastos', 'icon': 'receipt', 'type': 'navigation', 'target': '/admin/expenses'},
            {
                'id': 'yape',
                'label': 'Importar Yape',
                'icon': 'mobile',
                'type': 'navigation',
                'target': '/admin/yape-import',
            },
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/finanzas'},
        ],
    },
    'payments': {
        'welcome': 'Gestión de cobros y pagos. Puedo ayudarte a registrar pagos y ver historial.',
        'suggestions': ['Registrar pago', 'Ver historial', 'Deudores de la semana', 'Exportar datos'],
        'action_chips': [
            {
                'id': 'pago',
                'label': 'Registrar Pago',
                'icon': 'dollar-sign',
                'type': 'modal',
                'target': 'registerPayment',
            },
            {'id': 'hist', 'label': 'Historial', 'icon': 'history', 'type': 'navigation', 'target': '/admin/payments'},
            {'id': 'fin', 'label': 'Finanzas', 'icon': 'chart-line', 'type': 'navigation', 'target': '/admin/finanzas'},
        ],
    },
    'users': {
        'welcome': 'Gestión de usuarios del centro. Puedo ayudarte a crear, buscar o gestionar usuarios.',
        'suggestions': ['Crear usuario', 'Ver terapeutas', 'Buscar paciente', 'Usuarios deudores'],
        'action_chips': [
            {'id': 'cusr', 'label': 'Crear Usuario', 'icon': 'user-plus', 'type': 'modal', 'target': 'createUser'},
            {'id': 'ter', 'label': 'Terapeutas', 'icon': 'user-doctor', 'type': 'filter', 'target': 'terapista'},
            {'id': 'pac', 'label': 'Pacientes', 'icon': 'user', 'type': 'filter', 'target': 'jugador'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/users'},
        ],
    },
    'sedes': {
        'welcome': 'Gestión de sedes del centro. Puedo ayudarte a crear o administrar sedes.',
        'suggestions': ['Crear sede', 'Ver pacientes por sede', 'Estadísticas de sede'],
        'action_chips': [
            {'id': 'csed', 'label': 'Nueva Sede', 'icon': 'building', 'type': 'modal', 'target': 'createSede'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/sedes'},
        ],
    },
    'sessions': {
        'welcome': 'Calendario de sesiones. Puedo ayudarte a programar o gestionar sesiones.',
        'suggestions': ['Crear sesión', 'Ver próximas', 'Sesiones de hoy', 'Buscar por paciente'],
        'action_chips': [
            {
                'id': 'cses',
                'label': 'Nueva Sesión',
                'icon': 'calendar-plus',
                'type': 'modal',
                'target': 'createSession',
            },
            {'id': 'cal', 'label': 'Calendario', 'icon': 'calendar', 'type': 'scroll', 'target': 'calendar-widget'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/sessions'},
        ],
    },
    'expenses': {
        'welcome': 'Nómina y gastos operativos. Puedo ayudarte a registrar gastos o ver la nómina.',
        'suggestions': ['Registrar gasto', 'Ver nómina', 'Gastos del mes', 'Pagar terapeuta'],
        'action_chips': [
            {'id': 'gast', 'label': 'Registrar Gasto', 'icon': 'receipt', 'type': 'modal', 'target': 'registerExpense'},
            {'id': 'nom', 'label': 'Nómina', 'icon': 'file-invoice-dollar', 'type': 'scroll', 'target': 'table'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/expenses'},
        ],
    },
    'reports': {
        'welcome': 'Reportes y análisis del centro. Puedo generar reportes o exportar datos.',
        'suggestions': ['Generar reporte', 'Exportar CSV', 'Análisis IA', 'Ver métricas'],
        'action_chips': [
            {'id': 'gen', 'label': 'Generar Reporte', 'icon': 'file-alt', 'type': 'action', 'target': 'generateReport'},
            {'id': 'csv', 'label': 'Exportar CSV', 'icon': 'download', 'type': 'action', 'target': 'exportCSV'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/reports'},
        ],
    },
    'messages': {
        'welcome': 'Bandeja de mensajes. Puedo ayudarte a gestionar comunicaciones.',
        'suggestions': ['Ver mensajes no leídos', 'Enviar broadcast', 'Responder por WhatsApp'],
        'action_chips': [
            {'id': 'bcast', 'label': 'Broadcast', 'icon': 'paper-plane', 'type': 'modal', 'target': 'broadcastMessage'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/messages'},
        ],
    },
    'games': {
        'welcome': 'Catálogo de juegos terapéuticos. Puedo ayudarte a subir o gestionar juegos.',
        'suggestions': ['Subir juego', 'Ver catálogo', 'Juegos populares'],
        'action_chips': [
            {'id': 'cgame', 'label': 'Subir Juego', 'icon': 'gamepad', 'type': 'modal', 'target': 'uploadGame'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/games'},
        ],
    },
    'logs': {
        'welcome': 'Visor de logs del sistema. Puedo ayudarte a filtrar o buscar errores.',
        'suggestions': ['Ver errores', 'Buscar warning', 'Logs recientes'],
        'action_chips': [
            {'id': 'err', 'label': 'Solo Errores', 'icon': 'exclamation-triangle', 'type': 'filter', 'target': 'ERROR'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/logs'},
        ],
    },
    'profile': {
        'welcome': 'Tu perfil de administrador. Puedo ayudarte a actualizar tu información.',
        'suggestions': ['Cambiar contraseña', 'Actualizar nombre', 'Ver configuración'],
        'action_chips': [
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/profile'},
        ],
    },
    'yape-import': {
        'welcome': 'Importación de transacciones Yape. Puedo ayudarte a subir archivos.',
        'suggestions': ['Importar archivo', 'Ver pendientes', 'Reconciliar pagos'],
        'action_chips': [
            {'id': 'imp', 'label': 'Importar', 'icon': 'upload', 'type': 'modal', 'target': 'importYape'},
            {'id': 'wiz', 'label': 'Guía', 'icon': 'question-circle', 'type': 'wizard', 'target': '/admin/yape-import'},
        ],
    },
    'api-tokens': {
        'welcome': 'Gestión de tokens de API. Puedo ayudarte a generar o revocar tokens.',
        'suggestions': ['Generar token', 'Ver tokens activos', 'Revocar token'],
        'action_chips': [
            {'id': 'gen', 'label': 'Generar Token', 'icon': 'key', 'type': 'modal', 'target': 'generateToken'},
        ],
    },
    'ai': {
        'welcome': 'Entrenamiento de IA. Puedo ayudarte a mejorar las respuestas del sistema.',
        'suggestions': ['Ver precisión', 'Entrenar modelo', 'Revisar intentos fallidos'],
        'action_chips': [],
    },
    'csp-reports': {
        'welcome': 'Reportes CSP. Puedo ayudarte a revisar reportes de contenido.',
        'suggestions': ['Ver reportes', 'Filtrar por estado'],
        'action_chips': [],
    },
}


def get_page_context_suggestions(page: str, role: str = 'admin') -> dict:
    ctx = ADMIN_PAGE_CONTEXT.get(page, ADMIN_PAGE_CONTEXT.get('dashboard', {}))
    return {
        'welcome': ctx.get('welcome', ''),
        'suggestions': ctx.get('suggestions', []),
        'action_chips': ctx.get('action_chips', []),
    }
