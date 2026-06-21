# Antigravity Agentic Chat — Refactorizacion Extrema

**Fecha:** 2026-06-18
**Estado:** Aprobado para implementacion

## Problema

1. **Contexto estatico de "3 pacientes"** — El chat envia un bloque de texto plano con los primeros 5 pacientes como contexto. El modelo no tiene forma de buscar mas pacientes ni datos actualizados.
2. **Un solo modo** — No hay diferenciacion entre consulta rapida y modo administrador completo.
3. **Sin ReAct** — Los pagos con voucher (Yape) no siguen un flujo agente: analizar, extraer, preguntar, ejecutar.
4. **Sin tool-calling nativo** — El sistema actual usa regex + keywords para deteccion de intencion, sin llamadas a funciones reales.

## Arquitectura

```
Frontend (Angular)                    Backend (Flask)                     Groq API
┌─────────────────────┐   POST        ┌─────────────────────────┐  tools  ┌──────────┐
│ ai-chat.ts           │  /llama/agent│ agent_orchestrator.py   │ ──────→ │ llama-   │
│  mode: chiquito/     │ ────────────→│                         │ ←────── │ 3.1-8b  │
│        grande        │              │ 1. Build system prompt   │         └──────────┘
│  message loop        │              │ 2. Groq + tools         │
│  tool results        │ ←─────────── │ 3. tool_call → handler   │
└─────────────────────┘   response   │ 4. loop max 5 iter.     │
                                       └─────────────────────────┘
                                        tools_registry.py
                                        ┌──────────────────────┐
                                        │ ~30 tools con JSON    │
                                        │ Schema + handlers     │
                                        └──────────────────────┘
```

## Componentes Nuevos

### 1. `app/services/agent_orchestrator.py` (nuevo)

Loop ReAct completo:

```python
def process_agent_message(uid, message, mode='chiquito'):
    # 1. Build system prompt segun mode
    system_prompt = get_system_prompt(mode)

    # 2. Tools disponibles segun mode
    tools = get_tools_for_mode(mode)  # solo lectura vs todas

    # 3. Loop ReAct (max 5 iterations)
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": message}]

    for _ in range(5):
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            # Respuesta final en texto
            return build_result(msg.content)

        # Ejecutar tool calls
        for tool_call in msg.tool_calls:
            result = execute_tool(tool_call.function.name,
                                  json.loads(tool_call.function.arguments))
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

    return build_result("Lo siento, no pude completar la operacion.")
```

### 2. `app/services/tools_registry.py` (nuevo)

Registro centralizado de ~30 tools. Cada tool tiene:
- `name` — nombre unico
- `description` — descripcion para el LLM
- `parameters` — JSON Schema para Groq
- `handler` — nombre de funcion ejecutora
- `category` — `'read'` o `'write'` (para filtrar por modo)
- `handler_func` — referencia a la funcion

### 3. System Prompts

**Chiquito:**
```
Eres un asistente de consulta del Centro de Terapias Juan Pablo II.
SOLO PUEDES LEER DATOS — NUNCA crear, modificar o eliminar.

Reglas:
- Responde en Markdown limpio
- Si tienes dudas sobre datos, usa search_patients, list_users
- Si el usuario pide registrar un pago, crear usuario, o cualquier mutacion:
  → Responde: "Para procesar eso, cambia al **Modo Administrador** (⛶ pantalla completa)"
```

**Grande:**
```
Eres un agente administrador con control total del Centro de Terapias Juan Pablo II.
Tienes acceso a TODAS las herramientas del sistema.

Directrices ReAct:
1. Cuando necesites datos → llama a la tool correspondiente
2. Para pagos con voucher: analiza → extrae monto → si falta paciente, pregunta →
   solo cuando tengas todo el payload, ejecuta register_payment
3. Para crear usuarios: pregunta por nombre y rol explicitamente
```

## Tools por Fase de Implementacion

### Fase 1 — Busqueda y Lectura (8 tools)
| Tool | Handler | Read-only |
|------|---------|-----------|
| `search_patients(query, limit)` | `handle_search_patients` | Si |
| `list_users(role)` | `handle_list_users` | Si |
| `get_user(id)` | `handle_get_user` | Si |
| `get_financial_summary()` | `handle_financial_summary` | Si |
| `get_debt_report(month)` | `handle_debt_report` | Si |
| `get_sessions(start, end, therapist_id)` | `handle_get_sessions` | Si |
| `get_therapist_efficiency(therapist_id)` | `handle_therapist_efficiency` | Si |
| `get_payment_history(patient_id)` | `handle_payment_history` | Si |

### Fase 2 — Pagos y Vouchers (7 tools)
| Tool | Handler | Read-only |
|------|---------|-----------|
| `register_payment(patient_id, amount, method, reference)` | `handle_register_payment` | No |
| `get_payment_info(patient_id)` | `handle_get_payment_info` | Si |
| `get_all_payments()` | `handle_all_payments` | Si |
| `delete_payment(payment_id)` | `handle_delete_payment` | No |
| `get_yape_pending()` | `handle_yape_pending` | Si |
| `search_yape_transactions(query)` | `handle_search_yape` | Si |
| `get_yape_dashboard()` | `handle_yape_dashboard` | Si |

### Fase 3 — Usuarios y Sesiones (9 tools)
| Tool | Handler | Read-only |
|------|---------|-----------|
| `create_user(name, role, email)` | `handle_create_user` | No |
| `update_user(id, username, email)` | `handle_update_user` | No |
| `toggle_user_status(user_id)` | `handle_toggle_user_status` | No |
| `delete_user(id)` | `handle_delete_user` | No |
| `assign_therapist(patient_id, therapist_ids)` | `handle_assign_therapist` | No |
| `reset_password(user_id)` | `handle_reset_password` | No |
| `create_appointment(patient_id, therapist_id, start, end)` | `handle_create_appointment` | No |
| `update_session(id, title, start, end, status)` | `handle_update_session` | No |
| `delete_session(id)` | `handle_delete_session` | No |

### Fase 4+ — Reportes, Gastos, Sedes (7 tools)
| Tool | Handler | Read-only |
|------|---------|-----------|
| `register_expense(category, amount, description)` | `handle_register_expense` | No |
| `get_expenses(start, end, category)` | `handle_get_expenses` | Si |
| `broadcast_message(subject, body, target)` | `handle_broadcast` | No |
| `get_weekly_summary(week_start)` | `handle_weekly_summary` | Si |
| `get_monthly_summary(year, month)` | `handle_monthly_summary` | Si |
| `generate_ai_report()` | `handle_generate_report` | Si |
| `get_dashboard_overview()` | `handle_dashboard_overview` | Si |

## Cambios en Frontend

### `llama.service.ts`
- Nuevo metodo: `sendAgentMessage(message, mode): Observable<LlamaResponse>`
- POST a `/llama/agent`

### `ai-chat.ts`
- `sendMessage()` decide `mode = fullScreen ? 'grande' : 'chiquito'`
- Envia `mode` en el payload

### `ai-chat.html`
- Sin cambios estructurales. Solo se actualiza el placeholder segun modo.

## Endpoint Nuevo

`POST /llama/agent`
- Request: `{ message: string, mode: 'chiquito' | 'grande' }`
- Response: `{ intent, response, action_chips, suggestions }`
- `csrf.exempt` + `@login_required`

## Migracion

1. Crear `agent_orchestrator.py` y `tools_registry.py`
2. Agregar endpoint `/llama/agent` en `llama_routes.py`
3. Actualizar `llama.service.ts` con `sendAgentMessage`
4. Actualizar `ai-chat.ts` con `mode`
5. Probar modo Chiquito: preguntar por paciente "Juan" → debe llamar `search_patients`
6. Probar modo Grande: "registra pago de Maria por S/200" → flujo ReAct completo
7. Mantener `/llama/chat/send` como respaldo

## No Incluye (fuera de alcance)

- No se refactoriza el backend de `enhanced_llm_service_v5.py` — solo se agrega el nuevo orquestador
- No se tocan los templates HTML del backend
- No se migran datos
- No se cambia la autenticacion
