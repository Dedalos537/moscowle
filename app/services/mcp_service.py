import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.llm_client import llm_chat
from app.services.tools_registry import SAFE_WRITE_TOOLS, TOOL_REGISTRY, execute_tool, get_tools_for_mode

logger = logging.getLogger('app.mcp')

MAX_TOOL_RESULT_CHARS = 1500

LIMA_TZ = ZoneInfo('America/Lima')

_DIAS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
_MESES_ES = [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
]


def get_current_date_context():
    """Fecha actual en America/Lima para que el LLM nunca adivine 'hoy'."""
    now = datetime.now(LIMA_TZ)
    fecha = f'{_DIAS_ES[now.weekday()]} {now.day} de {_MESES_ES[now.month - 1]} de {now.year}'
    return (
        f"Hoy es {fecha}. Usa SIEMPRE esta fecha como referencia para 'hoy'. "
        'Todos los usuarios están en la zona horaria America/Lima (UTC-5).'
    )


SYSTEM_PROMPTS = {
    'admin': (
        'You are the AI assistant for Centro Juan Pablo II, a mental health center in Peru.\n'
        'You are an ERP chatbot that executes REAL actions in the system.\n\n'
        'CRITICAL RULES:\n'
        '- ALWAYS respond in Spanish.\n'
        '- Be concise: max 3-5 lines per response.\n'
        '- NEVER invent, guess, or fabricate ANY data. ONLY use EXACT values from tool results.\n'
        '- NEVER generate HTML, JavaScript, CSS, or code. You are a chatbot, not a code generator.\n'
        '- NEVER output code blocks, <html>, <script>, <table>, or any markup.\n'
        '- If you don\'t have data from a tool, say "No tengo esos datos" and offer to search.\n'
        '- NEVER modify, estimate, or "fill in" values. Report EXACTLY what the tool returned.\n'
        '- If a tool result is truncated, say "el resultado fue truncado" and show what you received.\n'
        '- NEVER show your reasoning process. Only show the final result.\n'
        '- When listing items, show a SHORT summary (count + first 5 names).\n'
        '- For payments: ALWAYS ask patient, amount, method, date BEFORE registering.\n'
        '- Before deleting, confirm with the user.\n\n'
        'TOOL FORMAT (you MUST call tools to get real data):\n'
        'Option 1: <function=search_patients{"query": "Carlos"}</function>\n'
        'Option 2: search_patients(query: "Carlos")\n'
        'Both formats work. ALWAYS include the arguments.\n'
        'WRONG: search_patients  <- missing arguments, WILL FAIL\n\n'
        'EXAMPLE of a correct tool call:\n'
        'User: "Busca al paciente Carlos"\n'
        'You: <function=search_patients{"query": "Carlos"}</function>\n\n'
        'EXAMPLE with multiple params:\n'
        'User: "Registra pago de Juan por 100 soles en efectivo"\n'
        'You: <function=register_payment{"patient_id": 5, "amount": 100, "method": "Efectivo", "payment_date": "2026-08-18"}</function>\n\n'
        'TOOLS BY CATEGORY:\n\n'
        'PATIENTS/USERS: search_patients, list_patients, get_patient_detail, list_users, get_user_detail, create_user, update_user, delete_user, assign_therapist, update_patient, toggle_user_status\n'
        'SESSIONS: get_sessions, get_sessions_day, create_session, update_session, cancel_session, complete_session, batch_create_sessions\n'
        'INCIDENTS: create_incident, list_incidents, get_incident_detail, update_incident_status, assign_incident\n'
        'BRANCHES: list_sedes, get_sede_stats, list_patient_groups, create_patient_group\n'
        'FINANCE: get_financial_summary (use month/year params for past months), get_payment_history, register_payment, cancel_payment (delete a payment by ID), edit_payment (modify amount/method/date/status/receipt_url), get_debtors, send_payment_reminder, list_expenses, create_expense, get_therapist_financials, get_debt_summary, compare_periods (compare 2 months)\n'
        'REPORTS: generate_weekly_report, get_weekly_summary, get_monthly_reports, get_therapist_efficiency, get_user_growth (user registration metrics by month)\n'
        'MESSAGING: broadcast_message, send_direct_message, get_notifications, mark_notifications_read\n'
        'CONTRACTS: list_contracts\n\n'
        'PAYMENT WORKFLOW:\n'
        '1. search_patients to find the patient ID\n'
        '2. Ask: amount, method (Efectivo/Yape/Transferencia/IA/Copilot), date\n'
        '3. Only THEN call register_payment with ALL 4 params\n'
        '4. Confirm the result\n\n'
        'VOUCHER IMAGE PROCESSING:\n'
        'When user sends an image (voucher/comprobante):\n'
        '1. The frontend uploads image to /mcp/upload and gets OCR data\n'
        '2. OCR extracts: amount, method, date, patient_hint\n'
        '3. Use ONLY the OCR data provided - NEVER invent or guess values\n'
        '4. If OCR returns null for a field, ASK the user for that data\n'
        '5. Confirm all extracted data with user before registering\n'
        '6. Store image URL as receipt_url in the payment\n'
        '7. NEVER say "Juan Pérez" or "S/100" if OCR did not return those values\n\n'
        'EDITING PAYMENTS:\n'
        '1. get_payment_history(patient_id) to find the payment ID\n'
        '2. edit_payment(payment_id, amount=..., method=..., payment_date=..., status=..., receipt_url=...)\n'
        '3. Confirm changes to user\n\n'
        'DELETING PAYMENTS:\n'
        '1. get_payment_history(patient_id) to find the payment ID\n'
        '2. Show user the payment details and ask for confirmation\n'
        '3. cancel_payment(payment_id) — ONLY after user confirms\n\n'
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

# Broader fallback patterns for small models that deviate from the exact format
_FALLBACK_PATTERNS = [
    # Without braces: <function=search_patients</function> or <function=search_patients></function>
    re.compile(r'<function=(\w+)\s*</function>', re.DOTALL),
    # With single quotes: <function=search_patients{'query': 'Carlos'}</function>
    re.compile(r"<function=(\w+)\s*(' .*?')\s*</function>", re.DOTALL),
    # Markdown code block: ```function=search_patients{...}```
    re.compile(r'```[^`]*<function=(\w+)\s*(\{.*?\})?\s*</function>', re.DOTALL),
    # Partial: search_patients{"query":"Carlos"} (no <function> tags)
    re.compile(r'\b(\w+)\s*(\{[^{}]*\})\s*(?:->|$|\n)', re.DOTALL),
]

# Pattern for parentheses format: toolname(key: value, key: value)
_PAREN_PATTERN = re.compile(
    r'(\w+)\s*\(([^)]*)\)',
    re.DOTALL,
)


def _parse_paren_args(args_str):
    """Parse 'key: value, key: value' from parentheses format."""
    result = {}
    if not args_str or not args_str.strip():
        return result
    # Split by comma, but handle quoted strings
    parts = []
    current = ''
    in_quote = False
    quote_char = None
    for ch in args_str:
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
            current += ch
        elif ch == quote_char and in_quote:
            in_quote = False
            quote_char = None
            current += ch
        elif ch == ',' and not in_quote:
            parts.append(current.strip())
            current = ''
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())

    for part in parts:
        if ':' in part:
            key, _, value = part.partition(':')
            key = key.strip().strip('"').strip("'")
            value = value.strip().strip('"').strip("'")
            # Try to parse as int/float
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            result[key] = value
    return result


def _parse_text_tool_call(text):
    """Extract tool name and args from various tool call formats."""
    # Try strict pattern first
    match = TOOL_CALL_PATTERN.search(text)
    if match:
        tool_name = match.group(1)
        args_str = match.group(2)
        if args_str:
            try:
                tool_args = json.loads(args_str)
            except json.JSONDecodeError:
                tool_args = {}
        else:
            tool_args = {}
        # Only return if the tool name is actually registered
        if tool_name in TOOL_REGISTRY:
            return tool_name, tool_args

    # Try fallback patterns
    for pattern in _FALLBACK_PATTERNS:
        match = pattern.search(text)
        if match:
            tool_name = match.group(1)
            args_str = match.group(2) if match.lastindex >= 2 else None
            if tool_name not in TOOL_REGISTRY:
                continue
            if args_str:
                # Try to fix single quotes to double quotes
                fixed = args_str.replace("'", '"')
                try:
                    tool_args = json.loads(fixed)
                except json.JSONDecodeError:
                    tool_args = {}
            else:
                tool_args = {}
            return tool_name, tool_args

    # Try parentheses format: toolname(key: value, key: value)
    for match in _PAREN_PATTERN.finditer(text):
        tool_name = match.group(1)
        args_str = match.group(2)
        if tool_name in TOOL_REGISTRY:
            tool_args = _parse_paren_args(args_str)
            return tool_name, tool_args

    return None, None


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
        'IMPORTANT: For any tool that REGISTERS, UPDATES, DELETES, or CHANGES STATE (payments, users, sessions, '
        'incidents, expenses, messages, contracts, patient groups, reminders), you MUST first collect ALL required '
        'parameters from the user one by one. If a required parameter is missing, ASK for it. '
        'Only call the tool once you have every required value. The system will then ask the user to confirm before executing.',
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

    def process_message(
        self, message, user_role, user_id, mode='grande', history=None, confirmed_tool=None, telegram_mode=False
    ):
        system_prompt = SYSTEM_PROMPTS.get(user_role, SYSTEM_PROMPTS['jugador'])

        if telegram_mode:
            system_prompt += (
                '\n\nTELEGRAM MODE:\n'
                '- You are responding via Telegram chat.\n'
                '- Keep responses SHORT (max 10 lines).\n'
                '- Use emoji sparingly for emphasis.\n'
                '- Format with *bold* and _italic_ for readability.\n'
                '- For lists, use bullet points.\n'
                '- If data is long, summarize with count + top 3 items.\n'
                '- Always end with a clear answer or next step.\n'
            )

        tools = get_tools_for_mode(mode, user_role)
        tool_prompt = _build_tool_prompt(tools)

        full_system = get_current_date_context() + '\n\n' + system_prompt + '\n\n' + tool_prompt
        messages = [{'role': 'system', 'content': full_system}]

        if history:
            for h in history[-8:]:
                messages.append({'role': h['role'], 'content': h['content']})

        messages.append({'role': 'user', 'content': message})

        tool_calls_log = []

        def _safe_write(name):
            entry = TOOL_REGISTRY.get(name, {})
            return bool(entry) and entry.get('category') == 'write' and name not in SAFE_WRITE_TOOLS

        # If confirmed_tool is provided, execute it directly without calling LLM
        if confirmed_tool and confirmed_tool.get('name'):
            tool_name = confirmed_tool['name']
            tool_args = confirmed_tool.get('args') or {}
            logger.info(f'MCP confirmed tool execution: {tool_name}({tool_args})')

            try:
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
                # Generate a natural response from the result
                messages.append(
                    {
                        'role': 'user',
                        'content': (
                            f'[Tool {tool_name} result — use ONLY this data]:\n'
                            f'{result_str}\n\n'
                            f'Respond to the user using ONLY the exact values above. '
                            f'Keep it SHORT and natural. Use emoji for confirmation.'
                        ),
                    }
                )

                content, provider = llm_chat(messages, temperature=0.3, max_tokens=1024)
                return {
                    'response': content or f'✅ Operación ejecutada: {tool_name}',
                    'tool_calls': tool_calls_log,
                    'done': True,
                    'provider': provider,
                }
            except Exception as e:
                logger.error(f'MCP confirmed tool execution error: {e}', exc_info=True)
                return {
                    'response': f'❌ Error ejecutando la operación: {str(e)[:200]}',
                    'tool_calls': tool_calls_log,
                    'done': True,
                }

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

                    # Write tools require explicit confirmation before running.
                    confirmed_name = (confirmed_tool or {}).get('name')
                    if _safe_write(tool_name) and not confirmed_name:
                        return {
                            'response': 'Acción pendiente de confirmación.',
                            'tool_calls': tool_calls_log,
                            'done': False,
                            'requires_confirmation': True,
                            'pending_tool': {'name': tool_name, 'args': tool_args, 'tool_call_text': content},
                            'provider': provider,
                        }

                    # On confirmation, prefer the args captured at request time (e.g. receipt_url of a voucher).
                    effective_args = tool_args
                    if confirmed_name and confirmed_name == tool_name:
                        saved_args = (confirmed_tool or {}).get('args') or {}
                        if saved_args:
                            effective_args = {**tool_args, **saved_args}

                    result = execute_tool(tool_name, effective_args, user_id=user_id, role=user_role)
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
