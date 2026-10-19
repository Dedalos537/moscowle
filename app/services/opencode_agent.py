"""Asistente con opencode como cerebro (PRP 009).

- Para los roles de `ai.opencode.roles` (hoy solo admin) **todo** pasa por opencode (MiMo-V2.6-Flash Free),
  incluso los saludos. Si opencode no está, se acabó la cuota o falla, se lanza `OpencodeUnavailableError` y el
  llamador sigue por la cadena actual (Ollama → Groq → …).
- opencode solo decide el siguiente paso con un JSON (`{"kind": "tool"|"answer"|"clarify", ...}`). Las tools
  las ejecuta Moscowle con `execute_tool(user_id, role)`: las de lectura entran al bucle (máx. `MAX_STEPS`),
  las de escritura salen como confirmación y se ejecutan al confirmar, igual que hoy.
- Todo lo que sale va seudonimizado (`ai_privacy.Vault`), sin notas clínicas; la respuesta y los argumentos
  vuelven a sus valores reales antes de mostrarse o ejecutarse.
- Una sesión de opencode por usuario (la primera carga ~40k tokens del propio OpenCode; las siguientes, cientos).
"""

import base64
import io
import json
import logging
import re
import time
from datetime import datetime

from app.extensions import db
from app.models.ai_external_call import AiExternalCall
from app.models.system_setting import SystemSetting
from app.services import opencode_client as oc
from app.services.ai_privacy import Vault
from app.services.opencode_client import OpencodeUnavailableError

logger = logging.getLogger(__name__)

MAX_STEPS = 4
SESSION_TTL = 6 * 3600
SESSION_MAX_TURNS = 40

DEFAULTS = {
    'ai.opencode.enabled': '0',
    'ai.opencode.roles': 'admin',
    'ai.dev_mode.enabled': '0',
}

_sessions: dict = {}


class _PartialError(Exception):
    """opencode falló después de ejecutar una tool: se responde con lo hecho, sin reintentar por otra vía."""


# ── Ajustes ────────────────────────────────────────────────────────────────────


def setting(key):
    row = db.session.get(SystemSetting, key)
    return row.value if row and row.value not in (None, '') else DEFAULTS[key]


def settings():
    return {
        'enabled': setting('ai.opencode.enabled') == '1',
        'roles': [r for r in setting('ai.opencode.roles').split(',') if r],
        'dev_mode': setting('ai.dev_mode.enabled') == '1',
    }


def save_settings(values, user_id=None):
    mapping = {'enabled': 'ai.opencode.enabled', 'dev_mode': 'ai.dev_mode.enabled'}
    for field, key in mapping.items():
        if field in (values or {}):
            row = db.session.get(SystemSetting, key) or SystemSetting(key=key)
            row.value = '1' if values[field] else '0'
            row.updated_by_id = user_id
            db.session.add(row)
    db.session.commit()
    if (values or {}).get('enabled'):
        oc.unblock('chat')
    return settings()


def enabled_for(user):
    if not user or not oc.configured('chat') or oc.blocked('chat'):
        return False
    conf = settings()
    return conf['enabled'] and user.role in conf['roles']


def dev_enabled_for(user):
    return bool(user and user.role == 'admin' and settings()['dev_mode'] and oc.configured('dev'))


def status():
    return {
        **settings(),
        'chat': {**oc.state('chat'), 'online': oc.ping('chat') if oc.configured('chat') else False},
        'dev': {**oc.state('dev'), 'online': oc.ping('dev') if oc.configured('dev') else False},
        'usage_today': usage_today(),
    }


def usage_today():
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.session.query(
            AiExternalCall.route,
            db.func.count(AiExternalCall.id),
            db.func.coalesce(db.func.sum(AiExternalCall.tokens_in), 0),
            db.func.coalesce(db.func.sum(AiExternalCall.tokens_out), 0),
            db.func.sum(db.case((AiExternalCall.ok.is_(False), 1), else_=0)),
        )
        .filter(AiExternalCall.created_at >= start)
        .group_by(AiExternalCall.route)
        .all()
    )
    return {
        r: {'calls': c, 'tokens_in': int(ti), 'tokens_out': int(to), 'errors': int(e or 0)} for r, c, ti, to, e in rows
    }


def _log(user_id, route, started, *, result=None, error=None, doc_type=None, tools=None):
    tokens = (result or {}).get('tokens') or {}
    try:
        db.session.add(
            AiExternalCall(
                user_id=user_id,
                route=route,
                doc_type=doc_type,
                tools=','.join(tools or [])[:300] or None,
                tokens_in=int(tokens.get('input') or 0),
                tokens_out=int(tokens.get('output') or 0),
                ms=int((time.time() - started) * 1000),
                ok=error is None,
                error=str(error)[:300] if error else None,
            )
        )
        db.session.commit()
    except Exception:  # noqa: BLE001 - el registro nunca rompe el chat
        db.session.rollback()


# ── Sesiones ───────────────────────────────────────────────────────────────────


def _session(user, kind='chat'):
    key = (user.id, kind)
    s = _sessions.get(key)
    if s and (time.time() - s['at'] > SESSION_TTL or s['turns'] >= SESSION_MAX_TURNS):
        oc.delete_session(s['sid'], inst='dev' if kind == 'dev' else 'chat')
        s = None
    if not s:
        inst = 'dev' if kind == 'dev' else 'chat'
        s = {'sid': oc.create_session(f'moscowle {kind} u{user.id}', inst=inst), 'at': time.time(), 'turns': 0}
        s['vault'] = Vault()
        s['primed'] = False
        _sessions[key] = s
    s['turns'] += 1
    return s


def reset(user_id):
    for kind in ('chat:grande', 'chat:chiquito', 'dev', 'vision'):
        s = _sessions.pop((user_id, kind), None)
        if s:
            oc.delete_session(s['sid'], inst='dev' if kind == 'dev' else 'chat')


# ── Prompt ─────────────────────────────────────────────────────────────────────


def _catalog(tools):
    lines = []
    for t in tools:
        fn = t['function']
        props = (fn.get('parameters') or {}).get('properties') or {}
        req = set((fn.get('parameters') or {}).get('required') or [])
        params = ', '.join(f'{k}{"" if k in req else "?"}:{(v or {}).get("type", "any")}' for k, v in props.items())
        desc = re.split(r'(?<=[.!?])\s', (fn.get('description') or '').strip(), maxsplit=1)[0][:160]
        lines.append(f'- {fn["name"]}({params}) — {desc}')
    return '\n'.join(lines)


def _primer(user, tools, write_names, mode='grande'):
    from app.services.report_service import lima_today

    if mode == 'chiquito':
        # El panel pequeño es de solo lectura: el modelo debe decir cómo crear/editar, no que «no se puede».
        mode_rule = (
            'MODO SOLO LECTURA (panel pequeño del chat): aquí no hay herramientas de escritura. Si el usuario pide '
            'crear, editar, registrar, cobrar o borrar algo, responde que sí se puede pero desde el asistente en '
            'PANTALLA COMPLETA (botón de expandir arriba a la derecha del chat, modo «Completo»), y que ahí '
            'se lo preparas para confirmar. No digas que el sistema no tiene esas herramientas.\n\n'
        )
    else:
        mode_rule = 'MODO COMPLETO: puedes proponer herramientas de escritura (el usuario las confirma).\n\n'
    return (
        'Eres el asistente del Centro de Terapias Juan Pablo II (sistema Moscowle). Hablas español de Perú, '
        'claro y breve. NO trabajas con código ni archivos: no uses tus herramientas de código (bash, read, edit, '
        'etc.); para datos del centro usa SOLO las herramientas del sistema de abajo, que ejecuta Moscowle.\n\n'
        f'Fecha de hoy (Lima): {lima_today().isoformat()}. Usuario: rol {user.role}.\n'
        + mode_rule
        + 'Los nombres, correos, teléfonos y DNI llegan como fichas («P1», «E1», «C1», «D1»): úsalas tal cual en '
        'los argumentos y en tus respuestas; el sistema las traduce.\n\n'
        'En CADA respuesta devuelve SOLO un bloque ```json``` con el siguiente paso:\n'
        '{"kind": "tool", "tool": "<nombre>", "args": {...}, "reason": "<por qué, 1 línea>"}\n'
        '{"kind": "answer", "answer": "<respuesta final al usuario, puede usar markdown>"}\n'
        '{"kind": "clarify", "question": "<pregunta corta si falta un dato imprescindible>"}\n'
        'Reglas: nunca inventes datos del centro; si necesitas un dato, pide la herramienta. Las herramientas '
        f'de escritura ({", ".join(sorted(write_names)) or "ninguna"}) siempre las confirma el usuario: '
        'propónlas con los argumentos completos. Si una herramienta devuelve error, explícalo.\n\n'
        f'Herramientas del sistema:\n{_catalog(tools)}\n'
    )


_JSON_BLOCK = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.S)


def parse_step(text):
    """Extrae el JSON del paso. Si el modelo respondió en prosa, se toma como respuesta final."""
    text = (text or '').strip()
    candidates = [m.group(1) for m in _JSON_BLOCK.finditer(text)]
    if not candidates:
        first, last = text.find('{'), text.rfind('}')
        if first != -1 and last > first:
            candidates = [text[first : last + 1]]
    for raw in candidates:
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get('kind') in ('tool', 'answer', 'clarify'):
            return data
    return {'kind': 'answer', 'answer': text} if text else None


# ── Bucle del chat ─────────────────────────────────────────────────────────────


def _run(user, message, *, history=None, mode='grande', confirmed_tool=None):
    """Generador de eventos (dicts) del turno. Lanza `OpencodeUnavailableError` si hay que caer a la cadena actual.

    Eventos: thinking{content, kind, tool?} · tool_call{name, args} · tool_result{name, result, success}
    · confirm{name, args} · final{content} · done{tool_calls, pending_confirm?}
    """
    from app.services.mcp_service import _trim_tool_result
    from app.services.tools_registry import SAFE_WRITE_TOOLS, TOOL_REGISTRY, execute_tool, get_tools_for_mode

    tools = get_tools_for_mode(mode, user.role)
    allowed = {t['function']['name'] for t in tools}
    writes = {n for n in allowed if TOOL_REGISTRY[n]['category'] == 'write' and n not in SAFE_WRITE_TOOLS}

    # Una sesión por modo: el catálogo de tools cambia entre el panel pequeño (lectura) y pantalla completa.
    s = _session(user, f'chat:{mode}')
    vault: Vault = s['vault']
    used: list[str] = []
    tool_calls: list[dict] = []
    started = time.time()

    def ask(text):
        t0 = time.time()
        try:
            res = oc.send(s['sid'], text)
        except OpencodeUnavailableError as exc:
            _log(user.id, 'chat', t0, error=exc, tools=used)
            _sessions.pop((user.id, f'chat:{mode}'), None)
            if tool_calls:
                # Ya se ejecutó algo: no se cae a la cadena de respaldo (lo repetiría).
                raise _PartialError(str(exc)) from exc
            raise
        _log(user.id, 'chat', t0, result=res, tools=used)
        return parse_step(res['text'])

    prefix = ''
    if not s['primed']:
        prefix = _primer(user, tools, writes, mode) + '\n'
        recent = [h for h in (history or [])[-6:] if h.get('content')]
        if recent:
            prefix += 'Conversación reciente:\n' + '\n'.join(
                f'{h["role"]}: {vault.mask_text(str(h["content"])[:600])}' for h in recent
            )
            prefix += '\n\n'
        s['primed'] = True

    yield {'type': 'thinking', 'content': 'Pensando con MiMo (opencode)...', 'kind': 'route'}

    if confirmed_tool and confirmed_tool.get('name'):
        name = confirmed_tool['name']
        args = confirmed_tool.get('args') or {}
        if name not in allowed:
            yield {'type': 'final', 'content': f'No tienes permisos para usar {name}.'}
            yield {'type': 'done', 'tool_calls': []}
            return
        yield {
            'type': 'thinking',
            'content': f'Ejecutando la acción confirmada: {name}...',
            'kind': 'tool',
            'tool': name,
        }
        yield {'type': 'tool_call', 'name': name, 'args': args}
        result = execute_tool(name, args, user_id=user.id, role=user.role)
        ok = not (isinstance(result, dict) and 'error' in result)
        tool_calls.append({'name': name, 'args': args, 'result': result})
        used.append(name)
        yield {'type': 'tool_result', 'name': name, 'result': _trim_tool_result(result), 'success': ok}
        step = ask(
            prefix
            + f'El usuario CONFIRMÓ y el sistema YA ejecutó {name}. Resultado:\n'
            + vault.mask_text(_trim_tool_result(vault.mask(result)))
            + '\nResponde con {"kind": "answer"} contando el resultado (no vuelvas a pedir la herramienta).'
        )
    else:
        step = ask(prefix + 'Usuario: ' + vault.mask_text(message))

    for _ in range(MAX_STEPS):
        if not step:
            break
        if step['kind'] == 'tool':
            name = step.get('tool') or ''
            args = vault.unmask(step.get('args') if isinstance(step.get('args'), dict) else {})
            if name not in allowed:
                step = ask(
                    f'La herramienta "{name}" no existe o tu rol no puede usarla. Elige otra de la lista o responde.'
                )
                continue
            if step.get('reason'):
                yield {'type': 'thinking', 'content': vault.unmask(step['reason'])[:200], 'kind': 'tool', 'tool': name}
            yield {'type': 'tool_call', 'name': name, 'args': args}
            if name in writes:
                yield {'type': 'confirm', 'name': name, 'args': args}
                yield {'type': 'done', 'tool_calls': tool_calls, 'pending_confirm': {'name': name, 'args': args}}
                return
            result = execute_tool(name, args, user_id=user.id, role=user.role)
            ok = not (isinstance(result, dict) and 'error' in result)
            tool_calls.append({'name': name, 'args': args, 'result': result})
            used.append(name)
            trimmed = _trim_tool_result(result)
            yield {'type': 'tool_result', 'name': name, 'result': trimmed, 'success': ok}
            yield {
                'type': 'thinking',
                'content': f'Analizando el resultado de {name}...',
                'kind': 'synth',
                'tool': name,
            }
            step = ask(
                f'Resultado de {name}:\n{vault.mask_text(_trim_tool_result(vault.mask(result)))}\n'
                'Siguiente paso (mismo formato JSON).'
            )
            continue
        text = step.get('answer') if step['kind'] == 'answer' else step.get('question')
        yield {'type': 'final', 'content': vault.unmask(text or '').strip() or 'Listo.'}
        yield {'type': 'done', 'tool_calls': tool_calls}
        return

    logger.info('opencode: sin respuesta final tras %s pasos (%.1fs)', MAX_STEPS, time.time() - started)
    yield {
        'type': 'final',
        'content': 'Necesité demasiados pasos para esto. ¿Puedes pedirlo por partes?'
        if step
        else 'No pude generar una respuesta.',
    }
    yield {'type': 'done', 'tool_calls': tool_calls}


def run(user, message, **kw):
    """Generador de eventos del turno (ver `_run`). Lanza `OpencodeUnavailableError` solo si no se ejecutó nada."""
    executed: list[str] = []
    try:
        for ev in _run(user, message, **kw):
            if ev['type'] == 'tool_result':
                executed.append(ev['name'])
            yield ev
    except _PartialError as exc:
        done = ', '.join(executed) or 'la acción'
        yield {
            'type': 'final',
            'content': f'Ejecuté {done}, pero MiMo dejó de responder antes de redactar el resumen ({exc}). '
            'Revisa el resultado en la traza.',
        }
        yield {'type': 'done', 'tool_calls': []}


def run_dict(user, message, **kw):
    """Versión no streaming (para `/mcp/chat` y Telegram): mismo contrato que `process_message`."""
    out = {'response': '', 'tool_calls': [], 'done': True, 'provider': 'opencode'}
    for ev in run(user, message, **kw):
        if ev['type'] == 'final':
            out['response'] = ev['content']
        elif ev['type'] == 'done':
            out['tool_calls'] = ev.get('tool_calls') or []
            if ev.get('pending_confirm'):
                out.update(
                    response='Acción pendiente de confirmación.',
                    done=False,
                    requires_confirmation=True,
                    pending_tool=ev['pending_confirm'],
                )
    return out


# ── Modo desarrollador ─────────────────────────────────────────────────────────


def run_dev(user, message):
    """Modo desarrollador (solo admin): OpenCode con lectura del repo y comandos de la lista blanca."""
    s = _session(user, 'dev')
    t0 = time.time()
    prefix = ''
    if not s['primed']:
        prefix = (
            'Modo desarrollador de Moscowle (solo lectura). Repo: /home/diego/moscowle_ia (Flask + Angular). '
            'Servicio: `moscowle` (gunicorn). Diagnostica con lectura de código, logs (`journalctl -u moscowle`), '
            '`systemctl status`, `git log/diff`. NO modifiques archivos ni reinicies servicios: si hace falta, '
            'explica el cambio. Nunca leas ni muestres .env, llaves o contraseñas. Responde en español.\n\n'
        )
        s['primed'] = True
    yield {'type': 'thinking', 'content': 'Revisando el servidor con OpenCode...', 'kind': 'route'}
    try:
        res = oc.send(s['sid'], prefix + message, timeout=240, inst='dev')
    except OpencodeUnavailableError as exc:
        _log(user.id, 'dev', t0, error=exc)
        _sessions.pop((user.id, 'dev'), None)
        raise
    _log(user.id, 'dev', t0, result=res, tools=[t['tool'] or '' for t in res['tools']])
    for t in res['tools']:
        cmd = (t.get('input') or {}).get('command') or (t.get('input') or {}).get('filePath') or ''
        yield {
            'type': 'thinking',
            'content': f'{t["tool"]}: {str(cmd)[:160]} ({t.get("status")})',
            'kind': 'tool',
            'tool': t['tool'],
        }
    for p in res['permissions']:
        if p['reply'] == 'reject':
            yield {'type': 'thinking', 'content': f'Bloqueado: {p["permission"]} {p["patterns"]}', 'kind': 'guard'}
    yield {'type': 'final', 'content': res['text'] or 'Sin respuesta.'}
    yield {'type': 'done', 'tool_calls': []}


# ── Imágenes ───────────────────────────────────────────────────────────────────

VISION_PROMPT = (
    'Mira la imagen (un documento de un centro de terapias en Perú). NO inventes: lo que no se lea va en null. '
    'Devuelve SOLO un bloque ```json``` con:\n'
    '{"doc_type": "voucher"|"expense_receipt"|"other", "confidence": 0-1,\n'
    ' "fields": {"amount": number|null, "date": "YYYY-MM-DD"|null, "method": "Yape"|"Plin"|"Transferencia"|'
    '"Efectivo"|"Tarjeta"|null, "reference": "n° de operación"|null, "payer": "nombre de quien paga"|null,\n'
    '  "vendor": "comercio o proveedor (recibos)"|null, "category": "material"|"servicios"|"alquiler"|"limpieza"|'
    '"transporte"|"alimentos"|"mantenimiento"|"otros"|null, "description": "1 línea"|null},\n'
    ' "warnings": ["..."]}\n'
    'voucher = comprobante de un pago recibido (Yape, Plin, transferencia, depósito). expense_receipt = boleta, '
    'factura o recibo de una compra/gasto del centro.'
)


def _image_payload(path, max_side=1600):
    from PIL import Image

    with Image.open(path) as src:
        im = src.convert('RGB')
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=85)
    return {
        'mime': 'image/jpeg',
        'filename': 'documento.jpg',
        'url': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(),
    }


def extract_image(user, path):
    """Lee un comprobante o recibo con MiMo. Devuelve el contrato de extracción + aviso de duplicado."""
    from app.models.payment import Payment

    t0 = time.time()
    try:
        sid = oc.create_session(f'moscowle vision u{user.id}')
        res = oc.send(sid, VISION_PROMPT, images=[_image_payload(path)], timeout=120)
        oc.delete_session(sid)
    except OpencodeUnavailableError as exc:
        _log(user.id, 'vision', t0, error=exc)
        raise
    data = parse_step_json(res['text']) or {}
    fields = data.get('fields') if isinstance(data.get('fields'), dict) else {}
    doc_type = data.get('doc_type') if data.get('doc_type') in ('voucher', 'expense_receipt', 'other') else 'other'
    _log(user.id, 'vision', t0, result=res, doc_type=doc_type)
    warnings = [str(w) for w in (data.get('warnings') or []) if w][:5]
    ref = (fields.get('reference') or '').strip() if isinstance(fields.get('reference'), str) else ''
    if doc_type == 'voucher' and ref and Payment.query.filter(Payment.reference == ref).first():
        warnings.insert(0, f'Ya hay un pago registrado con la operación {ref}: puede ser un comprobante duplicado.')
    try:
        confidence = float(data.get('confidence') or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    return {'doc_type': doc_type, 'confidence': confidence, 'fields': fields, 'warnings': warnings}


def parse_step_json(text):
    m = _JSON_BLOCK.search(text or '')
    raw = m.group(1) if m else None
    if not raw:
        first, last = (text or '').find('{'), (text or '').rfind('}')
        raw = text[first : last + 1] if first != -1 and last > first else None
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None
