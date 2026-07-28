import json
import logging
import re
from datetime import datetime

from app.services.llm_client import llm_chat
from app.services.tools_registry import TOOL_REGISTRY, execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

MAX_TOOL_RESULT_CHARS = 1500

SYSTEM_PROMPTS = {
    'admin': (
        'You are the AI assistant for Centro Juan Pablo II, a mental health center in Peru.\n'
        'You are an ERP chatbot that executes REAL actions in the system.\n\n'

        'RULES:\n'
        '- ALWAYS respond in Spanish.\n'
        '- Be concise: max 3-5 lines per response.\n'
        '- NEVER invent data. ONLY use the EXACT values returned by tools.\n'
        '- NEVER modify, estimate, or "fill in" values from tool results. Report EXACTLY what the tool returned.\n'
        '- If a tool result is truncated, say "el resultado fue truncado" and show what you received.\n'
        '- NEVER show your reasoning process. Only show the final result.\n'
        '- When listing items (patients, users, etc.), show a SHORT summary (count + first 5 names + "... and N more").\n'
        '- For payments: ALWAYS ask patient, amount, method, date BEFORE registering.\n'
        '- Before deleting, confirm with the user.\n\n'

        'TOOL FORMAT (CRITICAL - you MUST include the JSON args):\n'
        'Correct: <function=search_patients{"query": "Carlos"}</function>\n'
        'WRONG: <function=search_patients</function>  ← THIS WILL FAIL\n\n'

        'TOOLS BY CATEGORY:\n\n'

        'PATIENTS/USERS: search_patients, list_patients, get_patient_detail, list_users, get_user_detail, create_user, update_user, delete_user, assign_therapist, update_patient\n'
        'SESSIONS: get_sessions, get_sessions_day, create_session, update_session, cancel_session, complete_session, batch_create_sessions\n'
        'INCIDENTS: create_incident, list_incidents, get_incident_detail, update_incident_status, assign_incident\n'
        'BRANCHES: list_sedes, get_sede_stats, list_patient_groups, create_patient_group\n'
        'FINANCE: get_financial_summary (use month/year params for past months), get_payment_history, register_payment, get_debtors, send_payment_reminder, list_expenses, create_expense, get_therapist_financials, get_debt_summary, compare_periods (compare 2 months)\n'
        'REPORTS: generate_weekly_report, get_weekly_summary, get_monthly_reports, get_therapist_efficiency, get_user_growth (user registration metrics by month)\n'
        'MESSAGING: broadcast_message, send_direct_message, get_notifications, mark_notifications_read\n'
        'CONTRACTS: list_contracts\n\n'

        'PAYMENT WORKFLOW:\n'
        '1. search_patients to find the patient ID\n'
        '2. Ask: amount, method (Efectivo/Yape/Transferencia/IA/Copilot), date\n'
        '3. Only THEN call register_payment with ALL 4 params\n'
        '4. Confirm the result\n\n'

        'FINANCIAL QUERIES:\n'
        '- get_financial_summary with month=5, year=2026 for May 2026\n'
        '- ALWAYS include year parameter (current year is 2026)\n'
        '- compare_periods to compare any two months side by side\n'
        '- get_user_growth for registration trends\n\n'

        'MESSAGING WORKFLOW:\n'
        '1. search_patients or list_users to find the user ID\n'
        '2. send_direct_message with receiver_id AND content (BOTH required)\n'
    ),
    'supervisor': (
        'You are the AI assistant for Centro Juan Pablo II.\n'
        'You can query patients, sessions, payments, incidents, reports, branches, contracts.\n'
        'You can create sessions, incidents, users, groups, expenses and update data.\n'
        'Respond in Spanish, max 5 lines. Use tools for real data.\n'
        'For payments ask: patient, amount, method, date BEFORE registering.\n'
        'NEVER show your internal process. Only the final result.\n'
        'TOOL FORMAT: <function=name{"param": "value"}</function>  ← ALWAYS include JSON args\n'
    ),
    'terapista': (
        'You are the AI assistant for Centro Juan Pablo II.\n'
        'You can view your sessions, assigned patients, weekly/monthly reports.\n'
        'You can create sessions, complete them, cancel them and generate reports.\n'
        'Respond in Spanish, max 5 lines.\n'
        'NEVER show your internal process. Only the final result.\n'
        'TOOL FORMAT: <function=name{"param": "value"}</function>  ← ALWAYS include JSON args\n'
    ),
    'jugador': (
        'You are the AI assistant for Centro Juan Pablo II.\n'
        'You can view your sessions and profile.\n'
        'Respond in Spanish, max 3 lines.\n'
    ),
}

MAX_ITERATIONS = 6

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


def _trim_tool_result(result, max_chars=MAX_TOOL_RESULT_CHARS):
    """Trim tool result to avoid blowing up the context window."""
    if isinstance(result, dict):
        # For list results, keep count + first few items
        if 'patients' in result and isinstance(result['patients'], list):
            patients = result['patients']
            result = {
                'success': result.get('success', True),
                'count': result.get('count', len(patients)),
                'patients_preview': patients[:5],
                'note': f'Showing 5 of {len(patients)} patients' if len(patients) > 5 else None,
            }
        elif 'users' in result and isinstance(result['users'], list):
            users = result['users']
            result = {
                'success': result.get('success', True),
                'count': result.get('count', len(users)),
                'users_preview': users[:5],
                'note': f'Showing 5 of {len(users)} users' if len(users) > 5 else None,
            }
        elif 'payments' in result and isinstance(result['payments'], list):
            payments = result['payments']
            result = {
                'success': result.get('success', True),
                'patient': result.get('patient'),
                'total_payments': len(payments),
                'payments': payments[:10],
                'note': f'Showing {min(10, len(payments))} of {len(payments)} payments' if len(payments) > 10 else None,
            }
        elif 'sessions' in result and isinstance(result['sessions'], list):
            sessions = result['sessions']
            result = {
                'success': result.get('success', True),
                'count': result.get('count', len(sessions)),
                'sessions': sessions[:5],
                'note': f'Showing {min(5, len(sessions))} of {len(sessions)} sessions' if len(sessions) > 5 else None,
            }

    result_str = json.dumps(result, ensure_ascii=False, default=str)
    if len(result_str) > max_chars:
        result_str = result_str[:max_chars] + '... [truncated]'
    return result_str


def _build_tool_prompt(tools):
    """Build a compact text listing of available tools."""
    lines = [
        'AVAILABLE TOOLS (use format: <function=name{"param": "value"}</function>):',
        'IMPORTANT: ALWAYS include JSON args in {}. Without {} it FAILS.',
        '',
    ]
    for t in tools:
        fn = t['function']
        params = fn.get('parameters', {}).get('properties', {})
        required = fn.get('parameters', {}).get('required', [])
        param_parts = []
        for pname, pinfo in params.items():
            req = '*' if pname in required else ''
            param_parts.append(f'{pname}{req}:{pinfo.get("type", "string")}')
        params_str = ', '.join(param_parts) if param_parts else 'none'
        lines.append(f'- {fn["name"]}: {fn["description"]} | Params: {params_str}')
    return '\n'.join(lines)


class MCPService:
    """MCP service with GLM-5.2 as primary LLM and multi-provider fallback."""

    def process_message(self, message, user_role, user_id, mode='grande', history=None):
        system_prompt = SYSTEM_PROMPTS.get(user_role, SYSTEM_PROMPTS['jugador'])
        tools = get_tools_for_mode(mode, user_role)
        tool_prompt = _build_tool_prompt(tools)

        full_system = system_prompt + '\n\n' + tool_prompt
        messages = [{'role': 'system', 'content': full_system}]

        if history:
            for h in history[-8:]:
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
                    result = execute_tool(tool_name, tool_args, user_id=user_id, role=user_role)
                    tool_calls_log.append(
                        {
                            'name': tool_name,
                            'args': tool_args,
                            'result': result,
                            'timestamp': datetime.utcnow().isoformat(),
                        }
                    )

                    result_str = _trim_tool_result(result)
                    # Strip any fabricated text before the tool call — only keep the tool invocation
                    tool_call_match = re.search(r'<function=.*?</function>', content, re.DOTALL)
                    clean_assistant = tool_call_match.group(0) if tool_call_match else content
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

                            result_str = _trim_tool_result(result)
                            tool_call_match = re.search(r'<function=.*?</function>', failed_gen, re.DOTALL)
                            clean_assistant = tool_call_match.group(0) if tool_call_match else failed_gen
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
