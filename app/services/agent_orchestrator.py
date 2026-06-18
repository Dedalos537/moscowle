import json
import logging
import os

from groq import BadRequestError, Groq

from app.services.tools_registry import execute_tool, get_tools_for_mode

logger = logging.getLogger('app')

MODEL_MAP = {
    'chiquito': 'llama-3.1-8b-instant',
    'grande': 'llama-3.3-70b-versatile',
}

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
        'REGLAS:\n'
        '1. Antes de responder, llama SIEMPRE UNA herramienta.\n'
        '2. Para pagos con voucher: extrae monto (solo el numero, sin S/). '
        'Si falta paciente o ID, busca con search_patients primero.\n'
        '3. Para crear usuarios: pregunta nombre y rol.\n'
        '4. Confirma antes de mutaciones destructivas.\n'
        '5. Se conciso. Usa español.'
    ),
}

MAX_TOOL_RETRIES = 2
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
    model = MODEL_MAP.get(mode, MODEL_MAP['chiquito'])
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['chiquito'])
    tools = get_tools_for_mode(mode)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': message},
    ]

    tool_retry_count = 0

    for _ in range(MAX_ITERATIONS):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice='auto' if tools else None,
                parallel_tool_calls=False,
                temperature=0.3,
                max_tokens=2048,
            )
        except BadRequestError as e:
            error_str = str(e)
            logger.error(f'Groq BadRequestError: {error_str[:500]}')
            if 'Failed to call a function' in error_str or 'tool call validation' in error_str:
                messages.append(
                    {
                        'role': 'user',
                        'content': (
                            'La herramienta que intentaste usar rechazo los parametros. '
                            'NO vuelvas a intentar con los mismos datos. '
                            'PREGUNTALE al usuario QUE LE FALTA. '
                            'Por ejemplo: "Necesito el monto exacto" o "A nombre de quien?". '
                            'Luego cuando tengas los datos correctos, llama la herramienta de nuevo.'
                        ),
                    }
                )
                continue
            return build_result(f'Error del asistente: {error_str[:120]}')
        except Exception as e:
            logger.error(f'Groq API error: {e}', exc_info=True)
            return build_result(f'Error al contactar al asistente: {str(e)[:100]}')

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            if tool_retry_count < MAX_TOOL_RETRIES and mode == 'grande':
                tool_retry_count += 1
                logger.info(f'No tool calls (retry {tool_retry_count})')
                messages.append(
                    {
                        'role': 'user',
                        'content': (
                            'Usa UNA herramienta si tienes los datos necesarios. '
                            'Si te falta informacion, PREGUNTALE al usuario.'
                        ),
                    }
                )
                continue

            return build_result(
                response=msg.content or 'No se que responder.',
                intent='general_chat',
            )

        for tool_call in msg.tool_calls:
            try:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                logger.info(f'Tool call: {func_name}({json.dumps(func_args, ensure_ascii=False)[:300]})')

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

    return build_result(
        'La operacion requiere muchos pasos. Por favor, intenta con una instruccion mas directa.',
        intent='general_chat',
    )
