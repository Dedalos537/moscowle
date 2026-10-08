"""Construcción del system prompt DESDE el catálogo de tools.

Unifica las tres fuentes que hasta ahora convivían a mano:

* ``PERSONALITY_PROMPT`` / ``LOCAL_BASE_PROMPT`` (identidad y reglas),
* los bloques de fecha y de acceso por rol,
* el listado de herramientas (antes ``_build_tool_prompt``, escrito a mano
  junto al catálogo hardcodeado ``SYSTEM_PROMPTS``).

``build_system_prompt()`` genera: FECHA · IDENTIDAD/REGLAS · CATÁLOGO
(derivado de ``TOOL_REGISTRY``, agrupado por categoría y solo con las tools
permitidas del rol) · ACCESO.

Modos:
* ``compact=False`` (ruta remota): catálogo con params y descripción larga.
* ``compact=True`` (Ollama local): una línea por tool y presupuesto de
  ~1200 tokens (~4800 chars) para no desbordar el prefill en CPU.

El override del admin (``BotConfig.system_prompt``) gana; si está vacío,
queda ``PERSONALITY_PROMPT`` como fallback.
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.personality_prompt import LOCAL_BASE_PROMPT, PERSONALITY_PROMPT, ROLE_NAMES_ES
from app.services.tools_registry import get_tools_for_mode

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

# Presupuesto del prompt local (~1200 tokens a ≈4 chars/token).
_COMPACT_MAX_CHARS = 4800

_CATEGORY_LABELS = {
    'read': 'CONSULTAS (leen datos reales)',
    'write': 'ACCIONES (escriben datos — el sistema pedirá confirmación)',
}


def get_current_date_context():
    """Fecha actual en America/Lima para que el LLM nunca adivine 'hoy'."""
    now = datetime.now(LIMA_TZ)
    fecha = f'{_DIAS_ES[now.weekday()]} {now.day} de {_MESES_ES[now.month - 1]} de {now.year}'
    return (
        f"Hoy es {fecha}. Usa SIEMPRE esta fecha como referencia para 'hoy'. "
        'Todos los usuarios están en la zona horaria America/Lima (UTC-5).'
    )


def get_configured_system_prompt():
    """Prompt editado en el módulo de configuración del bot, si existe."""
    try:
        from app.models.bot_config import BotConfig

        configured = (BotConfig.get_or_create().system_prompt or '').strip()
        return configured or None
    except Exception:
        return None


def bot_identity():
    """(nombre, emoji, presentación) del bot según BotConfig; con respaldo si la BD no responde."""
    try:
        from app.models.bot_config import BotConfig

        cfg = BotConfig.get_or_create()
        return (cfg.bot_name or 'Diego').strip(), (cfg.bot_emoji or '').strip(), (cfg.persona_message or '').strip()
    except Exception:
        return 'Diego', '', ''


def apply_bot_name(prompt):
    """Los prompts base dicen «Diego»: se cambia por el nombre configurado en el panel.

    Se hace ANTES de sustituir {usuario}, para no tocar el nombre de la persona que escribe.
    """
    name = bot_identity()[0]
    return prompt if name == 'Diego' else re.sub(r'\bDiego\b', name, prompt)


def _substitute_tokens(prompt, user_role, user_id):
    prompt = apply_bot_name(prompt)
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


def get_role_access_block(user_role, mode='grande', tools=None):
    """Refuerza en runtime qué puede y qué NO puede hacer el rol actual."""
    role_name = ROLE_NAMES_ES.get(user_role, user_role)
    if tools is None:
        tools = get_tools_for_mode(mode, user_role)
    names = ', '.join(t['function']['name'] for t in tools) or 'ninguna'
    return (
        f'\nACCESO Y PERMISOS DEL USUARIO (nivel: {role_name}):\n'
        f'- Herramientas permitidas para tu nivel (SOLO estas): {names}\n'
        '- NO puedes usar ninguna otra herramienta ni elevar tu nivel de acceso.\n'
        '- PROHIBIDO: inventar resultados, afirmar que una operación se completó sin confirmación '
        'de la herramienta, y ejecutar acciones de escritura sin confirmación del usuario.\n'
        '- Si el usuario pide algo fuera de tu nivel de acceso, responde que no tienes permisos '
        'y sugiere solicitarlo al administrador o supervisor.'
    )


def _desc_oneline(desc, limit):
    """Primera oración de la descripción, en una sola línea y con tope."""
    text = re.split(r'(?<=[.!?])\s', (desc or '').strip())[0]
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + '…'
    return text


def build_tool_catalog(tools, compact=False):
    """Catálogo generado desde las tools permitidas, agrupado por categoría."""
    if not tools:
        return ''
    from app.services.tools_registry import TOOL_REGISTRY

    groups: dict[str, list[str]] = {}
    for t in tools:
        fn = t.get('function') or {}
        name = fn.get('name') or ''
        if not name:
            continue
        category = (TOOL_REGISTRY.get(name) or {}).get('category', 'read')
        if compact:
            line = f'- {name}: {_desc_oneline(fn.get("description"), 110)}'
        else:
            params = fn.get('parameters', {}) or {}
            required = set(params.get('required') or [])
            plist = ', '.join(f'{p}*' if p in required else p for p in (params.get('properties') or {})) or 'ninguno'
            line = f'- {name}: {_desc_oneline(fn.get("description"), 150)} | params: {plist}'
        groups.setdefault(category, []).append(line)

    header = (
        'HERRAMIENTAS DE ESTE TURNO (formato <function=nombre{"param": "valor"}>):'
        if compact
        else 'CATÁLOGO DE HERRAMIENTAS (usa SOLO estas, formato <function=nombre{"param": "valor"}>):'
    )
    parts = [header]
    for category in ('read', 'write'):
        lines = groups.get(category)
        if not lines:
            continue
        if not compact:
            parts.append(f'{_CATEGORY_LABELS.get(category, category.upper())}:')
        parts.extend(lines)
    text = '\n'.join(parts)
    if compact and len(text) > _COMPACT_MAX_CHARS:
        text = text[:_COMPACT_MAX_CHARS].rsplit('\n', 1)[0] + '\n…'
    return text


def build_system_prompt(role, user_id=None, mode='grande', tools=(), compact=False):
    """System prompt completo: FECHA · IDENTIDAD/REGLAS · CATÁLOGO · ACCESO.

    * ``compact=False`` → configuración del admin si existe, si no
      ``PERSONALITY_PROMPT`` (fallback documentado en el docstring superior).
    * ``compact=True`` → ``LOCAL_BASE_PROMPT`` + catálogo en una línea por
      tool, con presupuesto de prefill para modelos locales en CPU.
    * ``tools`` es SIEMPRE la lista de tools permitidas del rol/turno: el
      catálogo y el bloque de acceso no pueden mencionar ninguna otra.
    """
    if compact:
        base = _substitute_tokens(LOCAL_BASE_PROMPT, role, user_id)
        persona = bot_identity()[2]
        if persona:
            # Presentación del panel, recortada: en CPU cada token de contexto cuesta.
            base += '\nPRESENTACIÓN (úsala al saludar): ' + persona[:400]
    else:
        base = get_configured_system_prompt() or PERSONALITY_PROMPT
        base = _substitute_tokens(base, role, user_id)

    sections = [get_current_date_context(), base]
    catalog = build_tool_catalog(list(tools), compact=compact)
    if catalog:
        sections.append(catalog)
    sections.append(get_role_access_block(role, mode=mode, tools=tools))
    return '\n\n'.join(s for s in sections if s)
