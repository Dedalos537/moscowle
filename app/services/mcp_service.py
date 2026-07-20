import json
import logging
from datetime import datetime

from flask import current_app
from groq import Groq

from app.services.tools_registry import TOOL_REGISTRY, execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

SYSTEM_PROMPTS = {
    'admin': (
        'Eres el asistente de IA del Centro Juan Pablo II, una plataforma de salud mental. '
        'Tienes acceso COMPLETO al sistema: puedes crear, editar, eliminar, consultar y administrar '
        'todo: usuarios, pacientes, sesiones, pagos, incidencias, reportes, juegos, contratos, notificaciones. '
        'Siempre responde en español. Sé preciso y conciso. '
        'Cuando ejecutes una herramienta, confirma al usuario qué hiciste. '
        'Si necesitas información adicional para ejecutar una acción, pídela. '
        'Nunca inventes datos. Usa las herramientas para obtener información real del sistema.'
    ),
    'supervisor': (
        'Eres el asistente de IA del Centro Juan Pablo II. Puedes consultar y gestionar pacientes, '
        'sesiones, incidencias, reportes y notificaciones. '
        'Puedes crear y editar, pero no eliminar usuarios. '
        'Responde en español. Sé preciso y conciso.'
    ),
    'terapista': (
        'Eres el asistente de IA del Centro Juan Pablo II. Puedes consultar y gestionar '
        'tus pacientes asignados, tus sesiones, reportes semanales/mensuales, y notificaciones. '
        'Puedes crear sesiones y completarlas. '
        'Responde en español. Sé preciso y conciso.'
    ),
    'jugador': (
        'Eres el asistente de IA del Centro Juan Pablo II. Puedes consultar tus propias '
        'sesiones, notificaciones y perfil. '
        'Responde en español. Sé amigable y conciso.'
    ),
}

MAX_ITERATIONS = 5


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

    def process_message(self, message, user_role, user_id, mode='grande', history=None):
        """
        Procesa un mensaje del usuario con ReAct loop.
        Retorna dict con 'response', 'tool_calls', 'done'.
        """
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
                    tool_calls_log.append(
                        {
                            'name': tool_name,
                            'args': tool_args,
                            'result': result,
                            'timestamp': datetime.utcnow().isoformat(),
                        }
                    )

                    messages.append(
                        {
                            'role': 'tool',
                            'tool_call_id': tc.id,
                            'content': json.dumps(result, ensure_ascii=False, default=str),
                        }
                    )

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
            'response': 'No pude completar la operación después de varios intentos. Intenta ser más específico.',
            'tool_calls': tool_calls_log,
            'done': True,
        }

    def get_available_tools(self, user_role, mode='grande'):
        """Retorna lista de herramientas disponibles para un rol."""
        tools = get_tools_for_mode(mode, user_role)
        return [
            {
                'name': t['function']['name'],
                'description': t['function']['description'],
                'category': TOOL_REGISTRY[t['function']['name']]['category'],
            }
            for t in tools
        ]
