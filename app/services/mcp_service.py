import json
import logging
from datetime import datetime

from flask import current_app
from groq import Groq

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
        '- Responde en español, se conciso.\n'
        '- SIEMPRE usa herramientas para obtener datos reales. Nunca inventes.\n'
        '- Si el usuario pide algo que requiere datos, usa la herramienta apropiada primero.\n'
        '- Para registrar un pago, primero busca el paciente con search_patients si no tienes el ID.\n'
        '- Confirma al usuario cuando ejecutes una accion (crear, registrar, actualizar).\n'
        '- Si falta informacion para una accion, pide solo lo estrictamente necesario.\n'
    ),
    'supervisor': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes consultar pacientes, sesiones, pagos, incidencias y reportes.\n'
        'Puedes crear sesiones, incidencias y actualizar datos de pacientes.\n'
        'Responde en español, se conciso. Usa herramientas para datos reales.\n'
    ),
    'terapista': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes ver tus sesiones, pacientes asignados, reportes semanales/mensuales.\n'
        'Puedes crear sesiones y actualizar su estado.\n'
        'Responde en español, se amigable.\n'
    ),
    'jugador': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes ver tus sesiones y perfil.\n'
        'Responde en español, se amigable.\n'
    ),
}

MAX_ITERATIONS = 5
MODELS = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']


class MCPService:
    """Servicio MCP que conecta Groq API con tools_registry."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            api_key = current_app.config.get('GROQ_API_KEY')
            if not api_key:
                raise ValueError('GROQ_API_KEY no configurada')
            self._client = Groq(api_key=api_key)
        return self._client

    def _call_llm(self, client, messages, tools, model=None):
        """Call Groq API with error handling."""
        if model is None:
            model = MODELS[0]
        kwargs = {
            'model': model,
            'messages': messages,
            'max_tokens': 4096,
            'temperature': 0.3,
        }
        if tools:
            kwargs['tools'] = tools
            kwargs['tool_choice'] = 'auto'
        return client.chat.completions.create(**kwargs)

    def process_message(self, message, user_role, user_id, mode='grande', history=None):
        system_prompt = SYSTEM_PROMPTS.get(user_role, SYSTEM_PROMPTS['jugador'])
        tools = get_tools_for_mode(mode, user_role)
        messages = [{'role': 'system', 'content': system_prompt}]

        if history:
            for h in history[-20:]:
                messages.append({'role': h['role'], 'content': h['content']})

        messages.append({'role': 'user', 'content': message})

        tool_calls_log = []
        client = self._get_client()

        for iteration in range(MAX_ITERATIONS):
            try:
                response = self._call_llm(client, messages, tools)
                choice = response.choices[0]

                if choice.finish_reason == 'stop' or not choice.message.tool_calls:
                    return {
                        'response': choice.message.content or '',
                        'tool_calls': tool_calls_log,
                        'done': True,
                    }

                messages.append(choice.message)

                for tc in choice.message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info(f'MCP tool call: {tool_name}({tool_args})')
                    result = execute_tool(tool_name, tool_args)
                    tool_calls_log.append({
                        'name': tool_name,
                        'args': tool_args,
                        'result': result,
                        'timestamp': datetime.utcnow().isoformat(),
                    })

                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tc.id,
                        'content': json.dumps(result, ensure_ascii=False, default=str),
                    })

            except Exception as e:
                logger.error(f'MCP iteration {iteration} error: {e}', exc_info=True)
                if iteration >= 2:
                    return {
                        'response': f'Error procesando tu solicitud: {str(e)}',
                        'tool_calls': tool_calls_log,
                        'done': True,
                        'error': str(e),
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
