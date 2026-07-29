import json
import logging
import os
import re
import uuid
from datetime import datetime

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.auth_compat import current_user
from app.models import User
from app.services.llm_client import llm_chat_stream
from app.services.mcp_service import SYSTEM_PROMPTS, MCPService, _build_tool_prompt, _parse_text_tool_call, _trim_tool_result
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
        with _app.app_context():
            try:
                # Send thinking indicator
                yield f'data: {json.dumps({"type": "thinking", "content": "Procesando..."})}\n\n'

                tools = get_tools_for_mode(mode, user.role)
                tool_prompt = _build_tool_prompt(tools)
                system_prompt = SYSTEM_PROMPTS.get(user.role, SYSTEM_PROMPTS['jugador'])
                messages = [{'role': 'system', 'content': system_prompt + '\n\n' + tool_prompt}]

                if history:
                    for h in history[-8:]:
                        messages.append({'role': h['role'], 'content': h['content']})

                messages.append({'role': 'user', 'content': message})

                tool_calls_log = []

                for iteration in range(6):
                    try:
                        full_content = ''
                        for chunk in llm_chat_stream(messages, temperature=0.3, max_tokens=4096):
                            full_content += chunk
                            clean = re.sub(r'<function=\w+.*?</function>', '', chunk)
                            if clean.strip():
                                yield f'data: {json.dumps({"type": "chunk", "content": clean}, ensure_ascii=False)}\n\n'

                        if not full_content.strip():
                            yield f'data: {json.dumps({"type": "text", "content": "No pude generar una respuesta."})}\n\n'
                            break

                        tool_name, tool_args = _parse_text_tool_call(full_content)

                        if tool_name:
                            # Send tool_call event
                            tc_data = {'type': 'tool_call', 'name': tool_name, 'args': tool_args}
                            yield f'data: {json.dumps(tc_data, ensure_ascii=False)}\n\n'

                            result = execute_tool(tool_name, tool_args, user_id=user.id, role=user.role)
                            tool_calls_log.append({'name': tool_name, 'args': tool_args, 'result': result})

                            # Send trimmed tool_result
                            trimmed = _trim_tool_result(result)
                            success = not (isinstance(result, dict) and 'error' in result)
                            tr_data = {'type': 'tool_result', 'name': tool_name, 'result': trimmed, 'success': success}
                            yield f'data: {json.dumps(tr_data, ensure_ascii=False)}\n\n'

                            result_str = _trim_tool_result(result)
                            tool_call_match = re.search(r'<function=.*?</function>', full_content, re.DOTALL)
                            clean_assistant = tool_call_match.group(0) if tool_call_match else full_content
                            messages.append({'role': 'assistant', 'content': clean_assistant})
                            messages.append(
                                {
                                    'role': 'user',
                                    'content': (
                                        f'[REAL Tool {tool_name} result — use ONLY this data, do NOT invent anything]:\n'
                                        f'{result_str}\n\n'
                                        f'Respond to the user using ONLY the exact values above. If a field is missing, say "no disponible".'
                                    ),
                                }
                            )

                            # Send thinking indicator for next iteration
                            yield f'data: {json.dumps({"type": "thinking", "content": "Procesando resultado..."})}\n\n'
                            continue

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
                                    tc_data = {'type': 'tool_call', 'name': tn, 'args': ta}
                                    yield f'data: {json.dumps(tc_data, ensure_ascii=False)}\n\n'

                                    result = execute_tool(tn, ta, user_id=user.id, role=user.role)
                                    tool_calls_log.append({'name': tn, 'args': ta, 'result': result})

                                    trimmed = _trim_tool_result(result)
                                    success = not (isinstance(result, dict) and 'error' in result)
                                    tr_data = {'type': 'tool_result', 'name': tn, 'result': trimmed, 'success': success}
                                    yield f'data: {json.dumps(tr_data, ensure_ascii=False)}\n\n'

                                    result_str = _trim_tool_result(result)
                                    tool_call_match = re.search(r'<function=.*?</function>', failed_gen, re.DOTALL)
                                    clean_assistant = tool_call_match.group(0) if tool_call_match else failed_gen
                                    messages.append({'role': 'assistant', 'content': clean_assistant})
                                    messages.append(
                                        {
                                            'role': 'user',
                                            'content': (
                                                f'[REAL Tool {tn} result — use ONLY this data, do NOT invent anything]:\n'
                                                f'{result_str}\n\n'
                                                f'Respond to the user using ONLY the exact values above. If a field is missing, say "no disponible".'
                                            ),
                                        }
                                    )
                                    yield f'data: {json.dumps({"type": "thinking", "content": "Procesando resultado..."})}\n\n'
                                    continue

                        if iteration >= 2:
                            yield f'data: {json.dumps({"type": "text", "content": f"Error: {error_str[:200]}"})}\n\n'
                            break

                yield f'data: {json.dumps({"type": "done", "tool_calls": tool_calls_log}, ensure_ascii=False)}\n\n'

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


def _ocr_voucher(file_path, ext):
    """Use available LLM vision to extract payment data from voucher image."""
    try:
        import base64
        with open(file_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()

        mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}.get(ext, 'image/jpeg')
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
            '{"amount": number|null, "method": "Plin"|"Yape"|"Efectivo"|"Transferencia"|null, "date": "YYYY-MM-DD"|null, "patient_hint": "nombre completo"|null, "reference": "string"|null}\n\n'
            'EJEMPLO de respuesta correcta: {"amount": 200, "method": "Plin", "date": "2026-07-22", "patient_hint": "Diego Alejandro Centeno Barrutia", "reference": "2026077240"}'
        )

        # Try Gemini first
        try:
            from app.services.llm_client import get_gemini_model
            gemini = get_gemini_model()
            if gemini:
                import google.generativeai as genai
                response = gemini.generate_content([
                    prompt,
                    {'inline_data': {'mime_type': mime, 'data': img_b64}}
                ])
                text = response.text.strip()
                import json
                match = re.search(r'\{[^}]+\}', text)
                if match:
                    logger.info('OCR via Gemini exitoso')
                    return json.loads(match.group())
        except Exception as e:
            logger.warning(f'OCR Gemini failed: {e}')

        # Try Groq with llama vision
        try:
            import os, json
            api_key = os.environ.get('GROQ_API_KEY', '')
            if api_key:
                import requests as req
                resp = req.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={
                        'model': 'llama-3.2-11b-vision-preview',
                        'messages': [
                            {'role': 'user', 'content': [
                                {'type': 'text', 'text': prompt},
                                {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{img_b64}'}},
                            ]},
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
