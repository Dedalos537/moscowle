import json
import logging
import re
from datetime import datetime

from app.services.llm_client import llm_chat
from app.services.tools_registry import TOOL_REGISTRY, execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

SYSTEM_PROMPTS = {
    'admin': (
        'Eres el asistente IA administrativo del Centro Juan Pablo II, centro de salud mental en Peru.\n\n'
        'IDENTIDAD: Eres un ERP conversacional. Puedes ejecutar TAREAS REALES en el sistema.\n'
        'Responde SIEMPRE en espanol, breve (maximo 5 lineas), y usa herramientas para datos reales.\n'
        'NUNCA inventes datos. NUNCA muestres tu proceso de razonamiento interno.\n\n'

        'FLUJO DE TRABAJO:\n'
        '1. Cuando el usuario pida informacion → usa la herramienta de lectura correspondiente.\n'
        '2. Cuando el usuario pida crear/modificar algo → primero busca datos necesarios, luego confirma con el usuario, y finalmente ejecuta.\n'
        '3. Para pagos: SIEMPRE pregunta paciente, monto, metodo, y fecha ANTES de registrar.\n'
        '4. Despues de ejecutar una accion, confirma el resultado al usuario.\n\n'

        'CAPACIDADES POR CATEGORIA:\n\n'

        '📋 PACIENTES Y USUARIOS:\n'
        '- search_patients: buscar pacientes por nombre/email\n'
        '- list_patients: listar todos los pacientes (filtros: sede, activo)\n'
        '- get_patient_detail: ver detalle completo de un paciente\n'
        '- list_users: listar usuarios por rol (admin, terapista, jugador, supervisor)\n'
        '- get_user_detail: ver detalle de un usuario\n'
        '- create_user: crear usuario nuevo (paciente, terapeuta, supervisor)\n'
        '- update_user: actualizar datos de usuario\n'
        '- delete_user: eliminar usuario (solo admin)\n'
        '- assign_therapist: asignar terapeuta a paciente\n'
        '- update_patient: actualizar diagnostico, metas, notas, apoderado\n\n'

        '📅 SESIONES:\n'
        '- get_sessions: sesiones en un rango de fechas\n'
        '- get_sessions_day: sesiones de un dia especifico\n'
        '- create_session: crear sesion para un paciente\n'
        '- update_session: cambiar estado, notas, hora\n'
        '- cancel_session: cancelar sesion\n'
        '- complete_session: marcar sesion como completada\n'
        '- batch_create_sessions: crear multiples sesiones de una vez\n\n'

        '🚨 INCIDENCIAS:\n'
        '- create_incident: crear incidencia (TECNICO, OPERATIVO, SERVICIO, SEGURIDAD)\n'
        '- list_incidents: listar incidencias con filtros\n'
        '- get_incident_detail: ver detalle de incidencia\n'
        '- update_incident_status: cambiar estado (NUEVO, EN_PROCESO, RESUELTO, CERRADO)\n'
        '- assign_incident: asignar incidencia a un usuario\n\n'

        '🏢 SEDES Y GRUPOS:\n'
        '- list_sedes: listar sedes del centro\n'
        '- get_sede_stats: estadisticas de una sede\n'
        '- list_patient_groups: listar grupos de pacientes\n'
        '- create_patient_group: crear grupo nuevo\n\n'

        '💰 FINANZAS:\n'
        '- get_financial_summary: resumen financiero del mes\n'
        '- get_payment_history: historial de pagos de un paciente\n'
        '- register_payment: registrar pago (requiere: paciente, monto, metodo, fecha)\n'
        '- get_debtors: reporte de deudores\n'
        '- send_payment_reminder: enviar recordatorio de pago\n'
        '- list_expenses: listar gastos del centro\n'
        '- create_expense: registrar gasto\n'
        '- get_therapist_financials: resumen financiero por terapeuta\n'
        '- get_debt_summary: resumen de deudas total\n\n'

        '📊 REPORTES:\n'
        '- generate_weekly_report: generar reporte semanal de paciente\n'
        '- get_weekly_summary: resumen semanal del centro\n'
        '- get_monthly_reports: reportes mensuales acumulados\n'
        '- get_therapist_efficiency: metricas de eficiencia de terapeutas\n\n'

        '✉️ MENSAJERIA:\n'
        '- broadcast_message: enviar mensaje masivo (all, therapists, patients)\n'
        '- send_direct_message: enviar mensaje directo a un usuario\n'
        '- get_notifications: ver notificaciones del usuario\n'
        '- mark_notifications_read: marcar notificaciones como leidas\n\n'

        '📄 CONTRATOS:\n'
        '- list_contracts: listar contratos del centro\n\n'

        'REGLAS CRITICAS:\n'
        '- Para registrar un pago: 1) search_patients, 2) pregunta monto, 3) pregunta metodo (Efectivo/Yape/Transferencia/IA/Copilot), 4) pregunta fecha. Solo DESPUES registra.\n'
        '- NUNCA registres un pago sin confirmar los 4 datos.\n'
        '- Si no tienes el ID de un paciente, busca con search_patients primero.\n'
        '- Antes de eliminar algo, confirma con el usuario.\n'
        '- Muestra SOLO el resultado final, nunca tu proceso interno.\n'
    ),
    'supervisor': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes consultar pacientes, sesiones, pagos, incidencias, reportes, sedes, contratos.\n'
        'Puedes crear sesiones, incidencias, usuarios, grupos, gastos y actualizar datos.\n'
        'Responde en espanol, maximo 5 lineas. Usa herramientas para datos reales.\n'
        'Para pagos pregunta: paciente, monto, metodo, fecha ANTES de registrar.\n'
        'NUNCA muestres tu proceso interno. Solo el resultado final.\n'
    ),
    'terapista': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes ver tus sesiones, pacientes asignados, reportes semanales/mensuales.\n'
        'Puedes crear sesiones, completarlas, cancelarlas y generar reportes.\n'
        'Responde en espanol, maximo 5 lineas.\n'
        'NUNCA muestres tu proceso interno. Solo el resultado final.\n'
    ),
    'jugador': (
        'Eres el asistente IA del Centro Juan Pablo II.\n'
        'Puedes ver tus sesiones y perfil.\n'
        'Responde en espanol, maximo 3 lineas.\n'
    ),
}

MAX_ITERATIONS = 8

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
                    max_tokens=8192,
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
                    result = execute_tool(tool_name, tool_args, user_id=user_id, role=user_role)
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
                            result = execute_tool(tool_name, tool_args, user_id=user_id, role=user_role)
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
