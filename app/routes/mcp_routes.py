import base64
import json
import logging
import os
import re
import tempfile
import uuid
from contextlib import nullcontext

import requests as req
from flask import Blueprint, Response, current_app, has_app_context, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.auth_compat import current_user
from app.models import User
from app.services.audit_service import transcribe_audio
from app.services.llm_client import (
    get_gemini_model,
    llm_chat_stream,
)
from app.services.mcp_service import (
    ACTION_CLAIM_RE,
    HONEST_NO_ACTION,
    MCPService,
    _build_local_system_prompt,
    _force_intent_tool,
    _is_ollama_primary,
    _is_smalltalk,
    _parse_text_tool_call,
    _remote_ok,
    _select_local_tools,
    _trim_tool_result,
    normalize_number_spaces,
    resolve_system_prompt,
    should_escalate_to_remote,
    strip_tool_calls,
    tool_result_context,
)
from app.services.mcp_trace import TraceBuilder
from app.services.tools_registry import (
    SAFE_WRITE_TOOLS,
    TOOL_REGISTRY,
    execute_tool,
    get_tools_for_mode,
)

logger = logging.getLogger('app.mcp')

mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp')

mcp_service = MCPService()

ALLOWED_ORIGINS = [
    'https://moscowle.centrojuanpabloii.com',
    'https://centrojuanpabloii.com',
    'http://localhost:4200',
]

# Write tools that are safe to run without a confirmation gate.
# (Shared SAFE_WRITE_TOOLS lives in tools_registry.py)

# Anti-false-positive guard: if the LLM claims to have completed an action (or
# claims it consulted the DB) but did NOT actually run any tool in this turn,
# we append a visible warning so the user never trusts a hallucinated result.
_ACTION_CLAIM_RE = re.compile(
    r'(se ha creado|se creó|usuario creado|fue creado[^ ]*|ha sido creado[^ ]*|he creado|ya creé'
    r'|se ha registrado|registrado correctamente|se registró|he registrado|ya registré'
    r'|se actualizó|se ha actualizado|he actualizado'
    r'|se eliminó|se ha eliminado|se canceló|se ha cancelado'
    r'|se ha enviado|se envió|se guardó|se ha guardado|se ha completado|se completó'
    r'|asigné a|asigné la|se asignó|se le asignó|asignad[oa]|agregué a|se agregó|asocié a|se asoció'
    r'|confirmando|procediendo a la|procedo a la|listo[ ,]|hecho[ ,])',
    re.IGNORECASE,
)

_FAKE_VERIFY_RE = re.compile(
    r'(existe en el sistema|no existe en el sistema|existe el usuario|no existe el usuario'
    r'|el resultado fue truncado|fue truncado|null[^,]*)',
    re.IGNORECASE,
)

# El modelo afirma una CANTIDAD o dato del sistema sin haber ejecutado herramienta.
# (p.ej. "Hay 7 terapeutas", "6 pacientes registrados", "total: 12").
_DATA_CLAIM_RE = re.compile(
    r'(?:hay|existen|son|total(?:\s+dé\s+|de\s+)?|registrad[oa]s?|encontrad[oa]s?|tienen?|cuenta\s+con)\s*[:>]*\s*\d{1,4}'
    r'|\b\d{1,4}\s+(?:terapeutas?|paciente[s]?|usuarios?|alumnos?|sesiones?|pagos?|sede[s]?|contratos?|incidentes?|grupos?)\b',
    re.IGNORECASE,
)


def _is_write_tool(name):
    entry = TOOL_REGISTRY.get(name)
    return bool(entry) and entry.get('category') == 'write'


def _requires_confirmation(name):
    return _is_write_tool(name) and name not in SAFE_WRITE_TOOLS


CHIPS_AFTER_TOOL = {
    'register_payment': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
        {'id': 'act-debtors', 'type': 'action', 'label': 'Mostrar deudores del mes', 'icon': 'exclamation-circle'},
    ],
    'cancel_payment': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
    'edit_payment': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
    'send_payment_reminder': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
    'pay_installment': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
    'create_session': [
        {
            'id': 'nav-sessions',
            'type': 'navigation',
            'label': 'Ver sesiones',
            'icon': 'calendar',
            'target': '/admin/sessions',
        },
        {'id': 'act-more-sessions', 'type': 'action', 'label': 'Crear otra sesión', 'icon': 'calendar-plus'},
    ],
    'update_session': [
        {
            'id': 'nav-sessions',
            'type': 'navigation',
            'label': 'Ver sesiones',
            'icon': 'calendar',
            'target': '/admin/sessions',
        },
    ],
    'cancel_session': [
        {
            'id': 'nav-sessions',
            'type': 'navigation',
            'label': 'Ver sesiones',
            'icon': 'calendar',
            'target': '/admin/sessions',
        },
    ],
    'complete_session': [
        {
            'id': 'nav-sessions',
            'type': 'navigation',
            'label': 'Ver sesiones',
            'icon': 'calendar',
            'target': '/admin/sessions',
        },
    ],
    'batch_create_sessions': [
        {
            'id': 'nav-sessions',
            'type': 'navigation',
            'label': 'Ver sesiones',
            'icon': 'calendar',
            'target': '/admin/sessions',
        },
    ],
    'create_user': [
        {'id': 'nav-users', 'type': 'navigation', 'label': 'Ver usuarios', 'icon': 'users', 'target': '/admin/users'},
    ],
    'update_user': [
        {'id': 'nav-users', 'type': 'navigation', 'label': 'Ver usuarios', 'icon': 'users', 'target': '/admin/users'},
    ],
    'delete_user': [
        {'id': 'nav-users', 'type': 'navigation', 'label': 'Ver usuarios', 'icon': 'users', 'target': '/admin/users'},
    ],
    'toggle_user_status': [
        {'id': 'nav-users', 'type': 'navigation', 'label': 'Ver usuarios', 'icon': 'users', 'target': '/admin/users'},
    ],
    'assign_therapist': [
        {
            'id': 'nav-sessions',
            'type': 'navigation',
            'label': 'Ver sesiones',
            'icon': 'calendar',
            'target': '/admin/sessions',
        },
    ],
    'create_incident': [
        {
            'id': 'nav-incidents',
            'type': 'navigation',
            'label': 'Ver incidencias',
            'icon': 'exclamation-triangle',
            'target': '/admin/incidents',
        },
    ],
    'update_incident_status': [
        {
            'id': 'nav-incidents',
            'type': 'navigation',
            'label': 'Ver incidencias',
            'icon': 'exclamation-triangle',
            'target': '/admin/incidents',
        },
    ],
    'assign_incident': [
        {
            'id': 'nav-incidents',
            'type': 'navigation',
            'label': 'Ver incidencias',
            'icon': 'exclamation-triangle',
            'target': '/admin/incidents',
        },
    ],
    'create_expense': [
        {
            'id': 'nav-expenses',
            'type': 'navigation',
            'label': 'Ver gastos',
            'icon': 'wallet',
            'target': '/admin/expenses',
        },
    ],
    'broadcast_message': [
        {
            'id': 'nav-messages',
            'type': 'navigation',
            'label': 'Ver mensajes',
            'icon': 'envelope',
            'target': '/admin/messages',
        },
    ],
    'send_direct_message': [
        {
            'id': 'nav-messages',
            'type': 'navigation',
            'label': 'Ver mensajes',
            'icon': 'envelope',
            'target': '/admin/messages',
        },
    ],
    'update_patient': [
        {'id': 'act-patient-detail', 'type': 'action', 'label': 'Ver detalle del paciente', 'icon': 'user'},
    ],
    'update_patient_details': [
        {'id': 'act-patient-detail', 'type': 'action', 'label': 'Ver detalle del paciente', 'icon': 'user'},
    ],
    'create_patient_group': [
        {'id': 'act-list-groups', 'type': 'action', 'label': 'Listar grupos de pacientes', 'icon': 'users'},
    ],
    'create_contract': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
    'update_contract': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
    'cancel_contract': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
    'reactivate_contract': [
        {
            'id': 'nav-payments',
            'type': 'navigation',
            'label': 'Ver pagos',
            'icon': 'receipt',
            'target': '/admin/payments',
        },
    ],
}


def _next_action_chips(tool_name):
    return list(CHIPS_AFTER_TOOL.get(tool_name, []))


def _cors_headers():
    origin = request.headers.get('Origin', '')
    if origin in ALLOWED_ORIGINS:
        return {
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-CSRFToken',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        }
    return {}


@mcp_bp.before_request
def mcp_options_preflight():
    if request.method == 'OPTIONS':
        resp = current_app.make_default_options_response()
        for k, v in _cors_headers().items():
            resp.headers[k] = v
        resp.headers['Access-Control-Max-Age'] = '3600'
        return resp


def _get_current_user():
    """Get current user from JWT or session."""
    try:
        verify_jwt_in_request(locations=['cookies', 'headers'])
        uid = get_jwt_identity()
        return User.query.get(int(uid))
    except Exception:
        if current_user and current_user.is_authenticated:
            return current_user
        return None


@mcp_bp.route('/chat', methods=['POST'])
def mcp_chat():
    """Send a message and get a response with tool calls."""
    user = _get_current_user()
    cors = _cors_headers()
    if not user:
        resp = jsonify({'error': 'No autenticado'})
        resp.status_code = 401
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    mode = data.get('mode', 'grande')
    history = data.get('history', [])

    if not message:
        resp = jsonify({'error': 'Mensaje requerido'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    try:
        result = mcp_service.process_message(
            message=message,
            user_role=user.role,
            user_id=user.id,
            mode=mode,
            history=history,
        )
        try:
            from app.services.unanswered_questions import note_if_unanswered

            note_if_unanswered(result, message, 'chat web')
        except Exception:
            logger.exception('No se pudo registrar la pregunta sin respuesta')
        resp = jsonify(result)
        for k, v in cors.items():
            resp.headers[k] = v
        return resp
    except Exception as e:
        logger.error(f'MCP chat error: {e}', exc_info=True)
        resp = jsonify({'error': f'Error del servidor: {str(e)}'})
        resp.status_code = 500
        for k, v in cors.items():
            resp.headers[k] = v
        return resp


@mcp_bp.route('/chat/stream', methods=['POST'])
def mcp_chat_stream():
    """Send a message and stream the response via SSE with progress indicators."""
    user = _get_current_user()
    cors = _cors_headers()
    _app = current_app._get_current_object()

    if not user:
        resp = jsonify({'error': 'No autenticado'})
        resp.status_code = 401
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    mode = data.get('mode', 'grande')
    history = data.get('history', [])

    if not message:
        resp = jsonify({'error': 'Mensaje requerido'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    def generate():
        # Solo empuja un app_context si no hay ninguno activo: en el test client
        # (y en cualquier request viva) hacerlo reinicia la sesión de SQLAlchemy
        # y rompe la transacción anidada del fixture de tests.
        _ctx = nullcontext() if has_app_context() else _app.app_context()
        with _ctx:
            trace = TraceBuilder()
            try:
                # Send thinking indicator (legacy payload + structured step)
                yield trace.thinking('Evaluando tu petición...', 'route')

                tools = get_tools_for_mode(mode, user.role)
                local_mode = _is_ollama_primary()
                # Acciones de escritura -> proveedor en la nube: el router local inventaba el resultado.
                escalated = bool(
                    local_mode
                    and not (data.get('confirmed_tool') or {}).get('name')
                    and should_escalate_to_remote(message, history)
                )
                if escalated:
                    logger.info('MCP stream: pedido de escritura derivado del modelo local a la nube')
                    local_mode = False
                chain_kw = {'exclude': ('ollama',)} if escalated else {}
                if local_mode:
                    local_tools = _select_local_tools(tools, message, user_role=user.role)
                    full_system = _build_local_system_prompt(
                        user.role, user.id, mode, message, selected_tools=local_tools
                    )
                else:
                    # resolve_system_prompt ya incluye fecha + catálogo + acceso
                    full_system = resolve_system_prompt(user.role, user_id=user.id, mode=mode, tools=tools)
                messages = [{'role': 'system', 'content': full_system}]

                if history:
                    for h in history[-5:]:
                        messages.append({'role': h['role'], 'content': h['content']})

                messages.append({'role': 'user', 'content': message})

                tool_calls_log = []
                last_result_str = ''
                streamed_text = ''
                final_answer = None
                confirmed_tool = data.get('confirmed_tool') or {}
                corrections = 0

                # If the user confirmed a pending write action in the modal,
                # execute it now and feed the real result back into the conversation
                # so the LLM can produce the final answer (it must NOT re-call the tool).
                if confirmed_tool.get('name'):
                    cname = confirmed_tool['name']
                    cargs = confirmed_tool.get('args') or {}
                    ctool_call_text = confirmed_tool.get('tool_call_text') or (
                        f'<function={cname}{json.dumps(cargs, ensure_ascii=False)}</function>'
                    )
                    if _requires_confirmation(cname):
                        yield trace.thinking(
                            f'Ejecutando la acción confirmada: llamando a {cname}...', 'tool', tool=cname
                        )
                        tc_data = {'type': 'tool_call', 'name': cname, 'args': cargs}
                        trace.tool_call(cname, cargs)
                        yield f'data: {json.dumps(tc_data, ensure_ascii=False)}\n\n'

                        result = execute_tool(cname, cargs, user_id=user.id, role=user.role)
                        tool_calls_log.append({'name': cname, 'args': cargs, 'result': result})

                        trimmed = _trim_tool_result(result)
                        success = not (isinstance(result, dict) and 'error' in result)
                        trace.tool_result(cname, success)
                        tr_data = {'type': 'tool_result', 'name': cname, 'result': trimmed, 'success': success}
                        yield f'data: {json.dumps(tr_data, ensure_ascii=False)}\n\n'

                        last_result_str = _trim_tool_result(result)
                        messages.append({'role': 'assistant', 'content': ctool_call_text})
                        messages.append(
                            {
                                'role': 'user',
                                'content': tool_result_context(cname, last_result_str, already_executed=True),
                            }
                        )

                        chips = _next_action_chips(cname)
                        if chips:
                            yield f'data: {json.dumps({"type": "chips", "chips": chips}, ensure_ascii=False)}\n\n'

                        yield trace.thinking('Procesando resultado...', 'result')

                # Intent determinista: si el mensaje corresponde a un reporte inequívoco
                # (agenda de una fecha, sedes, gastos, deudores, grupo de sesiones), se ejecuta
                # la tool sin pasar por el router local. Evita que el modelo de 1.5B emita prosa
                # inventada antes del tool_call y ahorra CPU.
                det_tool = None
                if local_mode and not confirmed_tool.get('name') and not tool_calls_log:
                    det_tool = _force_intent_tool(message, tools, user.role)

                for iteration in range(6):
                    try:
                        full_content = ''
                        # Small-talk local: responder de una (MiniCPM, sin tools) y terminar.
                        if local_mode and iteration == 0 and not confirmed_tool.get('name') and _is_smalltalk(message):
                            for chunk in llm_chat_stream(messages, temperature=0.35, max_tokens=512, phase='tactical'):
                                full_content += chunk
                                if chunk.strip():
                                    streamed_text += chunk
                                    chunk_data = {'type': 'chunk', 'content': chunk}
                                    yield f'data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n'
                            # No se reenvia full_content como 'text': los chunks ya
                            # llevaron la respuesta entera y el frontend CONCATENA
                            # 'text' tras 'chunk' (ai-chat.ts / chat.ts) -> respuesta doble.
                            final_answer = normalize_number_spaces(strip_tool_calls(full_content))
                            _final_ev = json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)
                            yield f'data: {_final_ev}\n\n'
                            done_payload = {
                                'type': 'done',
                                'has_tool_call': False,
                                'trace': trace.as_list(),
                            }
                            yield f'data: {json.dumps(done_payload)}\n\n'
                            return

                        if det_tool and iteration == 0:
                            _det_args = json.dumps(det_tool[1], ensure_ascii=False)
                            full_content = f'<function={det_tool[0]}{_det_args}</function>'
                            logger.info(f'MCP stream intent determinista (sin router): {det_tool[0]}({_det_args})')
                        else:
                            llm_stream_kwargs = {'temperature': 0.3, 'max_tokens': 4096, **chain_kw}
                            if local_mode:
                                # Sin resultado REAL previo todavia -> fase route con tools nativas.
                                local_phase = 'resume' if tool_calls_log or last_result_str else 'route'
                                llm_stream_kwargs['phase'] = local_phase
                                if local_phase == 'route' and not confirmed_tool.get('name'):
                                    llm_stream_kwargs['tools'] = local_tools
                            for chunk in llm_chat_stream(messages, **llm_stream_kwargs):
                                full_content += chunk
                                clean = strip_tool_calls(chunk)
                                if clean.strip():
                                    streamed_text += clean
                                    _cd = {'type': 'chunk', 'content': clean}
                                    yield f'data: {json.dumps(_cd, ensure_ascii=False)}\n\n'

                        if not full_content.strip():
                            trace.add('synth', 'No pude generar una respuesta.')
                            msg = {'type': 'text', 'content': 'No pude generar una respuesta.'}
                            yield f'data: {json.dumps(msg)}\n\n'
                            break

                        tool_name, tool_args = _parse_text_tool_call(full_content)

                        forced = None
                        if local_mode and iteration == 0 and not confirmed_tool.get('name') and not tool_calls_log:
                            forced = _force_intent_tool(message, tools, user.role)
                        if forced:
                            # El intent determinista gana sobre lo que emita el router:
                            # evita paciente/hora alucinados en tools de escritura o de reporte.
                            tool_name, tool_args = forced
                            forced_content = (
                                f'<function={tool_name}{json.dumps(tool_args, ensure_ascii=False)}</function>'
                            )
                            full_content = forced_content
                            logger.info(f'MCP stream deterministic intent tool: {tool_name}({tool_args})')

                        if tool_name:
                            # Never re-execute a tool that was already confirmed & run above.
                            if confirmed_tool.get('name') and tool_name == confirmed_tool['name'] and last_result_str:
                                yield trace.thinking(
                                    f'Analizando el resultado de {tool_name}...', 'synth', tool=tool_name
                                )
                                tool_call_match = re.search(
                                    r'<function=.*?(?:</function>|/\s*>)', full_content, re.DOTALL
                                )
                                clean_assistant = tool_call_match.group(0) if tool_call_match else full_content
                                messages.append({'role': 'assistant', 'content': clean_assistant})
                                messages.append(
                                    {
                                        'role': 'user',
                                        'content': tool_result_context(tool_name, last_result_str),
                                    }
                                )
                                continue

                            # Send tool_call event
                            tc_data = {'type': 'tool_call', 'name': tool_name, 'args': tool_args}
                            trace.tool_call(tool_name, tool_args)
                            yield f'data: {json.dumps(tc_data, ensure_ascii=False)}\n\n'

                            # Write tools require explicit human confirmation before running.
                            if _requires_confirmation(tool_name):
                                confirm_payload = {
                                    'type': 'confirm',
                                    'name': tool_name,
                                    'args': tool_args,
                                    'tool_call_text': full_content,
                                }
                                yield f'data: {json.dumps(confirm_payload, ensure_ascii=False)}\n\n'
                                done_payload = {
                                    'type': 'done',
                                    'pending_confirm': {
                                        'name': tool_name,
                                        'args': tool_args,
                                        'tool_call_text': full_content,
                                    },
                                    'trace': trace.as_list(),
                                }
                                yield f'data: {json.dumps(done_payload, ensure_ascii=False)}\n\n'
                                return

                            result = execute_tool(tool_name, tool_args, user_id=user.id, role=user.role)
                            tool_calls_log.append({'name': tool_name, 'args': tool_args, 'result': result})

                            # Send trimmed tool_result
                            trimmed = _trim_tool_result(result)
                            success = not (isinstance(result, dict) and 'error' in result)
                            trace.tool_result(tool_name, success)
                            tr_data = {'type': 'tool_result', 'name': tool_name, 'result': trimmed, 'success': success}
                            yield f'data: {json.dumps(tr_data, ensure_ascii=False)}\n\n'

                            result_str = _trim_tool_result(result)
                            last_result_str = result_str
                            tool_call_match = re.search(r'<function=.*?(?:</function>|/\s*>)', full_content, re.DOTALL)
                            clean_assistant = tool_call_match.group(0) if tool_call_match else full_content
                            messages.append({'role': 'assistant', 'content': clean_assistant})
                            messages.append(
                                {
                                    'role': 'user',
                                    'content': tool_result_context(tool_name, result_str),
                                }
                            )

                            chips = _next_action_chips(tool_name)
                            if chips:
                                yield f'data: {json.dumps({"type": "chips", "chips": chips}, ensure_ascii=False)}\n\n'

                            # Send thinking indicator for next iteration
                            thinking_msg = f'Analizando el resultado de {tool_name}...'
                            yield trace.thinking(thinking_msg, 'synth', tool=tool_name)
                            continue

                        # No more tool calls — check if the model affirmed a system datum
                        # without having called any tool.  If so, re-prompt up to 2 times.
                        clean_final = strip_tool_calls(full_content).strip()
                        final_answer = normalize_number_spaces(clean_final)
                        if (
                            not confirmed_tool.get('name')
                            and corrections < 2
                            and _DATA_CLAIM_RE.search(clean_final)
                            and not tool_calls_log
                        ):
                            corrections += 1
                            messages.append(
                                {
                                    'role': 'user',
                                    'content': (
                                        '¡ALTO! Tu respuesta afirma un dato del sistema (cantidad, lista o estado), '
                                        'pero NO ejecutaste ninguna herramienta en este turno. Eso está PROHIBIDO. '
                                        'Vuelve a emitir la llamada a la herramienta correspondiente '
                                        '(formato: <function=nombre{"param": "valor"}</function>) '
                                        'y espera su resultado real.'
                                    ),
                                }
                            )
                            thinking_retry = 'Los datos deben venir de una herramienta. Reintentando...'
                            yield trace.thinking(thinking_retry, 'guard')
                            # El intento erróneo ya se transmitió: vacía la burbuja
                            # para que el retry no quede pegado a la respuesta final.
                            yield f'data: {json.dumps({"type": "reset_text"})}\n\n'
                            continue

                        # Afirma haber hecho una acción sin herramienta: se borra la burbuja y se reintenta.
                        if (
                            not confirmed_tool.get('name')
                            and not tool_calls_log
                            and ACTION_CLAIM_RE.search(clean_final)
                        ):
                            yield f'data: {json.dumps({"type": "reset_text"})}\n\n'
                            streamed_text = ''
                            if local_mode and not escalated and _remote_ok():
                                escalated, local_mode = True, False
                                chain_kw = {'exclude': ('ollama',)}
                                messages[0] = {
                                    'role': 'system',
                                    'content': resolve_system_prompt(
                                        user.role, user_id=user.id, mode=mode, tools=tools
                                    ),
                                }
                                messages = messages[:1] + [m for m in messages[1:] if m.get('role') != 'assistant']
                                yield trace.thinking('Preparando la acción con un modelo más capaz...', 'guard')
                                continue
                            if corrections < 2:
                                corrections += 1
                                messages.append(
                                    {
                                        'role': 'user',
                                        'content': (
                                            '¡ALTO! Dijiste que hiciste una acción, pero NO llamaste ninguna '
                                            'herramienta: nada cambió. Si tienes los datos, emite AHORA '
                                            '<function=nombre{"param": "valor"}</function>; si falta un dato '
                                            'obligatorio, pregúntalo sin afirmar nada.'
                                        ),
                                    }
                                )
                                yield trace.thinking(
                                    'La acción debe pasar por una herramienta. Reintentando...', 'guard'
                                )
                                continue
                            final_answer = HONEST_NO_ACTION
                            yield f'data: {json.dumps({"type": "text", "content": HONEST_NO_ACTION}, ensure_ascii=False)}\n\n'
                            break

                        # No more tool calls — final response already streamed
                        break

                    except Exception as e:
                        error_str = str(e)
                        logger.error(f'MCP stream iteration {iteration} error: {error_str}')

                        if 'failed_generation' in error_str:
                            match = re.search(r"'failed_generation':\s*'([^']*)'", error_str)
                            failed_gen = match.group(1) if match else ''
                            if failed_gen:
                                tn, ta = _parse_text_tool_call(failed_gen)
                                if tn:
                                    # Never re-execute an already-confirmed tool.
                                    if confirmed_tool.get('name') and tn == confirmed_tool['name'] and last_result_str:
                                        yield trace.thinking(f'Analizando el resultado de {tn}...', 'synth', tool=tn)
                                        tool_call_match = re.search(
                                            r'<function=.*?(?:</function>|/\s*>)', failed_gen, re.DOTALL
                                        )
                                        clean_assistant = tool_call_match.group(0) if tool_call_match else failed_gen
                                        messages.append({'role': 'assistant', 'content': clean_assistant})
                                        messages.append(
                                            {
                                                'role': 'user',
                                                'content': tool_result_context(tn, last_result_str),
                                            }
                                        )
                                        continue

                                    tc_data = {'type': 'tool_call', 'name': tn, 'args': ta}
                                    trace.tool_call(tn, ta)
                                    yield f'data: {json.dumps(tc_data, ensure_ascii=False)}\n\n'

                                    if _requires_confirmation(tn):
                                        confirm_payload = {
                                            'type': 'confirm',
                                            'name': tn,
                                            'args': ta,
                                            'tool_call_text': failed_gen,
                                        }
                                        yield f'data: {json.dumps(confirm_payload, ensure_ascii=False)}\n\n'
                                        done_payload = {
                                            'type': 'done',
                                            'pending_confirm': {'name': tn, 'args': ta, 'tool_call_text': failed_gen},
                                            'trace': trace.as_list(),
                                        }
                                        yield f'data: {json.dumps(done_payload, ensure_ascii=False)}\n\n'
                                        return

                                    result = execute_tool(tn, ta, user_id=user.id, role=user.role)
                                    tool_calls_log.append({'name': tn, 'args': ta, 'result': result})

                                    trimmed = _trim_tool_result(result)
                                    success = not (isinstance(result, dict) and 'error' in result)
                                    trace.tool_result(tn, success)
                                    tr_data = {'type': 'tool_result', 'name': tn, 'result': trimmed, 'success': success}
                                    yield f'data: {json.dumps(tr_data, ensure_ascii=False)}\n\n'

                                    result_str = _trim_tool_result(result)
                                    last_result_str = result_str
                                    tool_call_match = re.search(
                                        r'<function=.*?(?:</function>|/\s*>)', failed_gen, re.DOTALL
                                    )
                                    clean_assistant = tool_call_match.group(0) if tool_call_match else failed_gen
                                    messages.append({'role': 'assistant', 'content': clean_assistant})
                                    messages.append(
                                        {
                                            'role': 'user',
                                            'content': tool_result_context(tn, result_str),
                                        }
                                    )
                                    chips = _next_action_chips(tn)
                                    if chips:
                                        chips_payload = json.dumps(
                                            {'type': 'chips', 'chips': chips}, ensure_ascii=False
                                        )
                                        yield f'data: {chips_payload}\n\n'
                                    yield trace.thinking(f'Analizando el resultado de {tn}...', 'synth', tool=tn)
                                    continue

                        if iteration >= 2:
                            yield f'data: {json.dumps({"type": "text", "content": f"Error: {error_str[:200]}"})}\n\n'
                            break

                if final_answer is not None:
                    _final_ev = json.dumps({'type': 'final', 'content': final_answer}, ensure_ascii=False)
                    yield f'data: {_final_ev}\n\n'

                if not tool_calls_log and (
                    _ACTION_CLAIM_RE.search(streamed_text) or _FAKE_VERIFY_RE.search(streamed_text)
                ):
                    warning = (
                        '\n\n⚠️ *Aviso:* esta respuesta afirmaba una acción o un dato de la base de datos, '
                        'pero en este turno NO se ejecutó ninguna herramienta del sistema, así que '
                        'esa afirmación puede ser errónea. Si esperabas una acción o un dato real, '
                        'repítelo por favor.'
                    )
                    yield f'data: {json.dumps({"type": "text", "content": warning}, ensure_ascii=False)}\n\n'

                done_final = {'type': 'done', 'tool_calls': tool_calls_log, 'trace': trace.as_list()}
                yield f'data: {json.dumps(done_final, ensure_ascii=False)}\n\n'

            except Exception as e:
                logger.error(f'MCP stream error: {e}', exc_info=True)
                yield f'data: {json.dumps({"type": "error", "error": str(e), "trace": trace.as_list()})}\n\n'

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    headers.update(cors)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers=headers,
    )


@mcp_bp.route('/execute', methods=['POST'])
def mcp_execute():
    """Execute a specific tool by name. Used by MCP bridges."""
    user = _get_current_user()
    cors = _cors_headers()
    if not user:
        resp = jsonify({'error': 'No autenticado'})
        resp.status_code = 401
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    data = request.get_json(silent=True) or {}
    tool_name = data.get('tool_name')
    args = data.get('args', {})

    if not tool_name:
        resp = jsonify({'error': 'tool_name requerido'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    try:
        result = execute_tool(tool_name, args, user_id=user.id, role=user.role)
        resp = jsonify(result)
        for k, v in cors.items():
            resp.headers[k] = v
        return resp
    except Exception as e:
        logger.error(f'MCP execute error for {tool_name}: {e}', exc_info=True)
        resp = jsonify({'error': f'Error ejecutando herramienta: {str(e)}'})
        resp.status_code = 500
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    """List available tools for the current user's role."""
    user = _get_current_user()
    cors = _cors_headers()
    if not user:
        resp = jsonify({'error': 'No autenticado'})
        resp.status_code = 401
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    mode = request.args.get('mode', 'grande')
    tools = mcp_service.get_available_tools(user.role, mode)
    resp = jsonify({'tools': tools, 'count': len(tools), 'role': user.role, 'mode': mode})
    for k, v in cors.items():
        resp.headers[k] = v
    return resp


@mcp_bp.route('/chat/clear', methods=['POST'])
def mcp_clear():
    """Clear chat history (frontend-side, just acknowledge)."""
    cors = _cors_headers()
    resp = jsonify({'success': True, 'message': 'Historial limpiado'})
    for k, v in cors.items():
        resp.headers[k] = v
    return resp


@mcp_bp.route('/upload', methods=['POST'])
def mcp_upload():
    """Upload an image from chat. Returns URL and optional OCR data."""
    user = _get_current_user()
    cors = _cors_headers()
    if not user:
        resp = jsonify({'error': 'No autenticado'})
        resp.status_code = 401
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    if 'file' not in request.files:
        resp = jsonify({'error': 'No file provided'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    file = request.files['file']
    if not file.filename:
        resp = jsonify({'error': 'No filename'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    allowed = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'}
    if ext not in allowed:
        resp = jsonify({'error': f'Tipo no permitido: {ext}. Use: {", ".join(allowed)}'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    unique_name = f'{uuid.uuid4().hex[:12]}.{ext}'
    upload_dir = os.path.join(current_app.instance_path, 'uploads', 'mcp')
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, unique_name))
    logger.info(f'Upload guardado: {unique_name} por usuario {user.id}')

    url = f'/uploads/mcp/{unique_name}'

    ocr_data = None
    if ext in ('jpg', 'jpeg', 'png', 'webp'):
        try:
            ocr_data = _ocr_voucher(os.path.join(upload_dir, unique_name), ext)
            if ocr_data:
                logger.info(f'OCR exitoso: {ocr_data}')
            else:
                logger.warning('OCR retornó None')
        except Exception as e:
            logger.warning(f'OCR exception: {e}')

    resp_data = {'success': True, 'url': url, 'filename': unique_name}
    if ocr_data:
        resp_data['ocr'] = ocr_data

    resp = jsonify(resp_data)
    for k, v in cors.items():
        resp.headers[k] = v
    return resp


@mcp_bp.route('/transcribe', methods=['POST'])
def mcp_transcribe():
    """Transcribe audio from chat. Audio is deleted after transcription."""
    user = _get_current_user()
    cors = _cors_headers()
    if not user:
        resp = jsonify({'error': 'No autenticado'})
        resp.status_code = 401
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    if 'audio' not in request.files:
        resp = jsonify({'error': 'No se recibió archivo de audio'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    file = request.files['audio']
    if not file.filename:
        resp = jsonify({'error': 'No filename'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    allowed = {'webm', 'wav', 'mp3', 'ogg', 'm4a', 'mp4'}
    if ext not in allowed:
        resp = jsonify({'error': f'Tipo de audio no permitido: {ext}. Use: {", ".join(sorted(allowed))}'})
        resp.status_code = 400
        for k, v in cors.items():
            resp.headers[k] = v
        return resp

    tmp_path = os.path.join(tempfile.gettempdir(), f'audio_{uuid.uuid4().hex[:12]}.{ext}')
    try:
        file.save(tmp_path)
        result = transcribe_audio(tmp_path)
        resp = jsonify({'success': True, 'text': result.get('text', '')})
        for k, v in cors.items():
            resp.headers[k] = v
        return resp
    except Exception as e:
        logger.error(f'MCP transcribe error: {e}', exc_info=True)
        resp = jsonify({'error': str(e)})
        resp.status_code = 500
        for k, v in cors.items():
            resp.headers[k] = v
        return resp


def _ocr_voucher(file_path, ext):
    """Use available LLM vision to extract payment data from voucher image."""
    try:
        with open(file_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()

        mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}.get(
            ext, 'image/jpeg'
        )
        prompt = (
            'LEE ESTA IMAGEN CUIDADOSAMENTE. Es un comprobante de pago.\n'
            'NO INVENTES DATOS. Si no puedes leer algo, pon null.\n\n'
            'Busca:\n'
            '- Monto total (el número grande, puede tener S/ o S/.)\n'
            '- Nombre de quien recibe o envía (el nombre completo que aparece)\n'
            '- Fecha (formato: DD mes AAAA o YYYY-MM-DD)\n'
            '- Método de pago (Plin, Yape, Efectivo, Transferencia)\n'
            '- Número de operación o referencia\n\n'
            'Responde SOLO con JSON válido:\n'
            '{"amount": number|null, "method": "Plin"|"Yape"|"Efectivo"|"Transferencia"|null, '
            '"date": "YYYY-MM-DD"|null, "patient_hint": "nombre completo"|null, '
            '"reference": "string"|null}\n\n'
            'EJEMPLO de respuesta correcta: {"amount": 200, "method": "Plin", '
            '"date": "2026-07-22", "patient_hint": "Diego Alejandro Centeno Barrutia", '
            '"reference": "2026077240"}'
        )

        # Try Gemini first
        try:
            gemini = get_gemini_model()

            if gemini:
                response = gemini.generate_content([prompt, {'inline_data': {'mime_type': mime, 'data': img_b64}}])
                text = response.text.strip()

                match = re.search(r'\{[^}]+\}', text)
                if match:
                    logger.info('OCR via Gemini exitoso')
                    return json.loads(match.group())
        except Exception as e:
            logger.warning(f'OCR Gemini failed: {e}')

        # Try Groq with llama vision
        try:
            api_key = os.environ.get('GROQ_API_KEY', '')
            if api_key:
                resp = req.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={
                        'model': 'llama-3.2-11b-vision-preview',
                        'messages': [
                            {
                                'role': 'user',
                                'content': [
                                    {'type': 'text', 'text': prompt},
                                    {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{img_b64}'}},
                                ],
                            },
                        ],
                        'max_tokens': 300,
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    text = resp.json()['choices'][0]['message']['content']
                    match = re.search(r'\{[^}]+\}', text)
                    if match:
                        logger.info('OCR via Groq exitoso')
                        return json.loads(match.group())
        except Exception as e:
            logger.warning(f'OCR Groq failed: {e}')

        logger.warning('OCR: ningún proveedor disponible')
        return None
    except Exception as e:
        logger.warning(f'OCR error: {e}')
        return None
