import json
import logging
import re
from datetime import datetime

from app.services.llm_client import llm_chat
from app.services.tools_registry import TOOL_REGISTRY, execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

SYSTEM_PROMPTS = {
    'admin': (
        'Eres el asistente IA del Centro Juan Pablo II, centro de salud mental.\n\n'
        'CAPACIDADES:\n'
        '- Buscar y ver info de pacientes (search_patients, get_patient_detail)\n'
        '- Listar usuarios por rol (list_users)\n'
        '- Ver sesiones del calendario (get_sessions)\n'
        '- Crear y actualizar sesiones (create_session, update_session)\n'
        '- Ver historial de pagos y resumen financiero (get_payment_history, get_financial_summary)\n'
        '- Registrar pagos (register_payment)\n'
        '- Crear incidencias (create_incident)\n'
        '- Actualizar datos de pacientes (update_patient)\n'
        '- Enviar mensajes/notificaciones (broadcast_message)\n\n'
        'REGLAS:\n'
        '- Responde en espanol, maximo 3 lineas.\n'
        '- SIEMPRE usa herramientas para obtener datos reales. Nunca inventes.\n'
        '- Si el usuario pide algo que requiere datos, usa la herramienta apropiada primero.\n'
        '- Para registrar un pago, primero busca el paciente con search_patients si no tienes el ID.\n'
        '- Confirma al usuario cuando ejecutes una accion (crear, registrar, actualizar).\n'
        '- NO incluyas tu proceso de razonamiento ni pasos intermedios como "Voy a..." o "Primero necesito...".\n'
        '- Solo muestra el resultado final.\n'
    ),
    'supervisor': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes consultar pacientes, sesiones, pagos, incidencias y reportes.\n'
        'Puedes crear sesiones, incidencias y actualizar datos de pacientes.\n'
        'Responde en espanol, maximo 3 lineas. Usa herramientas para datos reales.\n'
        '- NO incluyas tu proceso de razonamiento ni pasos intermedios.\n'
        '- Solo muestra el resultado final.\n'
    ),
    'terapista': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes ver tus sesiones, pacientes asignados, reportes semanales/mensuales.\n'
        'Puedes crear sesiones y actualizar su estado.\n'
        'Responde en espanol, maximo 3 lineas.\n'
        '- NO incluyas tu proceso de razonamiento ni pasos intermedios.\n'
        '- Solo muestra el resultado final.\n'
    ),
    'jugador': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes ver tus sesiones y perfil.\n'
        'Responde en espanol, maximo 3 lineas.\n'
    ),
}

MAX_ITERATIONS = 5

TOOL_CALL_PATTERN = re.compile(
    r'<function=(\w+)\s*(\{.*?\})?\s*</function>',
    re.DOTALL,
)


def _parse_text_tool_call(text):
    """Extract tool name and args from text like <function=search_patients{"query":"Carlos"}</function>."""
    match = TOOL_CALL_PATTERN.search(text)
    if not match:
        return None, None
    tool_name = match.group(1)
    args_str = match.group(2)
    if args_str:
        try:
            tool_args = json.loads(args_str)
        except json.JSONDecodeError:
            tool_args = {}
    else:
        tool_args = {}
    return tool_name, tool_args


def _build_tool_prompt(tools):
    """Build a text listing of available tools for the system prompt."""
    lines = ['HERRAMIENTAS DISPONIBLES (usa el formato <function=nombre{json_args} </function>):']
    for t in tools:
        fn = t['function']
        params = fn.get('parameters', {}).get('properties', {})
        required = fn.get('parameters', {}).get('required', [])
        param_parts = []
        for pname, pinfo in params.items():
            req = '*' if pname in required else ''
            param_parts.append(f'{pname}{req}:{pinfo.get("type", "string")}')
        params_str = ', '.join(param_parts) if param_parts else 'ninguno'
        lines.append(f'- {fn["name"]}: {fn["description"]} | Params: {params_str}')
    return '\n'.join(lines)


class MCPService:
    """Servicio MCP con GLM-5.2 como LLM principal y fallback multi-provider."""

    def process_message(self, message, user_role, user_id, mode='grande', history=None):
        system_prompt = SYSTEM_PROMPTS.get(user_role, SYSTEM_PROMPTS['jugador'])
        tools = get_tools_for_mode(mode, user_role)
        tool_prompt = _build_tool_prompt(tools)

        full_system = system_prompt + '\n\n' + tool_prompt
        messages = [{'role': 'system', 'content': full_system}]

        if history:
            for h in history[-20:]:
                messages.append({'role': h['role'], 'content': h['content']})

        messages.append({'role': 'user', 'content': message})

        tool_calls_log = []

        for iteration in range(MAX_ITERATIONS):
            try:
                content, provider = llm_chat(
                    messages,
                    temperature=0.3,
                    max_tokens=4096,
                )

                if not content.strip():
                    return {
                        'response': 'No pude generar una respuesta.',
                        'tool_calls': tool_calls_log,
                        'done': True,
                        'provider': provider,
                    }

                logger.info(f'MCP LLM response via {provider} (iteration {iteration})')

                tool_name, tool_args = _parse_text_tool_call(content)

                if tool_name:
                    logger.info(f'MCP parsed tool call: {tool_name}({tool_args})')
                    result = execute_tool(tool_name, tool_args)
                    tool_calls_log.append(
                        {
                            'name': tool_name,
                            'args': tool_args,
                            'result': result,
                            'timestamp': datetime.utcnow().isoformat(),
                        }
                    )

                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                    messages.append({'role': 'assistant', 'content': content})
                    messages.append(
                        {
                            'role': 'user',
                            'content': f'[Tool result for {tool_name}]: {result_str}\n\nAhora responde al usuario con esta informacion.',
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

                # Try to recover tool calls from failed_generation error (Groq-specific)
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
                            result = execute_tool(tool_name, tool_args)
                            tool_calls_log.append(
                                {
                                    'name': tool_name,
                                    'args': tool_args,
                                    'result': result,
                                    'timestamp': datetime.utcnow().isoformat(),
                                }
                            )

                            result_str = json.dumps(result, ensure_ascii=False, default=str)
                            messages.append({'role': 'assistant', 'content': failed_gen})
                            messages.append(
                                {
                                    'role': 'user',
                                    'content': f'[Tool result for {tool_name}]: {result_str}\n\nAhora responde al usuario con esta informacion.',
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
