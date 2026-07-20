import json
import logging

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.auth_compat import current_user
from app.models import User
from app.services.mcp_service import MCPService

logger = logging.getLogger('app.mcp')

mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp')

mcp_service = MCPService()


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
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    mode = data.get('mode', 'grande')
    history = data.get('history', [])

    if not message:
        return jsonify({'error': 'Mensaje requerido'}), 400

    try:
        result = mcp_service.process_message(
            message=message,
            user_role=user.role,
            user_id=user.id,
            mode=mode,
            history=history,
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f'MCP chat error: {e}', exc_info=True)
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500


@mcp_bp.route('/chat/stream', methods=['POST'])
def mcp_chat_stream():
    """Send a message and stream the response via SSE."""
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    mode = data.get('mode', 'grande')
    history = data.get('history', [])

    if not message:
        return jsonify({'error': 'Mensaje requerido'}), 400

    def generate():
        try:
            from groq import Groq

            from app.services.mcp_service import SYSTEM_PROMPTS
            from app.services.tools_registry import execute_tool, get_tools_for_mode

            api_key = current_app.config.get('GROQ_API_KEY')
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

            for iteration in range(5):
                kwargs = {
                    'model': 'llama-3.3-70b-versatile',
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

                        yield f'data: {json.dumps({"type": "tool_call", "name": tool_name, "args": tool_args}, ensure_ascii=False)}\n\n'  # noqa: E501

                        result = execute_tool(tool_name, tool_args)
                        tool_calls_log.append({'name': tool_name, 'args': tool_args, 'result': result})

                        yield f'data: {json.dumps({"type": "tool_result", "name": tool_name, "result": result}, ensure_ascii=False, default=str)}\n\n'  # noqa: E501

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

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@mcp_bp.route('/tools', methods=['GET'])
def mcp_tools():
    """List available tools for the current user's role."""
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'No autenticado'}), 401

    mode = request.args.get('mode', 'grande')
    tools = mcp_service.get_available_tools(user.role, mode)
    return jsonify({'tools': tools, 'count': len(tools), 'role': user.role, 'mode': mode})


@mcp_bp.route('/chat/clear', methods=['POST'])
def mcp_clear():
    """Clear chat history (frontend-side, just acknowledge)."""
    return jsonify({'success': True, 'message': 'Historial limpiado'})
