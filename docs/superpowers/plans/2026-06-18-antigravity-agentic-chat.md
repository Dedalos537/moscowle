# Antigravity Agentic Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static-context intent-based chat with a true agentic ReAct system using Groq tool-calling, two modes (chiquito/grande), and a ReAct payment flow.

**Architecture:** New `agent_orchestrator.py` runs a ReAct loop calling Groq with JSON Schema tools. `tools_registry.py` defines ~30 tools with handlers. Frontend sends `mode` flag. Read-only tools in Chiquito, all tools in Grande.

**Tech Stack:** Groq (llama-3.1-8b-instant), Flask, Angular 17, python-groq SDK

---

## File Structure

```
Create:
  app/services/tools_registry.py        — ~30 tool definitions + handlers
  app/services/agent_orchestrator.py    — ReAct loop with Groq

Modify:
  app/routes/llama_routes.py            — Add POST /llama/agent endpoint (lines 8-46)
  edysync/src/app/core/services/llama.service.ts    — sendAgentMessage()
  edysync/src/app/shared/components/ai-chat/ai-chat.ts — mode logic
  edysync/src/app/shared/components/ai-chat/ai-chat.html — placeholder text
```

---

### Task 1: Create tools_registry.py — Phase 1 (Read tools)

**Files:**
- Create: `app/services/tools_registry.py`

**Context:** This file defines the 8 read-only tools for Phase 1. Each tool has a JSON Schema for Groq and a handler function that calls the DB/service layer directly. All handlers are async-safe (Flask synchronous context is fine).

- [ ] **Step 1: Create the file with tool definitions + handler pattern**

```python
import json
import logging
from datetime import datetime, timedelta

from flask import current_app
from app.models import User, Appointment, Payment
from app.extensions import db

logger = logging.getLogger('app')

TOOL_REGISTRY = {}

def tool(name, description, parameters, category='read'):
    """Decorator to register a tool."""
    def decorator(func):
        TOOL_REGISTRY[name] = {
            'name': name,
            'description': description,
            'parameters': parameters,
            'category': category,
            'handler': func,
        }
        return func
    return decorator


def get_tools_for_mode(mode):
    """Return list of tool dicts for Groq API based on mode."""
    tools = []
    for name, t in TOOL_REGISTRY.items():
        if mode == 'chiquito' and t['category'] == 'write':
            continue
        tools.append({
            'type': 'function',
            'function': {
                'name': t['name'],
                'description': t['description'],
                'parameters': t['parameters'],
            }
        })
    return tools


def execute_tool(name, args):
    """Execute a tool by name with given args. Returns dict result."""
    t = TOOL_REGISTRY.get(name)
    if not t:
        return {'error': f'Unknown tool: {name}'}
    try:
        return t['handler'](**args)
    except Exception as e:
        logger.error(f'Tool {name} error: {e}', exc_info=True)
        return {'error': str(e)}
```

- [ ] **Step 2: Implement search_patients tool**

```python
@tool(
    name='search_patients',
    description='Busca pacientes por nombre, email o telefono. MINIMO 2 caracteres.',
    parameters={
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Termino de busqueda (min 2 caracteres)'},
            'limit': {'type': 'integer', 'description': 'Maximo resultados', 'default': 10},
        },
        'required': ['query'],
    },
    category='read',
)
def handle_search_patients(query, limit=10):
    if len(query) < 2:
        return {'error': 'Minimo 2 caracteres'}
    patients = User.query.filter(
        db.or_(
            User.username.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%'),
            User.phone.ilike(f'%{query}%'),
        )
    ).limit(limit).all()
    return {
        'success': True,
        'count': len(patients),
        'patients': [{
            'id': p.id,
            'username': p.username,
            'email': p.email,
            'role': p.role,
            'is_active': p.is_active,
            'phone': getattr(p, 'phone', ''),
        } for p in patients],
    }
```

- [ ] **Step 3: Implement list_users and get_user tools**

```python
@tool(
    name='list_users',
    description='Lista todos los usuarios del sistema. Opcionalmente filtrar por rol.',
    parameters={
        'type': 'object',
        'properties': {
            'role': {
                'type': 'string',
                'description': 'Filtrar por rol: admin, terapista, jugador, supervisor',
                'enum': ['admin', 'terapista', 'jugador', 'supervisor'],
            },
        },
    },
    category='read',
)
def handle_list_users(role=None):
    q = User.query
    if role:
        q = q.filter_by(role=role)
    users = q.order_by(User.username).limit(100).all()
    return {
        'success': True,
        'count': len(users),
        'users': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active,
        } for u in users],
    }


@tool(
    name='get_user',
    description='Obtiene detalle completo de un usuario por ID.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
        },
        'required': ['user_id'],
    },
    category='read',
)
def handle_get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    return {
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'phone': getattr(user, 'phone', ''),
            'sede_id': getattr(user, 'sede_id', None),
            'created_at': str(user.created_at) if hasattr(user, 'created_at') else '',
        },
    }
```

- [ ] **Step 4: Implement financial/debt/sessions tools**

```python
from app.services.financial_service import FinancialService
from app.services.payment_service import PaymentService

_finance_service = FinancialService()
_payment_service = PaymentService()


@tool(
    name='get_financial_summary',
    description='Resumen financiero del mes actual: ingresos, egresos, ganancia, cobranza.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_financial_summary():
    from flask import url_for
    try:
        resp = current_app.test_client().get('/admin/api/financial-summary')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_debt_report',
    description='Reporte de deudores. Muestra pacientes con pagos pendientes agrupados por sede.',
    parameters={
        'type': 'object',
        'properties': {
            'month': {'type': 'string', 'description': 'Mes en formato YYYY-MM o "all" para todos', 'default': 'current'},
        },
    },
    category='read',
)
def handle_debt_report(month='current'):
    from flask import url_for
    try:
        resp = current_app.test_client().get(f'/api/admin/deudores?month={month}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_sessions',
    description='Obtiene sesiones del calendario en un rango de fechas.',
    parameters={
        'type': 'object',
        'properties': {
            'start': {'type': 'string', 'description': 'Fecha inicio (YYYY-MM-DD)'},
            'end': {'type': 'string', 'description': 'Fecha fin (YYYY-MM-DD)'},
            'therapist_id': {'type': 'integer', 'description': 'Filtrar por terapeuta'},
        },
    },
    category='read',
)
def handle_get_sessions(start=None, end=None, therapist_id=None):
    from flask import url_for
    try:
        params = {}
        if start: params['start'] = start
        if end: params['end'] = end
        if therapist_id: params['therapist_id'] = therapist_id
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = current_app.test_client().get(f'/admin/api/sessions?{qs}')
        data = resp.get_json() if resp else []
        return {'success': True, 'count': len(data) if isinstance(data, list) else 0, 'sessions': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_therapist_efficiency',
    description='Metricas de eficiencia de terapeutas: sesiones, accuracy, audit compliance.',
    parameters={
        'type': 'object',
        'properties': {
            'therapist_id': {'type': 'integer', 'description': 'Filtrar por terapeuta especifico'},
        },
    },
    category='read',
)
def handle_therapist_efficiency(therapist_id=None):
    from flask import url_for
    try:
        params = f'?therapist_id={therapist_id}' if therapist_id else ''
        resp = current_app.test_client().get(f'/admin/api/therapist-efficiency{params}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}
```

- [ ] **Step 5: Implement get_payment_history tool**

```python
@tool(
    name='get_payment_history',
    description='Historial de pagos de un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='read',
)
def handle_payment_history(patient_id):
    patient = User.query.get(patient_id)
    if not patient:
        return {'error': 'Paciente no encontrado'}
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).limit(50).all()
    return {
        'success': True,
        'patient': {'id': patient.id, 'username': patient.username},
        'payments': [{
            'id': p.id,
            'amount': float(p.amount),
            'date': str(p.date),
            'method': p.method,
            'reference': p.reference,
        } for p in payments],
    }
```

- [ ] **Step 6: Commit**

```bash
git add app/services/tools_registry.py
git commit -m "feat(agent): create tools_registry.py with Phase 1 read tools"
```

---

### Task 2: Create agent_orchestrator.py

**Files:**
- Create: `app/services/agent_orchestrator.py`

- [ ] **Step 1: Create the ReAct orchestrator**

```python
import json
import logging
import os
from groq import Groq

from app.services.tools_registry import get_tools_for_mode, execute_tool

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

    for iteration in range(MAX_ITERATIONS):
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

                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call.id,
                    'content': result_str,
                })
            except Exception as e:
                logger.error(f'Error executing tool {tool_call.function.name}: {e}', exc_info=True)
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call.id,
                    'content': json.dumps({'error': str(e)}),
                })

    # Max iterations reached — return last assistant content or fallback
    return build_result(
        'La operacion requiere muchos pasos. Por favor, intenta con una instruccion mas directa.',
        intent='general_chat',
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/services/agent_orchestrator.py
git commit -m "feat(agent): create agent_orchestrator.py with ReAct loop"
```

---

### Task 3: Add POST /llama/agent endpoint

**Files:**
- Modify: `app/routes/llama_routes.py` — add new endpoint before `get_chat_history` (line ~44)

- [ ] **Step 1: Add the import and endpoint**

Find the line `llama_bp = Blueprint('llama', __name__, url_prefix='/llama')` and add imports after it:

```python
from app.services.agent_orchestrator import process_agent_message
```

Then add the new endpoint before the `get_chat_history` function:

```python
@llama_bp.route('/agent', methods=['POST'])
@csrf.exempt
@login_required
def agent_send():
    auth_error = _require_admin_or_supervisor()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    user_message = sanitize_text(data.get('message', ''))
    if not user_message:
        return jsonify({'error': 'Mensaje vacio'}), 400

    mode = data.get('mode', 'chiquito')
    if mode not in ('chiquito', 'grande'):
        mode = 'chiquito'

    try:
        conversation_id = get_or_create_conversation(current_user.id)
        save_chat_message(conversation_id, 'user', user_message)

        result = process_agent_message(current_user.id, user_message, mode=mode)

        save_chat_message(
            conversation_id, 'assistant', result.get('response', ''),
            intent=result.get('intent', 'general_chat'),
        )

        result['conversation_id'] = conversation_id
        result['success'] = True
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f'Error en /llama/agent: {e}', exc_info=True)
        return jsonify({'success': False, 'error': f'Error: {str(e)[:100]}}'}), 500
```

- [ ] **Step 2: Commit**

```bash
git add app/routes/llama_routes.py
git commit -m "feat(agent): add POST /llama/agent endpoint"
```

---

### Task 4: Frontend — Add sendAgentMessage to LlamaService

**Files:**
- Modify: `edysync/src/app/core/services/llama.service.ts`

- [ ] **Step 1: Add the sendAgentMessage method**

After the existing `sendMessage` method, add:

```typescript
sendAgentMessage(message: string, mode: 'chiquito' | 'grande'): Observable<LlamaResponse> {
  return this.http.post<LlamaResponse>('/llama/agent', { message, mode });
}
```

- [ ] **Step 2: Commit**

```bash
git add edysync/src/app/core/services/llama.service.ts
git commit -m "feat(agent): add sendAgentMessage to llama service"
```

---

### Task 5: Frontend — Wire mode into ai-chat.ts

**Files:**
- Modify: `edysync/src/app/shared/components/ai-chat/ai-chat.ts`

- [ ] **Step 1: Change sendMessage to use mode**

Replace the `sendMessage()` method's call from `this.llama.sendMessage(msg, page)` to use `sendAgentMessage` when in grande mode. Add a mode getter.

Add this property:
```typescript
get currentMode(): 'chiquito' | 'grande' {
  return this.fullScreen ? 'grande' : 'chiquito';
}
```

Then modify the `sendMessage()` method. Find the line:
```typescript
this.subs.add(this.llama.sendMessage(msg, page).subscribe({
```

Replace with:
```typescript
const obs = this.fullScreen
  ? this.llama.sendAgentMessage(msg, 'grande')
  : this.llama.sendMessage(msg, page);

this.subs.add(obs.subscribe({
```

Also update the `sendSuggestion` method to pass mode context. And in `loadInitialContext`, pass the mode:

```typescript
private loadInitialContext() {
  this.currentPage = this.detectCurrentPage();
  const mode = this.currentMode;
  const obs = mode === 'grande'
    ? this.llama.sendAgentMessage('context_init', 'grande')
    : this.llama.sendMessage('context_init', this.currentPage);

  this.subs.add(obs.subscribe({
    next: (res) => {
      if (res.success) {
        this.suggestions = res.suggestions || [];
        this.actionChips = res.action_chips || [];
        if (res.response) {
          this.welcomeMessage = res.response;
        }
      }
      this.cdr.markForCheck();
    },
    error: () => {
      this.suggestions = ['Ver deudores', 'Registrar pago', 'Crear usuario', 'Ir a finanzas', 'Ver reporte'];
      this.cdr.markForCheck();
    },
  }));
}
```

- [ ] **Step 2: Add mode badge in the header**

Add to the `ai-chat.html` template, inside the header next to the title, a small badge when in grande mode:

```html
@if (fullScreen) {
  <span class="mode-badge mode-badge--grande">Admin</span>
} @else {
  <span class="mode-badge mode-badge--chiquito">Consulta</span>
}
```

Add to `ai-chat.scss`:
```scss
.mode-badge {
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-left: 8px;
}

.mode-badge--chiquito {
  background: var(--color-surface-container-highest);
  color: var(--color-on-surface-variant);
}

.mode-badge--grande {
  background: var(--color-primary);
  color: var(--color-on-primary);
}
```

- [ ] **Step 3: Commit**

```bash
git add edysync/src/app/shared/components/ai-chat/ai-chat.ts edysync/src/app/shared/components/ai-chat/ai-chat.html edysync/src/app/shared/components/ai-chat/ai-chat.scss
git commit -m "feat(agent): wire mode (chiquito/grande) into ai-chat"
```

---

### Task 6: Add Phase 2 tools — Payments & Vouchers

**Files:**
- Modify: `app/services/tools_registry.py` — append new tools

- [ ] **Step 1: Add register_payment tool**

```python
@tool(
    name='register_payment',
    description='Registra un pago para un paciente. SOLO cuando tengas patient_id y amount confirmados.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'amount': {'type': 'number', 'description': 'Monto del pago en soles'},
            'method': {
                'type': 'string',
                'description': 'Metodo de pago',
                'enum': ['Efectivo', 'Yape', 'Transferencia', 'IA/Copilot', 'IA/Copilot + OCR'],
                'default': 'IA/Copilot',
            },
            'reference': {'type': 'string', 'description': 'Referencia del pago'},
        },
        'required': ['patient_id', 'amount'],
    },
    category='write',
)
def handle_register_payment(patient_id, amount, method='IA/Copilot', reference=''):
    from datetime import datetime, timedelta
    patient = User.query.get(patient_id)
    if not patient:
        return {'error': 'Paciente no encontrado'}
    try:
        success, result = _payment_service.register_payment(
            patient_id=patient_id,
            amount=float(amount),
            method=method,
            reference=reference or 'Copilot',
            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        )
        if success:
            return {
                'success': True,
                'message': f'Pago de S/. {amount:.2f} registrado para {patient.username}',
                'payment_id': result.id if hasattr(result, 'id') else None,
            }
        else:
            return {'error': str(result)}
    except Exception as e:
        return {'error': str(e)}
```

- [ ] **Step 2: Add payment info, all payments, delete, yape tools**

```python
@tool(
    name='get_payment_info',
    description='Obtiene configuracion de pago de un paciente (monto, fecha de vencimiento, plan).',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
        },
        'required': ['patient_id'],
    },
    category='read',
)
def handle_get_payment_info(patient_id):
    try:
        resp = current_app.test_client().get(f'/admin/api/payment-info/{patient_id}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_all_payments',
    description='Lista los ultimos pagos registrados en el sistema.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_all_payments():
    try:
        resp = current_app.test_client().get('/admin/api/payments/all')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_yape_pending',
    description='Transacciones Yape pendientes de asignar a pacientes.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_yape_pending():
    try:
        resp = current_app.test_client().get('/admin/yape/pending')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='search_yape_transactions',
    description='Busca transacciones Yape por query (operacion, monto, etc).',
    parameters={
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Termino de busqueda'},
        },
        'required': ['query'],
    },
    category='read',
)
def handle_search_yape(query):
    from flask import url_for
    try:
        resp = current_app.test_client().get(f'/admin/yape/search?q={query}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}
```

- [ ] **Step 3: Commit**

```bash
git add app/services/tools_registry.py
git commit -m "feat(agent): add Phase 2 payment and voucher tools"
```

---

### Task 7: Add Phase 3 tools — Users & Sessions

**Files:**
- Modify: `app/services/tools_registry.py` — append new tools

- [ ] **Step 1: Add create_user, update_user, toggle_user_status, delete_user**

```python
@tool(
    name='create_user',
    description='Crea un nuevo usuario en el sistema.',
    parameters={
        'type': 'object',
        'properties': {
            'username': {'type': 'string', 'description': 'Nombre completo del usuario'},
            'role': {
                'type': 'string',
                'description': 'Rol del usuario',
                'enum': ['jugador', 'terapista', 'admin'],
                'default': 'jugador',
            },
            'email': {'type': 'string', 'description': 'Email del usuario'},
        },
        'required': ['username'],
    },
    category='write',
)
def handle_create_user(username, role='jugador', email=None):
    from app.auth_compat import current_user
    if current_user.role != 'admin':
        return {'error': 'Solo administradores pueden crear usuarios'}
    import secrets
    from app.extensions import bcrypt
    _DEFAULT_USER_PASSWORD = os.environ.get('DEFAULT_USER_PASSWORD') or secrets.token_urlsafe(12)
    if not email:
        email = f'{username.lower().replace(" ", ".")}@centrojuanpabloii.com'
    existing = User.query.filter(
        db.or_(User.username.ilike(username), User.email == email)
    ).first()
    if existing:
        return {'error': f'Ya existe un usuario: {existing.username}'}
    user = User(
        username=username,
        email=email,
        password=bcrypt.generate_password_hash(_DEFAULT_USER_PASSWORD).decode('utf-8'),
        role=role,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return {
        'success': True,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'temp_password': _DEFAULT_USER_PASSWORD,
        'message': f'Usuario {username} creado como {role}',
    }


@tool(
    name='toggle_user_status',
    description='Activa o desactiva un usuario. El estado cambia al opuesto del actual.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
        },
        'required': ['user_id'],
    },
    category='write',
)
def handle_toggle_user_status(user_id):
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activado' if user.is_active else 'desactivado'
    return {
        'success': True,
        'user_id': user.id,
        'username': user.username,
        'is_active': user.is_active,
        'message': f'Usuario {user.username} {status}',
    }


@tool(
    name='delete_user',
    description='ELIMINA un usuario permanentemente del sistema. SOLO ejecutar tras confirmacion explicita del usuario.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario a eliminar'},
        },
        'required': ['user_id'],
    },
    category='write',
)
def handle_delete_user(user_id):
    from app.auth_compat import current_user
    if current_user.role != 'admin':
        return {'error': 'Solo administradores pueden eliminar usuarios'}
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    if user.id == current_user.id:
        return {'error': 'No puedes eliminarte a ti mismo'}
    # Delete related records
    from app.models import AIChatMessage, Appointment, Payment, ContactMessage, Notification
    for model in [AIChatMessage, Appointment, Payment, ContactMessage, Notification]:
        model.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return {'success': True, 'message': f'Usuario {user.username} eliminado'}
```

- [ ] **Step 2: Add assign_therapist, reset_password, create_appointment, update_session**

```python
@tool(
    name='assign_therapist',
    description='Asigna uno o mas terapeutas a un paciente.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'therapist_ids': {
                'type': 'array',
                'items': {'type': 'integer'},
                'description': 'IDs de los terapeutas a asignar',
            },
        },
        'required': ['patient_id', 'therapist_ids'],
    },
    category='write',
)
def handle_assign_therapist(patient_id, therapist_ids):
    if isinstance(therapist_ids, int):
        therapist_ids = [therapist_ids]
    from flask import url_for
    try:
        resp = current_app.test_client().post(
            '/api/admin/assign-therapist',
            json={'patient_id': patient_id, 'therapist_ids': therapist_ids},
        )
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='reset_password',
    description='Resetea la contrasena de un usuario a una temporal.',
    parameters={
        'type': 'object',
        'properties': {
            'user_id': {'type': 'integer', 'description': 'ID del usuario'},
        },
        'required': ['user_id'],
    },
    category='write',
)
def handle_reset_password(user_id):
    from app.auth_compat import current_user
    if current_user.role != 'admin':
        return {'error': 'Solo administradores pueden resetear contrasenas'}
    import secrets
    from app.extensions import bcrypt
    user = User.query.get(user_id)
    if not user:
        return {'error': 'Usuario no encontrado'}
    new_pw = secrets.token_urlsafe(8)
    user.password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    return {
        'success': True,
        'message': f'Contrasena reseteada para {user.username}',
        'temp_password': new_pw,
    }


@tool(
    name='create_appointment',
    description='Crea una sesion para un paciente con un terapeuta.',
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'ID del paciente'},
            'patient_name': {'type': 'string', 'description': 'Nombre del paciente (si no sabes el ID)'},
            'day': {'type': 'string', 'description': 'Dia de la sesion (YYYY-MM-DD)'},
            'time': {'type': 'string', 'description': 'Hora (HH:MM)'},
            'duration_minutes': {'type': 'integer', 'description': 'Duracion en minutos', 'default': 60},
        },
    },
    category='write',
)
def handle_create_appointment(patient_id=None, patient_name=None, day=None, time=None, duration_minutes=60):
    if not patient_id and not patient_name:
        return {'error': 'Debes proporcionar patient_id o patient_name'}
    if not patient_id:
        patient = User.query.filter(User.username.ilike(f'%{patient_name}%'), User.role == 'jugador').first()
        if not patient:
            return {'error': f'Paciente "{patient_name}" no encontrado'}
        patient_id = patient.id
    from datetime import datetime, timedelta
    from app.models import Appointment
    from app.auth_compat import current_user
    if day and time:
        start_str = f'{day} {time}'
    else:
        start_str = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d %H:%M')
    except ValueError:
        start_dt = datetime.now() + timedelta(hours=1)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    patient = User.query.get(patient_id)
    appt = Appointment(
        therapist_id=current_user.id,
        patient_id=patient_id,
        title=f'Sesion con {patient.username}',
        start_time=start_dt,
        end_time=end_dt,
        status='scheduled',
    )
    db.session.add(appt)
    db.session.commit()
    return {
        'success': True,
        'appointment_id': appt.id,
        'message': f'Sesion creada para {patient.username} el {start_dt.strftime("%d/%m/%Y %H:%M")}',
    }


@tool(
    name='get_dashboard_overview',
    description='Resumen general del dashboard: total terapeutas, pacientes, sesiones, accuracy.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_dashboard_overview():
    try:
        resp = current_app.test_client().get('/admin/api/overview')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}
```

- [ ] **Step 2: Commit**

```bash
git add app/services/tools_registry.py
git commit -m "feat(agent): add Phase 3 user and session tools"
```

---

### Task 8: Add Phase 4+ tools — Expenses, Reports, Broadcast, Sedes

**Files:**
- Modify: `app/services/tools_registry.py` — append new tools

- [ ] **Step 1: Add expense, broadcast, report, sede tools**

```python
@tool(
    name='register_expense',
    description='Registra un gasto del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'category': {'type': 'string', 'description': 'Categoria del gasto'},
            'amount': {'type': 'number', 'description': 'Monto en soles'},
            'description': {'type': 'string', 'description': 'Descripcion del gasto'},
            'date': {'type': 'string', 'description': 'Fecha del gasto (YYYY-MM-DD)'},
        },
        'required': ['category', 'amount'],
    },
    category='write',
)
def handle_register_expense(category, amount, description='', date=None):
    from app.services.financial_service import FinancialService
    svc = FinancialService()
    try:
        expense_data = {
            'category': category,
            'amount': float(amount),
            'date': date or datetime.now().strftime('%Y-%m-%d'),
            'description': description or 'Gasto via Copilot',
            'method': 'IA/Copilot',
        }
        svc.create_expense(expense_data)
        return {'success': True, 'message': f'Gasto de S/. {amount} registrado en {category}'}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_expenses',
    description='Obtiene lista de gastos del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'start_date': {'type': 'string', 'description': 'Fecha inicio (YYYY-MM-DD)'},
            'end_date': {'type': 'string', 'description': 'Fecha fin (YYYY-MM-DD)'},
            'category': {'type': 'string', 'description': 'Filtrar por categoria'},
        },
    },
    category='read',
)
def handle_get_expenses(start_date=None, end_date=None, category=None):
    try:
        params = {}
        if start_date: params['start_date'] = start_date
        if end_date: params['end_date'] = end_date
        if category: params['category'] = category
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = current_app.test_client().get(f'/admin/api/expenses?{qs}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='broadcast_message',
    description='Envia un mensaje a todos los pacientes, terapeutas, o un usuario especifico.',
    parameters={
        'type': 'object',
        'properties': {
            'subject': {'type': 'string', 'description': 'Asunto del mensaje'},
            'body': {'type': 'string', 'description': 'Cuerpo del mensaje'},
            'target': {
                'type': 'string',
                'description': 'Destinatarios: all, therapists, patients, specific',
                'default': 'all',
            },
            'receiver_id': {'type': 'integer', 'description': 'ID del usuario si target=specific'},
        },
        'required': ['subject', 'body'],
    },
    category='write',
)
def handle_broadcast(subject, body, target='all', receiver_id=None):
    from flask import url_for
    try:
        payload = {'subject': subject, 'body': body, 'target': target}
        if receiver_id:
            payload['receiver_id'] = receiver_id
        resp = current_app.test_client().post(
            '/api/admin/messages/broadcast',
            json=payload,
        )
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_weekly_summary',
    description='Resumen semanal por terapeuta.',
    parameters={
        'type': 'object',
        'properties': {
            'week_start': {'type': 'string', 'description': 'Fecha de inicio de la semana (YYYY-MM-DD)'},
        },
    },
    category='read',
)
def handle_weekly_summary(week_start=None):
    try:
        params = f'?week_start={week_start}' if week_start else ''
        resp = current_app.test_client().get(f'/admin/api/weekly-summary{params}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_monthly_summary',
    description='Resumen mensual del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'year': {'type': 'integer', 'description': 'Ano'},
            'month': {'type': 'integer', 'description': 'Mes (1-12)'},
        },
    },
    category='read',
)
def handle_monthly_summary(year=None, month=None):
    try:
        params = {}
        if year: params['year'] = year
        if month: params['month'] = month
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        resp = current_app.test_client().get(f'/admin/api/reports/monthly?{qs}')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='generate_ai_report',
    description='Genera un reporte estrategico de inteligencia artificial del centro.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_generate_report():
    from flask import url_for
    try:
        resp = current_app.test_client().post('/admin/generate-ia-report')
        data = resp.get_json() if resp else {}
        return {'success': True, 'data': data}
    except Exception as e:
        return {'error': str(e)}


@tool(
    name='get_sedes',
    description='Lista todas las sedes del centro.',
    parameters={'type': 'object', 'properties': {}},
    category='read',
)
def handle_get_sedes():
    sedes = __import__('app.models', fromlist=['Sede']).Sede.query.all()
    from app.models import User
    return {
        'success': True,
        'sedes': [{
            'id': s.id,
            'name': s.name,
            'address': getattr(s, 'address', ''),
            'patient_count': User.query.filter_by(sede_id=s.id, role='jugador').count(),
        } for s in sedes],
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/services/tools_registry.py
git commit -m "feat(agent): add Phase 4 expense, report, broadcast, sede tools"
```

---

### Task 9: Test the full ReAct flow

**Files:** No file changes — manual testing

- [ ] **Step 1: Start the Flask dev server**

```bash
python run.py
```

Test with curl:

```bash
# Test chiquito mode
curl -X POST http://localhost:5000/llama/agent \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"message": "cuantos pacientes hay?", "mode": "chiquito"}'

# Test grande mode — search patients
curl -X POST http://localhost:5000/llama/agent \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"message": "busca al paciente Juan", "mode": "grande"}'

# Test grande mode — register payment
curl -X POST http://localhost:5000/llama/agent \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"message": "registra un pago de S/150 para Maria", "mode": "grande"}'

# Test chiquito mutation block
curl -X POST http://localhost:5000/llama/agent \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"message": "registra un pago", "mode": "chiquito"}'
```

Expected chiquito mutation block response:
`"Para procesar eso, cambia al **Modo Administrador** (⛶ pantalla completa)"`

- [ ] **Step 2: Deploy**

```bash
# Frontend build
cd edysync && npx ng build --configuration production && cd ..

# Commit all remaining changes
git add -A
git commit -m "feat(agent): antigravity agentic chat v1 — ReAct loop, 30 tools, two modes"

# Push to repos
git push dedalos main
cd railway_deploy && cp ../app/services/agent_orchestrator.py app/services/ && cp ../app/services/tools_registry.py app/services/ && cp ../app/routes/llama_routes.py app/routes/ && git add -A && git commit -m "feat(agent): antigravity agentic chat" && git push origin main && cd ..
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Tool-calling nativo con Groq | Task 1 (tools_registry) + Task 2 (agent_orchestrator loop) |
| Eliminar contexto estatico "3 pacientes" | Task 1 — search_patients tool reemplaza el bloque estatico |
| Modo Chiquito (read-only) | Task 2 — system prompt restrictivo, filtra tools `category='read'` |
| Modo Grande (agentic admin) | Task 2 — todas las tools, system prompt agente |
| Mode routing por fullScreen | Task 5 — `currentMode` getter en ai-chat.ts |
| ReAct flow para pagos con voucher | Task 6 — register_payment tool, prompt le exige confirmar datos |
| 30 tools cubriendo todos los endpoints | Tasks 1, 6, 7, 8 |
| Nuevo endpoint /llama/agent | Task 3 |
| sendAgentMessage en frontend | Task 4 |
| Mode badge en UI | Task 5 |
