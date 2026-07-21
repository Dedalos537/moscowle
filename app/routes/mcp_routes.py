import json
import logging

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from groq import Groq

from app.auth_compat import current_user
from app.models import User
from app.services.mcp_service import SYSTEM_PROMPTS, MCPService
from app.services.tools_registry import execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp')

mcp_service = MCPService()

ALLOWED_ORIGINS = [
    'https://moscowle.centrojuanpabloii.com',
    'https://centrojuanpabloii.com',
    'http://localhost:4200',
]


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
    """Send a message and stream the response via SSE."""
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
        with _app.app_context():
            try:
                api_key = _app.config.get('GROQ_API_KEY')
                client = Groq(api_key=api_key)
                tools = get_tools_for_mode(mode, user.role)
                system_prompt = SYSTEM_PROMPTS.get(user.role, SYSTEM_PROMPTS['jugador'])
                messages = [{'role': 'system', 'content': system_prompt}]

                if history:
                    for h in history[-20:]:
                        messages.append({'role': h['role'], 'content': h['content']})

                messages.append({'role': 'user', 'content': message})

                full_response = ''
                tool_calls_log = []

                for _iteration in range(5):
                    kwargs = {
                        'model': 'llama-3.1-8b-instant',
                        'messages': messages,
                        'max_tokens': 4096,
                        'temperature': 0.3,
                    }
                    if tools:
                        kwargs['tools'] = tools
                        kwargs['tool_choice'] = 'auto'

                    response = client.chat.completions.create(**kwargs)
                    choice = response.choices[0]

                    if choice.message.tool_calls:
                        messages.append(choice.message)

                        for tc in choice.message.tool_calls:
                            tool_name = tc.function.name
                            try:
                                tool_args = json.loads(tc.function.arguments)
                            except json.JSONDecodeError:
                                tool_args = {}

                            tc_data = {
                                'type': 'tool_call',
                                'name': tool_name,
                                'args': tool_args,
                            }
                            yield f'data: {json.dumps(tc_data, ensure_ascii=False)}\n\n'

                            result = execute_tool(tool_name, tool_args)
                            tool_calls_log.append(
                                {
                                    'name': tool_name,
                                    'args': tool_args,
                                    'result': result,
                                }
                            )

                            tr_data = {
                                'type': 'tool_result',
                                'name': tool_name,
                                'result': result,
                            }
                            yield (f'data: {json.dumps(tr_data, ensure_ascii=False, default=str)}\n\n')

                            messages.append(
                                {
                                    'role': 'tool',
                                    'tool_call_id': tc.id,
                                    'content': json.dumps(result, ensure_ascii=False, default=str),
                                }
                            )
                    else:
                        content = choice.message.content or ''
                        full_response += content
                        yield f'data: {json.dumps({"type": "text", "content": content}, ensure_ascii=False)}\n\n'
                        break

                done_event = {'type': 'done', 'tool_calls': tool_calls_log}
                yield f'data: {json.dumps(done_event, ensure_ascii=False, default=str)}\n\n'

            except Exception as e:
                logger.error(f'MCP stream error: {e}', exc_info=True)
                yield f'data: {json.dumps({"type": "error", "error": str(e)})}\n\n'

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


@mcp_bp.route('/tools', methods=['GET'])
def mcp_tools():
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
