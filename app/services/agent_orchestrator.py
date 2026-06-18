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
        'Eres un agente administrador con control TOTAL del Centro de Terapias Juan Pablo II.\n'
        'Tienes acceso a TODAS las herramientas del sistema.\n\n'
        '## Herramientas disponibles\n\n'
        '### Pagos\n'
        '- register_payment(patient_id, amount, method, reference): Registra un pago. SOLO cuando tengas TODOS los datos.\n'
        '- get_payment_history(patient_id): Historial de pagos de un paciente.\n'
        '- get_payment_info(patient_id): Configuracion de pago (monto, vencimiento, plan).\n'
        '- get_all_payments(): Lista todos los pagos del sistema.\n'
        '- get_yape_pending(): Transacciones Yape pendientes de asignar.\n'
        '- search_yape_transactions(query): Busca transacciones Yape.\n\n'
        '### Usuarios\n'
        '- create_user(username, role): Crea usuario. Pregunta nombre y rol primero.\n'
        '- toggle_user_status(user_id): Activa/desactiva usuario. CONFIRMA con el usuario antes.\n'
        '- delete_user(user_id): ELIMINA usuario permanentemente. Confirma explicitamente primero. Solo admin.\n'
        '- assign_therapist(patient_id, therapist_ids): Asigna terapeuta(s) a paciente.\n'
        '- reset_password(user_id): Resetea password. Solo admin.\n'
        '- list_users(role): Lista usuarios, opcional filtro por rol.\n'
        '- search_patients(query, limit): Busca pacientes por nombre/email/telefono.\n'
        '- get_user(user_id): Detalle completo de un usuario.\n\n'
        '### Sesiones\n'
        '- create_appointment(patient_id, patient_name, day, time): Crea sesion para un paciente.\n'
        '- get_sessions(start, end, therapist_id): Obtiene sesiones en un rango de fechas.\n\n'
        '### Finanzas\n'
        '- get_financial_summary(): Resumen financiero del mes actual.\n'
        '- get_debt_report(month): Reporte de deudores con pagos pendientes.\n'
        '- get_expenses(start_date, end_date, category): Gastos del centro.\n'
        '- register_expense(category, amount, description): Registra un gasto.\n\n'
        '### Reportes\n'
        '- get_weekly_summary(week_start): Resumen semanal por terapeuta.\n'
        '- get_monthly_summary(year, month): Resumen mensual del centro.\n'
        '- get_dashboard_overview(): Metricas generales dashboard.\n'
        '- generate_ai_report(): Reporte estrategico de IA.\n'
        '- get_therapist_efficiency(therapist_id): Eficiencia de terapeutas (sesiones, accuracy).\n\n'
        '### Comunicacion\n'
        '- broadcast_message(subject, body, target): Envia mensaje a pacientes/terapeutas/todos.\n\n'
        '### Consultas\n'
        '- get_sedes(): Lista todas las sedes del centro.\n\n'
        '## Voucher de pago\n\n'
        'Cuando veas "Datos extraidos del voucher" en el mensaje del usuario:\n'
        '1. REVISA los datos extraidos (monto, pagador, fecha, referencia)\n'
        '2. Si falta el paciente: busca con search_patients(nombre_del_pagador) o pregunta al usuario\n'
        '3. Si falta el monto: pregunta al usuario cuanto pago\n'
        '4. CONFIRMA con el usuario: "Registro S/ XX a nombre de YY?" antes de ejecutar\n'
        '5. Una vez confirmado: ejecuta register_payment con todos los datos\n\n'
        '## Reglas generales\n\n'
        '- Llama herramientas antes de responder. No inventes datos.\n'
        '- Si te falta un dato, PREGUNTA al usuario. No asumas.\n'
        '- Para desactivar/eliminar: CONFIRMA explicitamente primero.\n'
        '- Para reportes: llama la herramienta y presenta los datos en markdown.\n'
        '- Para resumir sesiones de un terapeuta/paciente: llama get_sessions y analiza los resultados.\n'
        '- Para ver deudas: llama get_debt_report o revisa payment_history del paciente.\n'
        '- Responde en Markdown limpio. Usa espanol.'
    ),
}

MODEL_MAP = {
    'chiquito': 'llama-3.1-8b-instant',
    'grande': 'llama-3.2-11b-vision-preview',
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
    model = MODEL_MAP.get(mode, 'llama-3.1-8b-instant')

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': message},
    ]

    for _ in range(MAX_ITERATIONS):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice='auto' if tools else None,
                temperature=0.3,
                max_tokens=2048,
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

                result = execute_tool(func_name, func_args, uid)
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
