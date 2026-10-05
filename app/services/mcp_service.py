import json
import logging
import os
import re
from datetime import date, datetime, timedelta

from app.services.llm_client import llm_chat
from app.services.prompt_builder import (
    _MESES_ES,
    LIMA_TZ,
    build_system_prompt,
    get_current_date_context,  # noqa: F401 — re-export para mcp_routes y tests
)
from app.services.tool_intents import match_intent, norm
from app.services.tools_registry import SAFE_WRITE_TOOLS, TOOL_REGISTRY, execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

MAX_TOOL_RESULT_CHARS = 1500
LOCAL_MAX_TOOLS = 14


def resolve_system_prompt(user_role, user_id=None, mode='grande', tools=None):
    """Prompt remoto completo (FECHA · REGLAS · CATÁLOGO · ACCESO).

    El catálogo y el bloque de acceso se generan en ``prompt_builder`` desde
    las ``tools`` permitidas del rol; el admin puede sobrescribir las reglas
    con ``BotConfig.system_prompt`` (fallback: PERSONALITY_PROMPT)."""
    if tools is None:
        tools = get_tools_for_mode(mode, user_role)
    return build_system_prompt(user_role, user_id=user_id, mode=mode, tools=tools, compact=False)


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

# Variante con paréntesis que emiten los modelos pequeños: cierran el hint
# <function=nombre{...}> con () en vez de </function>. Sin este patrón la llamada
# cruda se filtraba a la burbuja del chat (bug de producción 007-F).
_PAREN_FUNC_PATTERN = re.compile(
    r'\(\s*function\s*=\s*(\w+)\s*(\{.*?\})?(?=\s*\))',
    re.DOTALL,
)

# Broader fallback patterns for small models that deviate from the exact format
_FALLBACK_PATTERNS = [
    # Parenthesized variant: (function=search_patients {"query": "Carlos"})
    _PAREN_FUNC_PATTERN,
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

# Cualquiera de las dos sintaxis, para limpiar llamadas del texto visible.
_TOOL_CALL_ANY_RE = re.compile(
    r'<function=\w+.*?(?:</function>|/\s*>)'
    r'|\(\s*function\s*=\s*\w+\s*(?:\{.*?\})?(?=\s*\))',
    re.DOTALL,
)

# Nombres de herramienta invocados en cualquiera de las dos sintaxis.
_UNKNOWN_CALL_RE = re.compile(r'(?:<|\(\s*)function\s*=\s*(\w+)')


def strip_tool_calls(text):
    """Elimina llamadas a funciones (ángulos o paréntesis) del texto visible."""
    return _TOOL_CALL_ANY_RE.sub('', text or '')


# Emails/URLs: nunca se les inserta espacio (los modelos retipean correos
# como "adrenalina11@..." y el normalizador no debe romperlos).
_EMAIL_URL_RE = re.compile(r'https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.-]+')


def normalize_number_spaces(text):
    """Corrige el sesgo de los modelos locales (qwen/minicpm) de emitir cifras
    sin espacio previo: 'Hay4', 'domingo4', 'a las14:58:47'.

    Solo INSERTA espacio entre una letra y un dígito; emails y URLs quedan
    intactos. Idempotente."""
    if not text:
        return text or ''

    def _fix(segment):
        return re.sub(
            r'(?<=[A-Za-z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1])(?=\d)', ' ', segment
        )

    parts = []
    last = 0
    for m in _EMAIL_URL_RE.finditer(text):
        parts.append(_fix(text[last : m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(_fix(text[last:]))
    return ''.join(parts)


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


def tool_result_context(tool_name, result_str, already_executed=False):
    """Bloque de contexto tras una tool real para una síntesis fiel:
    conteo primero, copia exacta y honestidad con resultados truncados."""
    lines = [
        f'[REAL Tool {tool_name} result — use ONLY this data, do NOT invent anything]:',
        str(result_str),
        '',
        'RESPONDE ASÍ (obligatorio):',
        '1. Si preguntaron cuántos, empieza con el conteo EXACTO: "Hay N ..." '
        '(usa el campo count o la longitud real de la lista).',
        '2. Luego lista los valores EXACTAMENTE como aparecen arriba; nunca inventes, '
        'complete ni fusiones nombres/correos.',
        '3. Si el resultado indica "Showing X of Y" o viene cortado, dilo: "mostrando X de Y".',
        '4. Si el resultado es GLOBAL (sin filtro de la persona nombrada), NO se lo atribuyas: '
        'di el alcance real (p.ej. "pacientes activos del centro"); para UN terapeuta existe '
        'get_therapist_patients.',
        '5. No afirmes estados (activo/inactivo, permisos, montos) salvo que estén en los '
        'datos; si falta un campo, di "no disponible".',
        '6. Responde en español, conciso, sin mencionar herramientas ni procesos internos.',
        '7. Escribe con espacio entre palabras y cifras ("Hay 4", "las 14:58"): NUNCA "Hay4".',
    ]
    if already_executed:
        lines.append(f'8. {tool_name} YA fue ejecutada: NO la llames de nuevo; responde ahora.')
    return '\n'.join(lines)


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
                    'summary': payload.get('summary') or {},
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
        'list_expenses',
        'create_expense',
    },
    'sesiones': {
        'get_sessions',
        'get_sessions_day',
        'schedule_programmed_session',
        'update_session_plan',
        'cancel_session',
        'complete_session',
        'batch_create_sessions',
        'create_group_sessions',
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
        'egresos',
        'gasto',
        'gastos',
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


_RETRIEVER = None


def _get_retriever():
    """Recuperador singleton. El indice (67 docs) se construye una sola vez."""
    global _RETRIEVER  # noqa: PLW0603
    if _RETRIEVER is None:
        from app.services.retrieval import ToolRetriever

        _RETRIEVER = ToolRetriever(TOOL_REGISTRY)
    return _RETRIEVER


def _select_local_tools(tools, message, user_role=None, k=None):
    """Selecciona las tools relevantes para el mensaje.

    Reemplaza la seleccion por palabras clave (que seccionaba el catalogo y
    llegaba a ofrecer 'delete_user' a una consulta de conteo) por el
    recuperador BM25 + sinonimos, que además respeta el rol del usuario.

    Mantiene ademas las tools esenciales del turno y el limite LOCAL_MAX_TOOLS
    para no degradar el prefill en CPU.
    """
    # 8 tools, no LOCAL_MAX_TOOLS(14): el objetivo es que el prompt del
    # sintetizador pase de 8142 tokens a ~1200. Con 6 recuperadas mas el reloj
    # hay margen de sobra y el prefill en CPU se mantiene corto.
    k = k or 8
    permitidas = {t['function']['name'] for t in tools}
    role = user_role

    candidates = _get_retriever().search(message, role=role, k=k)

    # El prompt local siempre incluye el reloj: el bot lo necesita para
    # cualquier referencia temporal y es lo mas barato posible.
    if 'get_current_datetime' in permitidas and not any(t.name == 'get_current_datetime' for t in candidates):
        rel = next(
            t for t in _get_retriever().search('fecha hora actual', role=role, k=1) if t.name == 'get_current_datetime'
        )
        candidates = [rel] + candidates

    por_nombre = {t['function']['name']: t for t in tools}
    selected = [por_nombre[t.name] for t in candidates if t.name in permitidas]
    return [_compact_local_schema(t) for t in selected[:k]]


# Mapa determinista intención -> tool de reporte.
# Se usa SOLO como fallback cuando el router local (Qwen) no emite tool call
# ante una consulta de datos inequívoca sobre reportes/estadísticas.
# Formato por entrada: (tool_name, keywords, args) donde args puede ser un dict
# fijo, la string 'month' (se extrae el mes del mensaje) o None (sin args).
_LOCAL_MONTH_ABBR = {
    'ene': 1,
    'feb': 2,
    'mar': 3,
    'abr': 4,
    'may': 5,
    'jun': 6,
    'jul': 7,
    'ago': 8,
    'sep': 9,
    'set': 9,
    'oct': 10,
    'nov': 11,
    'dic': 12,
}


def _extract_month_arg(message):
    """Devuelve {'month': 'YYYY-MM'} si el mensaje menciona un mes ('setiembre',
    'septiembre', 'este mes', nombres/abr. en español); si no, {} (default)."""
    msg = (message or '').lower()
    now = datetime.now(LIMA_TZ)
    current = f'{now.year}-{now.month:02d}'
    if 'este mes' in msg or 'de este mes' in msg:
        return {'month': current}
    month_num = None
    for i, name in enumerate(_MESES_ES, 1):
        if name in msg:
            month_num = i
            break
    if month_num is None and 'setiembre' in msg:
        month_num = 9
    if month_num is None:
        for abbr, num in _LOCAL_MONTH_ABBR.items():
            if f' {abbr}' in msg or msg.startswith(abbr):
                month_num = num
                break
    if month_num:
        return {'month': f'{now.year}-{month_num:02d}'}
    return {}


_WEEKDAY_MAP = {
    'lunes': 0,
    'martes': 1,
    'miercoles': 2,
    'miércoles': 2,
    'jueves': 3,
    'viernes': 4,
    'sabado': 5,
    'sábado': 5,
    'domingo': 6,
}


_LOCAL_MONTH_NAMES = {
    'enero': 1,
    'febrero': 2,
    'marzo': 3,
    'abril': 4,
    'mayo': 5,
    'junio': 6,
    'julio': 7,
    'agosto': 8,
    'setiembre': 9,
    'septiembre': 9,
    'octubre': 10,
    'noviembre': 11,
    'diciembre': 12,
}


def _extract_date_arg(message):
    """Resuelve la fecha de una consulta de agenda: 'lunes 28 de setiembre',
    '28/09', 'el lunes', 'hoy', 'mañana'. Devuelve {'date': 'YYYY-MM-DD'}."""
    import re as _re

    text = _normalize_text(message)
    today = datetime.now(LIMA_TZ).date()

    if 'manana' in text or 'mañana' in text:
        return {'date': (today + timedelta(days=1)).strftime('%Y-%m-%d')}
    if 'ayer' in text:
        return {'date': (today - timedelta(days=1)).strftime('%Y-%m-%d')}
    if 'hoy' in text:
        return {'date': today.strftime('%Y-%m-%d')}

    month_num = None
    for name, num in _LOCAL_MONTH_NAMES.items():
        if _re.search(rf'\b{name}\b', text):
            month_num = num
            break

    day = None
    dm = _re.search(r'\b(\d{1,2})\s*(?:de\s+\w+)?[/.-]\s*(\d{1,2})(?:[/.-]\d{2,4})?\b', text)
    if dm:
        day, month_num = int(dm.group(1)), int(dm.group(2))
    else:
        dm = _re.search(r'\b(\d{1,2})\s+de\s+\w+\b', text)
        if dm and month_num:
            day = int(dm.group(1))
        else:
            dm = _re.search(r'\b(\d{1,2})\b', text)
            if dm:
                day = int(dm.group(1))

    if day and month_num:
        year = today.year
        try:
            return {'date': date(year, month_num, day).strftime('%Y-%m-%d')}
        except ValueError:
            try:
                return {'date': date(year + 1, month_num, day).strftime('%Y-%m-%d')}
            except ValueError:
                return None

    for name, weekday in _WEEKDAY_MAP.items():
        if _re.search(rf'\b{name}\b', text):
            delta = (weekday - today.weekday()) % 7
            return {'date': (today + timedelta(days=delta)).strftime('%Y-%m-%d')}

    return None


def _normalize_text(value):
    import unicodedata

    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '')) if unicodedata.category(c) != 'Mn').lower()


def _find_user_id_by_words(full_name, roles=('jugador',)):
    from app.models import User

    words = [w for w in _normalize_text(full_name).split() if len(w) > 1]
    if not words:
        return None
    candidates = User.query.filter(User.role.in_(roles)).all()
    for u in candidates:
        uu = _normalize_text(u.username)
        if all(w in uu for w in words):
            return u.id
    return None


def _default_therapist_id():
    from app.models import User

    t = (
        User.query.filter_by(role='terapista', is_active=True).order_by(User.id).first()
        or User.query.filter_by(role='terapista').order_by(User.id).first()
    )
    return t.id if t else None


def _extract_session_time(msg):
    m = re.search(
        r'(\d{1,2})(?::(\d{2}))?\s*(?:am|a\.m\.|hrs?)?\s*(?:a\s+las?|-)\s*(\d{1,2})(?::(\d{2}))?\s*(?:am|a\.m\.)', msg
    )
    if not m:
        m = re.search(r'(\d{1,2})[:.](\d{2})\s*(?:a\s+las?|-)\s*(\d{1,2})[:.](\d{2})', msg)
    if m:
        sh = int(m.group(1))
        sm = int(m.group(2) or 0)
        eh = int(m.group(3))
        em = int(m.group(4) or 0)
        return f'{sh:02d}:{sm:02d}', f'{eh:02d}:{em:02d}'
    return '08:00', '10:00'


def _extract_session_count(msg):
    m = re.search(r'(\d+)\s*(?:sesiones|sesión|ses)', msg)
    return int(m.group(1)) if m else 3


def _build_group_session_args(message):
    """Devuelve args deterministas para create_group_sessions si el mensaje pide
    crear un grupo de pacientes con sesiones; si no, None."""
    msg = _normalize_text(message)
    if 'grupo' not in msg or not re.search(r'sesion|se hacen', msg):
        return None
    names_blob = None
    m = re.search(r'grupo de\s+(.+?)(?:\s+y\s+(?:se\s+hacen|se\s+programan|sean|se)\b|$)', msg)
    if not m:
        m = re.search(r'grupo de\s+(.+?)(?:\s+y\s+(?:se|sean)\b|$)', msg)
    if m:
        names_blob = m.group(1).strip()
    if not names_blob:
        m2 = re.search(r'sesiones (?:para|de)\s+(.+?)(?:\s+a\s+partir|\s+desde|$)', msg)
        if m2:
            names_blob = m2.group(1).strip()
    if not names_blob:
        return None
    ids = []
    raw_names = [p.strip() for p in re.split(r'\s+y\s+', names_blob) if p.strip()]
    for rn in raw_names:
        pid = _find_user_id_by_words(rn)
        if pid:
            ids.append(pid)
    if not ids:
        return None
    start_date = None
    for name, wd in _WEEKDAY_MAP.items():
        if name in msg:
            today = datetime.now(LIMA_TZ).date()
            delta = (wd - today.weekday()) % 7
            if delta == 0:
                delta = 7
            start_date = (today + timedelta(days=delta)).strftime('%Y-%m-%d')
            break
    if not start_date:
        m3 = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', msg)
        start_date = m3.group(1) if m3 else None
    if not start_date:
        return None
    start_time, end_time = _extract_session_time(msg)
    return {
        'group_name': 'Grupo ' + ' y '.join(raw_names).title(),
        'patient_ids': list(dict.fromkeys(ids)),
        'start_date': start_date,
        'days': [0, 1, 2],
        'therapist_id': _default_therapist_id(),
        'start_time': start_time,
        'end_time': end_time,
        'count': _extract_session_count(msg),
    }


_ROLE_SYNONYMS = {
    'terapista': ('terapeuta', 'terapeutas', 'terapista', 'terapistas'),
    'jugador': ('paciente', 'pacientes', 'jugador', 'jugadores'),
    'admin': ('admin', 'administrador', 'administradora', 'administradores'),
    'supervisor': ('supervisor', 'supervisora', 'supervisores'),
}


def _extract_role_arg(message, tool_name):
    """arg_spec='role': {'role': valor} si el mensaje nombra un rol del enum.

    El valor se resuelve SIEMPRE contra el enum real de la tool definida en
    TOOL_REGISTRY; si el mensaje no nombra ningún rol (o no existe en el enum)
    devuelve {} y la tool corre sin filtro."""
    props = ((TOOL_REGISTRY.get(tool_name) or {}).get('parameters') or {}).get('properties') or {}
    enum = (props.get('role') or {}).get('enum') or []
    if not enum:
        return {}
    msg = (message or '').lower()
    for value in enum:
        for syn in _ROLE_SYNONYMS.get(value, (value,)):
            if re.search(r'\b' + re.escape(syn), msg):
                return {'role': value}
    return {}


# Preguntas de identidad de sesión: se responden con los tokens del prompt
# (usuario/rol/id), jamás forzando una tool de listado.
_IDENTITY_RE = re.compile(
    r'\b(en que usuario|que usuario soy|mi usuario|quien soy|soy yo|en que cuenta'
    r'|que rol tengo|mi rol|como me llamo|en que sesion estoy)\b'
)

_THERAPIST_NAME_RE = re.compile(
    r'(?:terapeuta|terapista)(?:s)?(?:\s+(?:el|la|llamad[oa]|de))?\s+'
    r'([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][\w\u00c1\u00c9\u00cd\u00d3\u00da\u00d1'
    r'\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]+'
    r'(?:\s+[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][\w\u00c1\u00c9\u00cd\u00d3\u00da\u00d1'
    r'\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]+)*)'
)


def _extract_therapist_arg(message, user_role):
    """arg_spec='therapist': {'therapist_name': nombre} para tools de terapeuta.

    1) Nombre propio tras 'terapeuta/terapista' en el mensaje crudo;
    2) resolutor de entidades (el nombre está en la BD con rol terapista)."""
    m = _THERAPIST_NAME_RE.search(message or '')
    if m:
        name = m.group(1).strip().rstrip('.,;:\u00bf?\u00a1!')
        if len(name) >= 3:
            return {'therapist_name': name}
    # Fallback al resolutor: solo si el mensaje contiene un candidato a nombre
    # propio (mayúscula inicial distinto de 'terapeuta/terapista'). Evita que la
    # palabra genérica resuelva a un usuario arbitrario de la BD.
    candidates = {
        w.lower()
        for w in re.findall(
            r'[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][\w\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]+', message or ''
        )
    }
    if candidates - {'terapeuta', 'terapeutas', 'terapista', 'terapistas'}:
        try:
            from app.services.entity_resolver import resolve_entities

            ents = resolve_entities(message, role=user_role)
            if ents.therapists:
                t = ents.therapists[0]
                name = t.get('username') or t.get('email') or ''
                if name:
                    return {'therapist_name': name}
        except Exception:
            pass
    return {}


def _force_intent_tool(message, local_tools, user_role):
    """Si el router local no llamó ninguna tool para un reporte inequívoco,
    fuerza la ejecución determinista de la tool elegida por el índice
    GENERADO (``tool_intents.match_intent``), sin keywords hardcodeadas.

    Solo decide la tool: los argumentos los resuelven los extractores
    genéricos de fecha/mes/grupo/rol/terapeuta de este módulo."""
    if not local_tools:
        return None
    # Identidad de sesión: se responde con el prompt, nunca con una tool.
    if _IDENTITY_RE.search(norm(message)):
        return None
    allowed = {t['function']['name'] for t in local_tools}
    hit = match_intent(message, allowed)
    if not hit:
        return None
    tool_name, arg_spec = hit
    # Estadísticas globales + persona nombrada en el mensaje -> la lista REAL
    # de ese terapeuta, en vez de atribuirle el total del centro.
    if tool_name == 'get_patient_stats' and 'get_therapist_patients' in allowed:
        resolved_therapist = _extract_therapist_arg(message, user_role)
        if resolved_therapist:
            logger.info(f'MCP force override stats->therapist: {resolved_therapist}')
            return ('get_therapist_patients', resolved_therapist)
    if arg_spec == 'month':
        resolved_args = _extract_month_arg(message)
    elif arg_spec == 'date':
        resolved_args = _extract_date_arg(message) or {}
    elif arg_spec == 'group_session':
        resolved_args = _build_group_session_args(message)
        if not resolved_args:
            return None
    elif arg_spec == 'role':
        resolved_args = _extract_role_arg(message, tool_name)
    elif arg_spec == 'therapist':
        resolved_args = _extract_therapist_arg(message, user_role)
        if not resolved_args:
            return None
    else:
        resolved_args = {}
    return (tool_name, resolved_args or {})


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
    """Prompt sistema COMPACTO para Ollama local: personalidad corta + tools del turno.

    Inyecta ademas las entidades ya resueltas contra la base de datos, para que
    el modelo use identificadores reales en vez de inventarlos.
    """
    tools = selected_tools or get_tools_for_mode(mode, user_role)
    context = build_system_prompt(user_role, user_id=user_id, mode=mode, tools=tools, compact=True)
    try:
        from app.services.entity_resolver import resolve_entities

        entities = resolve_entities(message, role=user_role)
        if entities:
            context += (
                '\n\nDATOS VERIFICADOS DE LA BASE (usa estos identificadores tal cual, '
                'no los inventes ni los calcules):\n' + entities.to_prompt_context()
            )
    except Exception:
        pass
    return context


class MCPService:
    """MCP service with GLM-5.2 as primary LLM and multi-provider fallback."""

    def process_message(
        self, message, user_role, user_id, mode='grande', history=None, confirmed_tool=None, telegram_mode=False
    ):
        local_mode = _is_ollama_primary()

        # Las herramientas se resuelven para AMBAS ramas: la remota tambien
        # construye el prompt de tools y antes recien se inicializaba dentro
        # de `if local_mode:`, lo que la hacia reventar con UnboundLocalError.
        tools = get_tools_for_mode(mode, user_role)

        if local_mode:
            local_tools = _select_local_tools(tools, message, user_role=user_role)
            system_prompt = _build_local_system_prompt(user_role, user_id, mode, message, selected_tools=local_tools)
            if telegram_mode:
                system_prompt += (
                    '\n\nTELEGRAM: responde corto (máx 10 líneas), usa *negrita* y bullets. '
                    'Si los datos son largos, resume con conteo + top 3.'
                )
        else:
            system_prompt = resolve_system_prompt(user_role, user_id=user_id, mode=mode, tools=tools)

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

        # Ambas ramas ya entregan el system prompt completo (fecha + catálogo).
        full_system = system_prompt

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
                    'response': normalize_number_spaces(content) or '¡Hola! ¿En qué te ayudo hoy? 😊',
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
                    'response': normalize_number_spaces(content) or f'✅ Operación ejecutada: {tool_name}',
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
                    m = _UNKNOWN_CALL_RE.search(content)
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

                if local_mode and not local_resume and not tool_calls_log:
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
                            'content': tool_result_context(tool_name, result_str),
                        }
                    )
                    if local_mode:
                        local_resume = True
                    continue

                # Si la respuesta afirma un dato del sistema sin haber ejecutado
                # herramienta (conteos/lists/estados), re-consulta hasta 2 veces
                # pidiendo la llamada real antes de devolverla como final.
                clean_content = strip_tool_calls(content).strip()
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
                    'response': normalize_number_spaces(content),
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
                                    'content': tool_result_context(tool_name, result_str),
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
