import json
import logging
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.llm_client import llm_chat
from app.services.personality_prompt import LOCAL_BASE_PROMPT, PERSONALITY_PROMPT, ROLE_NAMES_ES
from app.services.tools_registry import SAFE_WRITE_TOOLS, TOOL_REGISTRY, execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

MAX_TOOL_RESULT_CHARS = 1500
LOCAL_MAX_TOOLS = 14

LIMA_TZ = ZoneInfo('America/Lima')

_DIAS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
_MESES_ES = [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
]


def get_current_date_context():
    """Fecha actual en America/Lima para que el LLM nunca adivine 'hoy'."""
    now = datetime.now(LIMA_TZ)
    fecha = f'{_DIAS_ES[now.weekday()]} {now.day} de {_MESES_ES[now.month - 1]} de {now.year}'
    return (
        f"Hoy es {fecha}. Usa SIEMPRE esta fecha como referencia para 'hoy'. "
        'Todos los usuarios están en la zona horaria America/Lima (UTC-5).'
    )


SYSTEM_PROMPTS = {
    'admin': (
        'Eres Diego, el asistente de IA del Centro Juan Pablo II, un centro de salud mental en Perú.\n'
        'Eres un chatbot de ERP que ejecuta ACCIONES REALES en el sistema.\n\n'
        'CRITICAL RULES:\n'
        '- ALWAYS respond in Spanish.\n'
        '- Be concise: max 3-5 lines per response.\n'
        '- NEVER invent, guess, or fabricate ANY data. ONLY use EXACT values from tool results.\n'
        '- NEVER generate HTML, JavaScript, CSS, or code. You are a chatbot, not a code generator.\n'
        '- NEVER output code blocks, <html>, <script>, <table>, or any markup.\n'
        '- If you don\'t have data from a tool, and a tool exists that could answer the question, ALWAYS call that tool first. Only reply "No tengo esos datos" after calling a tool and receiving no data.\n'
        '- NEVER modify, estimate, or "fill in" values. Report EXACTLY what the tool returned.\n'
        '- If a tool result is truncated, say "el resultado fue truncado" and show what you received.\n'
        '- NEVER show your reasoning process. Only show the final result.\n'
        '- When listing items, show a SHORT summary (count + first 5 names).\n'
        '- For payments: ALWAYS ask patient, amount, method, date BEFORE registering.\n'
        '- Before deleting, confirm with the user.\n\n'
        'TOOL FORMAT (you MUST call tools to get real data):\n'
        'Option 1: <function=search_patients{"query": "Carlos"}</function>\n'
        'Option 2: search_patients(query: "Carlos")\n'
        'Both formats work. ALWAYS include the arguments.\n'
        'WRONG: search_patients  <- missing arguments, WILL FAIL\n\n'
        'EXAMPLE of a correct tool call:\n'
        'User: "Busca al paciente Carlos"\n'
        'You: <function=search_patients{"query": "Carlos"}</function>\n\n'
        'EXAMPLE with multiple params:\n'
        'User: "Registra pago de Juan por 100 soles en efectivo"\n'
        'You: <function=register_payment{"patient_id": 5, "amount": 100, "method": "Efectivo", "payment_date": "2026-08-18"}</function>\n\n'
        'TOOLS BY CATEGORY:\n\n'
        'PATIENTS/USERS: search_patients, list_patients, get_patient_detail, list_users, get_therapist_patients (pacientes asignados a un terapeuta), get_user_detail, create_user, delete_user, assign_therapist, update_patient, toggle_user_status\n'
        'SESSIONS: get_sessions, get_sessions_day, schedule_programmed_session, update_session_plan, cancel_session, complete_session, batch_create_sessions\n'
        'INCIDENTS: create_incident, list_incidents, get_incident_detail, update_incident_status, assign_incident\n'
        'BRANCHES: list_sedes, get_sede_stats, list_patient_groups, create_patient_group\n'
        'FINANCE: get_financial_summary (use month/year params for past months), get_payment_history, register_payment, cancel_payment (delete a payment by ID), edit_payment (modify amount/method/date/status/receipt_url), get_debtors, send_payment_reminder, list_expenses, create_expense, get_therapist_financials, get_debt_summary, compare_periods (compare 2 months)\n'
        'REPORTS: generate_weekly_report, get_weekly_summary, get_monthly_reports, get_therapist_efficiency, get_user_growth (user registration metrics by month)\n'
        'MESSAGING: broadcast_message, send_direct_message, get_notifications, mark_notifications_read\n'
        'CONTRACTS: list_contracts\n\n'
        'PAYMENT WORKFLOW:\n'
        '1. search_patients to find the patient ID\n'
        '2. Ask: amount, method (Efectivo/Yape/Transferencia/IA/Copilot), date\n'
        '3. Only THEN call register_payment with ALL 4 params\n'
        '4. Confirm the result\n\n'
        'VOUCHER IMAGE PROCESSING:\n'
        'When user sends an image (voucher/comprobante):\n'
        '1. The frontend uploads image to /mcp/upload and gets OCR data\n'
        '2. OCR extracts: amount, method, date, patient_hint\n'
        '3. Use ONLY the OCR data provided - NEVER invent or guess values\n'
        '4. If OCR returns null for a field, ASK the user for that data\n'
        '5. Confirm all extracted data with user before registering\n'
        '6. Store image URL as receipt_url in the payment\n'
        '7. NEVER say "Juan Pérez" or "S/100" if OCR did not return those values\n\n'
        'EDITING PAYMENTS:\n'
        '1. get_payment_history(patient_id) to find the payment ID\n'
        '2. edit_payment(payment_id, amount=..., method=..., payment_date=..., status=..., receipt_url=...)\n'
        '3. Confirm changes to user\n\n'
        'DELETING PAYMENTS:\n'
        '1. get_payment_history(patient_id) to find the payment ID\n'
        '2. Show user the payment details and ask for confirmation\n'
        '3. cancel_payment(payment_id) — ONLY after user confirms\n\n'
        'FINANCIAL QUERIES:\n'
        '- get_financial_summary with month=5, year=2026 for May 2026\n'
        '- ALWAYS include year parameter (current year is 2026)\n'
        '- compare_periods to compare any two months side by side\n'
        '- get_user_growth for registration trends\n\n'
        'MESSAGING WORKFLOW:\n'
        '1. search_patients or list_users to find the user ID\n'
        '2. send_direct_message with receiver_id AND content (BOTH required)\n'
    ),
    'supervisor': (
        'You are the AI assistant for Centro Juan Pablo II.\n'
        'You can query patients, sessions, payments, incidents, reports, branches, contracts.\n'
        'You can create sessions, incidents, users, groups, expenses and update data.\n'
        'Respond in Spanish, max 5 lines. Use tools for real data.\n'
        'For payments ask: patient, amount, method, date BEFORE registering.\n'
        'NEVER show your internal process. Only the final result.\n'
        'TOOL FORMAT: <function=name{"param": "value"}</function>  ← ALWAYS include JSON args\n'
    ),
    'terapista': (
        'You are the AI assistant for Centro Juan Pablo II.\n'
        'You can view your sessions, assigned patients, weekly/monthly reports.\n'
        'You can create sessions, complete them, cancel them and generate reports.\n'
        'Respond in Spanish, max 5 lines.\n'
        'NEVER show your internal process. Only the final result.\n'
        'TOOL FORMAT: <function=name{"param": "value"}</function>  ← ALWAYS include JSON args\n'
    ),
    'jugador': (
        'You are the AI assistant for Centro Juan Pablo II.\n'
        'You can view your sessions and profile.\n'
        'Respond in Spanish, max 3 lines.\n'
    ),
}


def get_configured_system_prompt():
    """Prompt editado en el módulo de configuración del bot, si existe."""
    try:
        from app.models.bot_config import BotConfig

        configured = (BotConfig.get_or_create().system_prompt or '').strip()
        return configured or None
    except Exception:
        return None


def _substitute_tokens(prompt, user_role, user_id):
    prompt = prompt.replace('{rol}', ROLE_NAMES_ES.get(user_role, user_role))
    prompt = prompt.replace('{rol_id}', user_role)
    prompt = prompt.replace('{user_id}', str(user_id or ''))
    try:
        from app.models import User

        u = User.query.get(int(user_id)) if user_id else None
        name = ''
        if u:
            name = getattr(u, 'full_name', None) or getattr(u, 'username', '') or ''
        prompt = prompt.replace('{usuario}', name)
    except Exception:
        pass
    return prompt


def get_role_access_block(user_role, mode='grande'):
    """Refuerza en runtime qué puede y qué NO puede hacer el rol actual."""
    role_name = ROLE_NAMES_ES.get(user_role, user_role)
    allowed = get_tools_for_mode(mode, user_role)
    names = ', '.join(t['function']['name'] for t in allowed) or 'ninguna'
    return (
        f'\n\nACCESO Y PERMISOS DEL USUARIO (nivel: {role_name}):\n'
        f'- Herramientas permitidas para tu nivel (SOLO estas): {names}\n'
        '- NO puedes usar ninguna otra herramienta ni elevar tu nivel de acceso.\n'
        '- PROHIBIDO: inventar resultados, afirmar que una operación se completó sin confirmación '
        'de la herramienta, y ejecutar acciones de escritura sin confirmación del usuario.\n'
        '- Si el usuario pide algo fuera de tu nivel de acceso, responde que no tienes permisos '
        'y sugiere solicitarlo al administrador o supervisor.'
    )


def resolve_system_prompt(user_role, user_id=None, mode='grande'):
    """Prompt base: configuración del bot > prompt de personalidad, + acceso según rol."""
    configured = get_configured_system_prompt()
    base = configured if configured else PERSONALITY_PROMPT
    base = _substitute_tokens(base, user_role, user_id)
    base += get_role_access_block(user_role, mode=mode)
    return base


MAX_ITERATIONS = 6

# Copia del patrón de mcp_routes (sin imports circulares): la respuesta del
# modelo afirma una CANTIDAD o dato del sistema sin haber ejecutado herramienta.
_DATA_CLAIM_RE = re.compile(
    r'(?:hay|existen|son|total(?:\s+dé\s+|de\s+)?|registrad[oa]s?|encontrad[oa]s?|tienen?|cuenta\s+con)\s*[:>]*\s*\d{1,4}'
    r'|\b\d{1,4}\s+(?:terapeutas?|paciente[s]?|usuarios?|alumnos?|sesiones?|pagos?|sede[s]?|contratos?|incidentes?|grupos?)\b',
    re.IGNORECASE,
)

TOOL_CALL_PATTERN = re.compile(
    r'<function=(\w+)\s*(\{.*?\})?\s*(?:</function>|' + r'/\s*' + r'>)',
    re.DOTALL,
)

# Broader fallback patterns for small models that deviate from the exact format
_FALLBACK_PATTERNS = [
    # Without braces: <function=search_patients</function> or <function=search_patients></function>
    re.compile(r'<function=(\w+)\s*</function>', re.DOTALL),
    # With single quotes: <function=search_patients{'query': 'Carlos'}</function>
    re.compile(r"<function=(\w+)\s*(' .*?')\s*</function>", re.DOTALL),
    # Markdown code block: ```function=search_patients{...}```
    re.compile(r'```[^`]*<function=(\w+)\s*(\{.*?\})?\s*</function>', re.DOTALL),
    # Partial: search_patients{"query":"Carlos"} (no <function> tags)
    re.compile(r'\b(\w+)\s*(\{[^{}]*\})\s*(?:->|$|\n)', re.DOTALL),
    # Markdown block: ```tool_code list_users({"role": "terapista"})
    re.compile(r'```[^\n]*\n?\s*(\w+)\s*\(\s*(\{[^{}]*\})\s*\)\s*```'),
]

# Pattern for parentheses format: toolname(key: value, key: value)
_PAREN_PATTERN = re.compile(
    r'(\w+)\s*\(([^)]*)\)',
    re.DOTALL,
)


def _parse_paren_args(args_str):
    """Parse 'key: value, key: value' from parentheses format."""
    result = {}
    if not args_str or not args_str.strip():
        return result
    # Split by comma, but handle quoted strings
    parts = []
    current = ''
    in_quote = False
    quote_char = None
    for ch in args_str:
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            current += ch
        elif ch == quote_char and in_quote:
            in_quote = False
            quote_char = None
            current += ch
        elif ch == ',' and not in_quote:
            parts.append(current.strip())
            current = ''
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())

    for part in parts:
        if ':' in part:
            key, _, value = part.partition(':')
            key = key.strip().strip('"').strip("'")
            value = value.strip().strip('"').strip("'")
            # Try to parse as int/float
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            result[key] = value
    return result


def _parse_text_tool_call(text):
    """Extract tool name and args from various tool call formats."""
    # Try strict pattern first
    match = TOOL_CALL_PATTERN.search(text)
    if match:
        tool_name = match.group(1)
        args_str = match.group(2)
        if args_str:
            try:
                tool_args = json.loads(args_str)
            except json.JSONDecodeError:
                tool_args = {}
        else:
            tool_args = {}
        # Only return if the tool name is actually registered
        if tool_name in TOOL_REGISTRY:
            return tool_name, tool_args

    # Try fallback patterns
    for pattern in _FALLBACK_PATTERNS:
        match = pattern.search(text)
        if match:
            tool_name = match.group(1)
            args_str = match.group(2) if match.lastindex >= 2 else None
            if tool_name not in TOOL_REGISTRY:
                continue
            if args_str:
                # Try to fix single quotes to double quotes
                fixed = args_str.replace("'", '"')
                try:
                    tool_args = json.loads(fixed)
                except json.JSONDecodeError:
                    tool_args = {}
            else:
                tool_args = {}
            return tool_name, tool_args

    # Try parentheses format: toolname(key: value, key: value)
    for match in _PAREN_PATTERN.finditer(text):
        tool_name = match.group(1)
        args_str = match.group(2)
        if tool_name in TOOL_REGISTRY:
            cleaned = (args_str or '').strip()
            if cleaned.startswith('{'):
                # JSON inside parens – fix single quotes → double quotes, remove trailing commas
                fixed = re.sub(r',\s*([}\]])', r'\1', cleaned.replace("'", '"'))
                try:
                    tool_args = json.loads(fixed)
                except json.JSONDecodeError:
                    tool_args = _parse_paren_args(args_str)
            else:
                tool_args = _parse_paren_args(args_str)
            return tool_name, tool_args

    return None, None


def _readable_name_list(items):
    """Build a verbatim numbered list (name/dni/email) for list results so the
    small model copies exact values instead of hallucinating."""
    lines = []
    ok = False
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            continue
        name = it.get('username') or it.get('full_name') or it.get('name') or it.get('patient_name') or it.get('title')
        label = name if name else it.get('email') or str(it.get('id', '?'))
        lines.append(f'{i}. {label}')
        ok = True
    return ok, '\n'.join(lines)


def _trim_tool_result(result, max_chars=MAX_TOOL_RESULT_CHARS):
    """Trim tool result to avoid blowing up the context window."""
    if isinstance(result, dict):
        # For list results, keep count + first few items
        if 'debtors' in result:
            payload = result.get('debtors')
            if isinstance(payload, dict):
                payload = payload.get('data') if isinstance(payload.get('data'), dict) else payload
                por_sede = payload.get('por_sede') or {}
                deudores = []
                for sede_id in sorted(por_sede, key=int, reverse=True):
                    deudores.extend((por_sede[sede_id] or {}).get('deudores') or [])
                result = {
                    'success': result.get('success', True),
                    'count': result.get('count', len(deudores)),
                    'deudores': deudores[:8],
                    'note': (
                        f'Showing {min(8, len(deudores))} of {len(deudores)} deudores' if len(deudores) > 8 else None
                    ),
                }
        elif 'patients' in result and isinstance(result['patients'], list):
            patients = result['patients']
            result = {
                'success': result.get('success', True),
                'count': result.get('count', len(patients)),
                'patients_preview': patients[:5],
                'note': f'Showing 5 of {len(patients)} patients' if len(patients) > 5 else None,
            }
        elif 'users' in result and isinstance(result['users'], list):
            users = result['users']
            read_ok, read_list = _readable_name_list(users)
            result = {
                'success': result.get('success', True),
                'count': result.get('count', len(users)),
                'users': users[:50],
                'readable_list': read_list,
                'note': (
                    f'Showing {min(50, len(users))} of {len(users)} users'
                    if len(users) > 50
                    else ('Copia "readable_list" y "users" TAL CUAL en tu respuesta.' if read_ok else None)
                ),
            }
        elif 'payments' in result and isinstance(result['payments'], list):
            payments = result['payments']
            result = {
                'success': result.get('success', True),
                'patient': result.get('patient'),
                'total_payments': len(payments),
                'payments': payments[:10],
                'note': f'Showing {min(10, len(payments))} of {len(payments)} payments' if len(payments) > 10 else None,
            }
        elif 'sessions' in result and isinstance(result['sessions'], list):
            sessions = result['sessions']
            result = {
                'success': result.get('success', True),
                'count': result.get('count', len(sessions)),
                'sessions': sessions[:5],
                'note': f'Showing {min(5, len(sessions))} of {len(sessions)} sessions' if len(sessions) > 5 else None,
            }

    result_str = json.dumps(result, ensure_ascii=False, default=str)
    if len(result_str) > max_chars:
        result_str = result_str[:max_chars] + '... [truncated]'
    return result_str


def _is_ollama_primary():
    """True cuando el proveedor activo es Ollama local (qwen/minicpm/gemma)."""
    try:
        from flask import current_app

        pref = os.environ.get('LLM_PROVIDER') or current_app.config.get('LLM_PROVIDER')
    except Exception:
        pref = os.environ.get('LLM_PROVIDER')
    return (pref or '').lower() == 'ollama'


_INTENT_GROUPS = {
    'pagos': {
        'search_patients',
        'get_payment_history',
        'register_payment',
        'register_payment_with_evidence',
        'cancel_payment',
        'edit_payment',
        'get_debtors',
        'get_current_datetime',
    },
    'finanzas': {
        'get_financial_summary',
        'compare_periods',
        'get_user_growth',
        'get_therapist_financials',
        'get_monthly_collection',
        'get_upcoming_installments',
        'get_payment_history',
        'get_current_datetime',
        'get_debtors',
        'get_monthly_reports',
    },
    'sesiones': {
        'get_sessions',
        'get_sessions_day',
        'schedule_programmed_session',
        'update_session_plan',
        'cancel_session',
        'complete_session',
        'batch_create_sessions',
        'search_patients',
        'get_current_datetime',
    },
    'pacientes': {
        'search_patients',
        'list_patients',
        'get_patient_detail',
        'get_patient_stats',
        'update_patient_profile',
        'update_patient_details',
        'create_full_patient',
        'assign_therapist',
        'get_therapist_patients',
        'get_current_datetime',
    },
    'usuarios': {
        'list_users',
        'get_user_detail',
        'create_user',
        'delete_user',
        'toggle_user_status',
        'assign_therapist_to_sede',
        'get_current_datetime',
    },
    'incidentes': {
        'create_incident',
        'list_incidents',
        'get_incident_detail',
        'update_incident_status',
        'assign_incident',
        'search_patients',
        'get_current_datetime',
    },
    'mensajeria': {
        'broadcast_message',
        'send_direct_message',
        'get_notifications',
        'mark_notifications_read',
        'list_users',
        'search_patients',
        'get_current_datetime',
    },
    'reportes': {
        'generate_weekly_report',
        'get_weekly_summary',
        'get_monthly_reports',
        'get_therapist_efficiency',
        'get_financial_summary',
        'get_current_datetime',
    },
    'contratos': {
        'list_contracts',
        'create_service_contract',
        'get_contract_detail',
        'get_contracts_filtered',
        'get_due_installments',
        'update_contract',
        'cancel_contract',
        'reactivate_contract',
        'get_current_datetime',
    },
    'general': {
        'search_patients',
        'list_patients',
        'list_users',
        'get_patient_detail',
        'get_current_datetime',
        'list_sedes',
        'get_notifications',
    },
}

_INTENT_KEYWORDS = {
    'pagos': ('pago', 'pagar', 'pagó', 'pagos', 'abono', 'deuda', 'deudor', 'saldo', 'voucher', 'comprobante'),
    'finanzas': (
        'financ',
        'ingreso',
        'egreso',
        'mensual',
        'utilidad',
        'ganancia',
        'recaud',
        'deuda',
        'deudor',
        'colecci',
    ),
    'sesiones': ('sesi', 'cita', 'agenda', 'agendar', 'programar', 'turno', 'horario', 'atender'),
    'pacientes': ('paciente', 'busca', 'buscar', 'ficha', 'perfil', 'historia'),
    'usuarios': ('usuario', 'staff', 'terapeuta', 'cuenta', 'acceso', 'alta', 'baja'),
    'incidentes': ('incidente', 'queja', 'reclamo', 'reporta', 'incidenc'),
    'mensajeria': ('mensaj', 'notificac', 'avis', 'contactar', 'enviar'),
    'reportes': ('reporte', 'resumen', 'semanal', 'semana', 'mensual'),
    'contratos': ('contrato', 'plan', 'cuota', 'instalment', 'matricula', 'pension'),
}

_ALWAYS_LOCAL_TOOLS = {'get_current_datetime', 'search_patients'}


_SMALLTALK_RE = re.compile(
    r'^\s*[¿¡]?\s*(?:'
    r'hola[\s\.,!?]*.*|buenas(?: tardes| noches| dias)?[\s\.,!?]*.*|'
    r'buenos dias[\s\.,!?]*.*|gracias?[\s\.,!?]*.*|ok|okay|dale|perfecto|listo|genial|excelente|'
    r'bien y tu\??|como estas|cómo estás|chau|hasta luego|bye|adios|adiós|'
    r'(?:quien|qué|que) (?:eres|sos|es)\??[^\n]{0,30}|a (?:que|qué) te dedicas|que sabes hacer|qué sabes hacer|'
    r'(?:eres|sois|es) (?:un|una|el|la) (?:bot|robot|ia|asistente)|test|prueba'
    r')[\s\.,!?]*$',
    re.IGNORECASE,
)


def _is_smalltalk(message):
    """True si el mensaje es pura conversación casual (no requiere tools)."""
    return bool(_SMALLTALK_RE.match((message or '').strip()))


def _select_local_tools(tools, message):
    """Selecciona un subconjunto relevante de tools para el LLM local (CPU):
    filtra por intención del mensaje y siempre incluye los esenciales.
    Mantiene el prompt pequeño -> prefill rápido (clave para <10s)."""
    msg = (message or '').lower()
    wanted = set(_ALWAYS_LOCAL_TOOLS)
    hit = False
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(k in msg for k in keywords):
            wanted |= _INTENT_GROUPS.get(intent, set())
            hit = True
    if not hit:
        wanted |= _INTENT_GROUPS['general']
    selected = [t for t in tools if t['function']['name'] in wanted]
    if len(selected) > LOCAL_MAX_TOOLS:
        extra = [t for t in selected if t['function']['name'] not in _ALWAYS_LOCAL_TOOLS]
        extra.sort(key=lambda t: TOOL_REGISTRY.get(t['function']['name'], {}).get('category', 'read') != 'read')
        selected = [t for t in selected if t['function']['name'] in _ALWAYS_LOCAL_TOOLS] + extra[
            : LOCAL_MAX_TOOLS - len(_ALWAYS_LOCAL_TOOLS)
        ]
    return [_compact_local_schema(t) for t in selected]


# Mapa determinista intención -> tool de reporte (sin args requeridos).
# Se usa SOLO como fallback cuando el router local (Qwen) no emite tool call
# ante una consulta de datos inequívoca sobre reportes sin parámetros.
_LOCAL_FORCE_TOOLS = (
    ('get_debtors', ('moroso', 'morosos', 'deudor', 'deudores', 'cuanto debe', 'deuda', 'saldos pendientes')),
    (
        'get_financial_summary',
        ('ingreso', 'ingresos', 'utilidad', 'ganancia', 'recaud', 'resumen financiero', 'finanzas'),
    ),
    ('get_user_growth', ('crecimiento', 'nuevos usuarios', 'registro de usuarios', 'cuántos se registr')),
    ('get_monthly_collection', ('recaudaci', 'total cobrado', 'cobrado este mes', 'collection')),
)


def _force_intent_tool(message, local_tools, user_role):
    """Si el router local no llamó ninguna tool para un reporte inequívoco,
    fuerza la ejecución determinista de la tool de reporte del intent."""
    if not local_tools:
        return None
    msg = (message or '').lower()
    allowed = {t['function']['name'] for t in local_tools}
    for tool_name, keywords in _LOCAL_FORCE_TOOLS:
        if any(k in msg for k in keywords) and tool_name in allowed:
            return (tool_name, {})
    return None


def _compact_local_schema(tool):
    """Miniatura del schema para el router local: sin ejemplos, desc corta.
    Reduce el prefill (y por tanto la latencia) del modelo en CPU."""
    fn = tool['function']
    params = fn.get('parameters', {}).get('properties', {})
    compact_props = {}
    for pname, pinfo in params.items():
        compact_props[pname] = {'type': pinfo.get('type', 'string')}
    desc = (fn.get('description') or '')[:120]
    return {
        'type': 'function',
        'function': {
            'name': fn['name'],
            'description': desc,
            'parameters': {
                'type': 'object',
                'properties': compact_props,
                'required': list(fn.get('parameters', {}).get('required', [])),
            },
        },
    }


def _build_local_system_prompt(user_role, user_id, mode, message, selected_tools=None):
    """Prompt sistema COMPACTO para Ollama local: personalidad corta + tools del turno."""
    base = LOCAL_BASE_PROMPT.replace('{rol}', ROLE_NAMES_ES.get(user_role, user_role))
    base = base.replace('{rol_id}', user_role)
    base = base.replace('{user_id}', str(user_id or ''))
    if selected_tools:
        names = ', '.join(t['function']['name'] for t in selected_tools)
    else:
        allowed = get_tools_for_mode(mode, user_role)
        names = ', '.join(t['function']['name'] for t in allowed) or 'ninguna'
    base += f'\n\nHerramientas disponibles este turno: {names}'
    return get_current_date_context() + '\n\n' + base


def _build_tool_prompt(tools):
    """Build a compact text listing of available tools."""
    lines = [
        'AVAILABLE TOOLS (use format: <function=name{"param": "value"}</function>):',
        'IMPORTANT: ALWAYS include JSON args in {}. Without {} it FAILS.',
        'IMPORTANT: For any tool that REGISTERS, UPDATES, DELETES, or CHANGES STATE (payments, users, sessions, '
        'incidents, expenses, messages, contracts, patient groups, reminders), you MUST first collect ALL required '
        'parameters from the user one by one. If a required parameter is missing, ASK for it. '
        'Only call the tool once you have every required value. The system will then ask the user to confirm before executing.',
        '',
    ]
    for t in tools:
        fn = t['function']
        params = fn.get('parameters', {}).get('properties', {})
        required = fn.get('parameters', {}).get('required', [])
        param_parts = []
        for pname, pinfo in params.items():
            req = '*' if pname in required else ''
            param_parts.append(f'{pname}{req}:{pinfo.get("type", "string")}')
        params_str = ', '.join(param_parts) if param_parts else 'none'
        lines.append(f'- {fn["name"]}: {fn["description"]} | Params: {params_str}')
    return '\n'.join(lines)


class MCPService:
    """MCP service with GLM-5.2 as primary LLM and multi-provider fallback."""

    def process_message(
        self, message, user_role, user_id, mode='grande', history=None, confirmed_tool=None, telegram_mode=False
    ):
        local_mode = _is_ollama_primary()

        if local_mode:
            tools = get_tools_for_mode(mode, user_role)
            local_tools = _select_local_tools(tools, message)
            system_prompt = _build_local_system_prompt(user_role, user_id, mode, message, selected_tools=local_tools)
            if telegram_mode:
                system_prompt += (
                    '\n\nTELEGRAM: responde corto (máx 10 líneas), usa *negrita* y bullets. '
                    'Si los datos son largos, resume con conteo + top 3.'
                )
        else:
            system_prompt = resolve_system_prompt(user_role, user_id=user_id, mode=mode)

            if telegram_mode:
                system_prompt += (
                    '\n\nTELEGRAM MODE:\n'
                    '- You are responding via Telegram chat.\n'
                    '- Keep responses SHORT (max 10 lines).\n'
                    '- Use emoji sparingly for emphasis.\n'
                    '- Format with *bold* and _italic_ for readability.\n'
                    '- For lists, use bullet points.\n'
                    '- If data is long, summarize with count + top 3 items.\n'
                    '- Always end with a clear answer or next step.\n'
                )

            # Chasqui MCP auto-fill: teach the bot to read logs and self-correct.
            try:
                from app.models.bot_config import BotConfig

                if BotConfig.get_or_create().mcp_prompt_enabled:
                    system_prompt += (
                        '\n\nSELF-SUPERVISION & AUTOCORRECCIÓN (MCP):\n'
                        '- Si no estás seguro de un dato o una operación falló, NO inventes respuestas.\n'
                        '- Ante un error de ejecución, usa las herramientas de logs/disponibles para REVISAR el estado '
                        'real antes de responder al usuario.\n'
                        '- Si detectas que una consulta devolvió datos incompletos o un error, explícalo con claridad '
                        'y sugiere el siguiente paso concreto.\n'
                        '- Nunca afirmes que una operación se completó si no tienes confirmación de la herramienta.\n'
                        '- Si hay un fallo recurrente, indica que se revisará y sugiere re-intentar.\n'
                    )
            except Exception:
                pass

        if local_mode:
            full_system = system_prompt
        else:
            tool_prompt = _build_tool_prompt(tools)
            full_system = get_current_date_context() + '\n\n' + system_prompt + '\n\n' + tool_prompt

        messages = [{'role': 'system', 'content': full_system}]

        if history:
            for h in history[-5:]:
                messages.append({'role': h['role'], 'content': h['content']})

        messages.append({'role': 'user', 'content': message})

        tool_calls_log = []

        def _safe_write(name):
            entry = TOOL_REGISTRY.get(name, {})
            return bool(entry) and entry.get('category') == 'write' and name not in SAFE_WRITE_TOOLS

        # Fast-path local: small-talk puro -> MiniCPM táctico (sin tools, <3s).
        if local_mode and not confirmed_tool and _is_smalltalk(message):
            try:
                content, provider = llm_chat(
                    messages,
                    temperature=0.35,
                    max_tokens=512,
                    phase='tactical',
                )
                return {
                    'response': content or '¡Hola! ¿En qué te ayudo hoy? 😊',
                    'tool_calls': [],
                    'done': True,
                    'provider': provider,
                }
            except Exception as e:
                logger.warning(f'MCP small-talk fallback to main loop: {e}')

        # If confirmed_tool is provided, execute it directly without calling LLM
        if confirmed_tool and confirmed_tool.get('name'):
            tool_name = confirmed_tool['name']
            tool_args = confirmed_tool.get('args') or {}
            logger.info(f'MCP confirmed tool execution: {tool_name}({tool_args})')

            try:
                result = execute_tool(tool_name, tool_args, user_id=user_id, role=user_role)
                tool_calls_log.append(
                    {
                        'name': tool_name,
                        'args': tool_args,
                        'result': result,
                        'timestamp': datetime.utcnow().isoformat(),
                    }
                )

                result_str = _trim_tool_result(result)
                # Generate a natural response from the result
                messages.append(
                    {
                        'role': 'user',
                        'content': (
                            f'[Tool {tool_name} result — use ONLY this data]:\n'
                            f'{result_str}\n\n'
                            f'Respond to the user using ONLY the exact values above. '
                            f'Keep it SHORT and natural. Use emoji for confirmation.'
                        ),
                    }
                )

                tools_kw = {}
                if local_mode:
                    tools_kw['phase'] = 'resume'
                content, provider = llm_chat(messages, temperature=0.3, max_tokens=1024, **tools_kw)
                return {
                    'response': content or f'✅ Operación ejecutada: {tool_name}',
                    'tool_calls': tool_calls_log,
                    'done': True,
                    'provider': provider,
                }
            except Exception as e:
                logger.error(f'MCP confirmed tool execution error: {e}', exc_info=True)
                return {
                    'response': f'❌ Error ejecutando la operación: {str(e)[:200]}',
                    'tool_calls': tool_calls_log,
                    'done': True,
                }

        corrections = 0
        local_resume = False
        for iteration in range(MAX_ITERATIONS):
            try:
                llm_kwargs = {'temperature': 0.3, 'max_tokens': 4096}
                if local_mode:
                    # Ruta: el router local decide/ejecuta la tool con tools nativas.
                    # Resume: tras un resultado real, responder directo sin re-llamar tools.
                    llm_kwargs['phase'] = 'resume' if local_resume else 'route'
                    if not local_resume:
                        llm_kwargs['tools'] = local_tools
                content, provider = llm_chat(messages, **llm_kwargs)

                if not content.strip():
                    return {
                        'response': 'No pude generar una respuesta.',
                        'tool_calls': tool_calls_log,
                        'done': True,
                        'provider': provider,
                    }

                logger.info(f'MCP LLM response via {provider} (iteration {iteration})')

                tool_name, tool_args = _parse_text_tool_call(content)

                if not tool_name:
                    # Guard against hallucinated tool names: if the model emits a
                    # <function=X{...}> call for a tool that does not exist, re-prompt
                    # instead of silently passing the fabricated text to the user.
                    m = re.search(r'<function=(\w+)', content)
                    if m and m.group(1) not in TOOL_REGISTRY:
                        unknown = m.group(1)
                        logger.warning(f'MCP hallucinated unknown tool: {unknown}')
                        available = ', '.join(sorted(TOOL_REGISTRY.keys()))
                        messages.append(
                            {
                                'role': 'user',
                                'content': (
                                    f'ERROR: la herramienta "{unknown}" NO existe. '
                                    f'Herramientas disponibles: {available}. '
                                    'Si necesitas ejecutar una accion, repite usando SIEMPRE la sintaxis '
                                    '<function=nombre{"param": "valor"}</function> con el nombre EXACTO '
                                    'de una herramienta disponible. Para consultas simples responde con datos reales.'
                                ),
                            }
                        )
                        continue

                if not tool_name and local_mode and not local_resume and not tool_calls_log:
                    forced = _force_intent_tool(message, local_tools, user_role)
                    if forced:
                        tool_name, tool_args = forced
                        content = f'<function={tool_name}{json.dumps(tool_args, ensure_ascii=False)}</function>'
                        logger.info(f'MCP deterministic intent tool: {tool_name}({tool_args})')

                if tool_name:
                    logger.info(f'MCP parsed tool call: {tool_name}({tool_args})')

                    # Write tools require explicit confirmation before running.
                    confirmed_name = (confirmed_tool or {}).get('name')
                    if _safe_write(tool_name) and not confirmed_name:
                        return {
                            'response': 'Acción pendiente de confirmación.',
                            'tool_calls': tool_calls_log,
                            'done': False,
                            'requires_confirmation': True,
                            'pending_tool': {'name': tool_name, 'args': tool_args, 'tool_call_text': content},
                            'provider': provider,
                        }

                    # On confirmation, prefer the args captured at request time (e.g. receipt_url of a voucher).
                    effective_args = tool_args
                    if confirmed_name and confirmed_name == tool_name:
                        saved_args = (confirmed_tool or {}).get('args') or {}
                        if saved_args:
                            effective_args = {**tool_args, **saved_args}

                    result = execute_tool(tool_name, effective_args, user_id=user_id, role=user_role)
                    tool_calls_log.append(
                        {
                            'name': tool_name,
                            'args': tool_args,
                            'result': result,
                            'timestamp': datetime.utcnow().isoformat(),
                        }
                    )

                    result_str = _trim_tool_result(result)
                    # Strip any fabricated text before the tool call — only keep the tool invocation
                    tool_call_match = re.search(r'<function=.*?(?:</function>|/\s*>)', content, re.DOTALL)
                    clean_assistant = tool_call_match.group(0) if tool_call_match else content
                    messages.append({'role': 'assistant', 'content': clean_assistant})
                    messages.append(
                        {
                            'role': 'user',
                            'content': (
                                f'[REAL Tool {tool_name} result — use ONLY this data, do NOT invent anything]:\n'
                                f'{result_str}\n\n'
                                f'Respond to the user using ONLY the exact values above, copying names and numbers EXACTLY as given (never adapt, translate or merge names/emails). If a field is missing, say "no disponible".'
                            ),
                        }
                    )
                    if local_mode:
                        local_resume = True
                    continue

                # Si la respuesta afirma un dato del sistema sin haber ejecutado
                # herramienta (conteos/lists/estados), re-consulta hasta 2 veces
                # pidiendo la llamada real antes de devolverla como final.
                clean_content = re.sub(r'<function=\w+.*?</function>', '', content).strip()
                if (
                    not (confirmed_tool or {}).get('name')
                    and corrections < 2
                    and _DATA_CLAIM_RE.search(clean_content)
                    and not tool_calls_log
                ):
                    corrections += 1
                    messages.append(
                        {
                            'role': 'user',
                            'content': (
                                '¡ALTO! Tu respuesta afirma un dato del sistema (cantidad, lista o estado), '
                                'pero NO ejecutaste ninguna herramienta en este turno. Eso está PROHIBIDO. '
                                'Emite la llamada a la herramienta correspondiente '
                                '(<function=nombre{"param": "valor"}</function>) y espera SU resultado real.'
                            ),
                        }
                    )
                    continue

                return {
                    'response': content,
                    'tool_calls': tool_calls_log,
                    'done': True,
                    'provider': provider,
                }

            except Exception as e:
                error_str = str(e)
                logger.error(f'MCP iteration {iteration} error: {error_str}', exc_info=True)

                if 'failed_generation' in error_str:
                    try:
                        err_json = json.loads(
                            error_str.split("'failed_generation':")[1].split('}', maxsplit=1)[0] + '}'
                        )
                        failed_gen = err_json.get('failed_generation', '')
                    except Exception:
                        match = re.search(r"'failed_generation':\s*'([^']*)'", error_str)
                        failed_gen = match.group(1) if match else ''

                    if failed_gen:
                        tool_name, tool_args = _parse_text_tool_call(failed_gen)
                        if tool_name:
                            logger.info(f'MCP fallback parsed tool call: {tool_name}({tool_args})')
                            result = execute_tool(tool_name, tool_args, user_id=user_id, role=user_role)
                            tool_calls_log.append(
                                {
                                    'name': tool_name,
                                    'args': tool_args,
                                    'result': result,
                                    'timestamp': datetime.utcnow().isoformat(),
                                }
                            )

                            result_str = _trim_tool_result(result)
                            tool_call_match = re.search(r'<function=.*?(?:</function>|/\s*>)', failed_gen, re.DOTALL)
                            clean_assistant = tool_call_match.group(0) if tool_call_match else failed_gen
                            messages.append({'role': 'assistant', 'content': clean_assistant})
                            messages.append(
                                {
                                    'role': 'user',
                                    'content': (
                                        f'[REAL Tool {tool_name} result — use ONLY this data, do NOT invent anything]:\n'
                                        f'{result_str}\n\n'
                                        f'Respond to the user using ONLY the exact values above, copying names and numbers EXACTLY as given (never adapt, translate or merge names/emails). If a field is missing, say "no disponible".'
                                    ),
                                }
                            )
                            continue

                if iteration >= 2:
                    return {
                        'response': f'Error procesando tu solicitud: {error_str[:200]}',
                        'tool_calls': tool_calls_log,
                        'done': True,
                        'error': error_str,
                    }

        return {
            'response': 'No pude completar la operacion. Intenta ser mas especifico.',
            'tool_calls': tool_calls_log,
            'done': True,
        }

    def get_available_tools(self, user_role, mode='grande'):
        tools = get_tools_for_mode(mode, user_role)
        return [
            {
                'name': t['function']['name'],
                'description': t['function']['description'],
                'category': TOOL_REGISTRY[t['function']['name']]['category'],
            }
            for t in tools
        ]
