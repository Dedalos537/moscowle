import json
import logging
import os

from groq import Groq

from app.services.tools_registry import execute_tool, get_tools_for_mode

logger = logging.getLogger('app')

SYSTEM_PROMPTS = {
    'chiquito': (
        'Eres un asistente de consulta del Centro de Terapias Juan Pablo II.\n'
        'SOLO PUEDES LEER DATOS — NUNCA crear, modificar o eliminar.\n\n'
        'Reglas:\n'
        '- Responde en Markdown limpio\n'
        '- Si tienes dudas sobre datos, usa search_patients, list_users\n'
        '- Si el usuario pide registrar un pago, crear usuario, o cualquier mutacion:\n'
        '  → Responde: "Para procesar eso, cambia al **Modo Administrador** (⛶ pantalla completa)"\n'
        '- Se conciso y directo. Usa español.\n'
        '- Si no sabes algo, di que no sabes.'
    ),
    'grande': (
        'Eres un agente administrador con control total del Centro de Terapias Juan Pablo II.\n'
        'Tienes acceso a TODAS las herramientas del sistema.\n\n'
        'Directrices ReAct:\n'
        '1. Cuando necesites datos → llama a la tool correspondiente\n'
        '2. Para pagos con voucher: analiza → extrae monto → '
        'si falta paciente, pregunta → solo cuando tengas todo el payload, ejecuta register_payment\n'
        '3. Para crear usuarios: pregunta por nombre y rol explicitamente\n'
        '4. Siempre confirma con el usuario antes de ejecutar mutaciones destructivas (delete, desactivar)\n'
        '5. Se conciso y directo. Usa español.'
    ),
}

MAX_ITERATIONS = 5


def build_result(response, intent='general_chat', action_chips=None, suggestions=None):
    return {
        'response': response,
        'intent': intent,
        'action_chips': action_chips or [],
        'suggestions': suggestions or [],
    }


def process_agent_message(uid, message, mode='chiquito'):
    """Main ReAct loop. Sends to Groq with tools, handles tool calls, returns final response."""
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        return build_result('Error: GROQ_API_KEY no configurada. Los modulos de IA no estan disponibles.')

    client = Groq(api_key=groq_api_key)
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['chiquito'])
    tools = get_tools_for_mode(mode)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': message},
    ]

    for _ in range(MAX_ITERATIONS):
        try:
            response = client.chat.completions.create(
                model='llama-3.1-8b-instant',
                messages=messages,
                tools=tools if tools else None,
                tool_choice='auto' if tools else None,
                temperature=0.3,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error(f'Groq API error: {e}', exc_info=True)
            return build_result(f'Error al contactar al asistente: {str(e)[:100]}')

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            return build_result(
                response=msg.content or 'No se que responder.',
                intent='general_chat',
            )

        # Process tool calls
        for tool_call in msg.tool_calls:
            try:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                logger.info(f'Tool call: {func_name}({func_args})')

                result = execute_tool(func_name, func_args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)

                messages.append(
                    {
                        'role': 'tool',
                        'tool_call_id': tool_call.id,
                        'content': result_str,
                    }
                )
            except Exception as e:
                logger.error(f'Error executing tool {tool_call.function.name}: {e}', exc_info=True)
                messages.append(
                    {
                        'role': 'tool',
                        'tool_call_id': tool_call.id,
                        'content': json.dumps({'error': str(e)}),
                    }
                )

    # Max iterations reached — return last assistant content or fallback
    return build_result(
        'La operacion requiere muchos pasos. Por favor, intenta con una instruccion mas directa.',
        intent='general_chat',
    )
