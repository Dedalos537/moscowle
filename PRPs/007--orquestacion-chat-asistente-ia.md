# PRP: Orquestación del Chat del Asistente IA (MCP)

> **Version:** 1.0
> **Created:** 2026-10-04
> **Status:** Ready

---

## Goal

Reorquestar el chat del asistente (`/mcp/chat/stream` + los 2 frontends) para que:

1. **La tarjeta "Pensamiento y herramientas" muestre el pipeline real** (intención → tool → resultado → síntesis) y **siga visible después de responder**, con los chips de tool **dentro** de la tarjeta, no en la burbuja.
2. **La respuesta final se comporte como WhatsApp**: burbuja del usuario instantánea, burbuja del asistente limpia (solo texto final, sin prefijos "Evaluando…/Analizando…"), sin mensajes intermedios de "borrador".
3. **La detección de tools no dependa de listas FAQ/keywords hardcodeadas**: un índice de intenciones **generado a partir de `TOOL_REGISTRY`** (descripciones + params) + function-calling nativo del provider.
4. **El system prompt se genere desde las funciones** (catálogo por tool: qué hace, params, cuándo usarla), en una sola fuente para modo local y remoto.
5. **La FAQ se genera desde las funciones** (`source='generated'`), reemplazando el crecimiento manual/auto-propuesto, y solo acorta el camino en Telegram (el chat web NUNCA se salta la tool).

## Why

- **Evidencia de usuario (2026-10-04)**: (a) "en pensamiento no aparece nada" — solo se ve `Evaluando tu petición...`; (b) el chip de tool sale **fuera** de la tarjeta; (c) "el mensaje se va redactando" en vez de llegar como burbuja de WhatsApp; (d) pide detección correcta de tools sin depender del FAQ y un system prompt mejor.
- **Causa raíz UI (verificada en código)**:
  - `ai-chat.ts:564` — `clearThinking()` borra `thinkingLog` en **cada chunk**; `ai-chat.html:158` — el panel solo se renderiza `@if (loading)`, así que al `done` desaparece. El usuario nunca ve los pasos de tool.
  - `ai-chat.ts:565/577/588` — `updateLastAssistant(assistantText, streamToolCalls)` adjunta los tools a la **burbuja** (`ai-chat.html:136-155`), por eso se pintan "desde afuera".
  - `chat.ts:157-169` (página `app-ai-assistant-chat`) — `case 'thinking'` **escribe el texto de estado dentro del mensaje asistente** y los `chunk` se **concatenan** a ese mismo string → la respuesta final queda redactada con prefijos de estado. Este es exactamente el síntoma "se va redactando".
  - El backend solo emite 4 `thinking` sueltos (`mcp_routes.py:422, 493, 567, 647`) sin estructura de traza; el `done` no lleva traza, así que el frontend no tiene nada con qué reconstruirla.
- **Causa raíz de detección**: producción corre en modo local (`provider order: ['ollama']` en la VM). La detección mezcla BM25 (`_select_local_tools`, `mcp_service.py:586`, k=8), function-calling del router (`qwen2.5:1.5b`) y un **mapa hardcodeado** `_LOCAL_FORCE_TOOLS` (≈7 tools / 384 keywords escritas a mano en `mcp_service.py`) vía `_force_intent_tool`. Es frágil y hay que mantenerlo a mano.
- **FAQ actual**: `faq_service.match_faq` solo lo usa Telegram (`telegram_bot_service.py:386-393`) y el admin; las preguntas son manuales o auto-propuestas desde consultas sin respuesta (`faq_service.auto_propose_faq`), no derivadas de las funciones.

## What

- Contrato de eventos con **traza persistente** (`done.trace` + pasos con `kind`), compatible con el contrato actual (los eventos `thinking/chunk/tool_call/tool_result/chips/confirm/done/error` siguen existiendo).
- Índice de intenciones **generado** desde el registro de tools; `_LOCAL_FORCE_TOOLS` (hardcoded) se elimina.
- `build_system_prompt()` único (local/compacto y remoto) que imprime el catálogo de funciones permitidas por rol.
- `generate_faq_from_tools()` crea/actualiza entradas FAQ derivadas de las tools de lectura.
- Frontend: tarjeta con traza viva + chips de tool dentro + respuesta en burbuja limpia tipo WhatsApp, en **ambos** frontends (`ai-chat.ts` y `chat.ts`).

### Success Criteria

- [ ] Preguntar "cuántos terapeutas hay?" muestra en la tarjeta: paso de ruteo + `list_users` con args + resultado, y **al terminar la tarjeta queda visible (colapsada) con ese resumen**; la burbuja de respuesta contiene SOLO la respuesta.
- [ ] La burbuja del asistente jamás contiene "Evaluando tu petición...", "Analizando el resultado..." ni otros prefijos de estado (verificado en `chat.ts` y `ai-chat.ts`).
- [ ] `match_intent('cuántos terapeutas hay', tools)` devuelve `list_users` **sin** keywords hardcodeadas (índice generado desde el registro).
- [ ] El system prompt local incluye una línea por tool permitida del rol y NO incluye tools no permitidas.
- [ ] Existen ≥ 30 entradas FAQ con `source='generated'` derivadas del catálogo, sin duplicados por pregunta normalizada.
- [ ] `pytest tests/ -q` no baja del baseline (**25 failed / 348 passed**); `ruff check` sin errores nuevos en archivos tocados; `ng build` sin errores.
- [ ] Las 2 regresiones de `tests/test_ai_chat_regressions.py` siguen en verde (no duplicar respuesta; `ai-preview` sin CSRF).

---

## All Needed Context

### Project Stack

- **Backend**: Flask (Python 3.11 en VM), blueprint `admin_bp`/`mcp`, SSE streaming (eventlet, gunicorn).
- **DB**: MySQL 8 (VM-DB `192.168.122.20`), SQLite en tests (`tests/conftest.py`, `WTF_CSRF_ENABLED=False`).
- **LLM en producción**: `provider order: ['ollama']` → `local_mode=True` en `mcp_routes`. Modelos: router `qwen2.5:1.5b`, tactical `openbmb/minicpm5:4_K_M`, default `gemma2`, fallback `gemma3:4b` (`llm_client.py:28-31`). Cadena remota Groq→GLM→Gemini existe en `llm_client.py` para cuando se encienda el fallback.
- **Frontend**: Angular 20 (enforce standalone, `OnPush`), Tailwind 4; **sin** infraestructura de tests de frontend (no hay specs; validación = `ng build`).
- **Deploy**: push a `main` → workflow `deploy-ubuntu.yml` → `server_deploy.sh` en VM-APP; frontend separado (tar/cPanel).
- **Catálogo**: `TOOL_REGISTRY` con ~66 tools núcleo (`CORE_TOOL_NAMES`, `tools_registry.py:164`), decorator `@tool(name, description, parameters, category, roles)`, filtro `get_tools_for_mode(mode, user_role)`.

### Key Files (líneas exactas)

| Archivo | Qué vive ahí |
|---|---|
| `app/routes/mcp_routes.py:395-790` | endpoint `/mcp/chat/stream`, loop de 6 iteraciones, emisión de eventos |
| `app/routes/mcp_routes.py:422` | único `thinking` inicial ("Evaluando tu petición...") |
| `app/routes/mcp_routes.py:459-546` | rama confirmed_tool, smalltalk, det_tool, parseo `<function=...>` |
| `app/routes/mcp_routes.py:656,772` | guards anti-alucinación `_DATA_CLAIM_RE` / `_ACTION_CLAIM_RE` (MANTENER) |
| `app/services/mcp_service.py:46` `SYSTEM_PROMPTS` | prompt admin legacy (no usar, duplica personalidad) |
| `app/services/mcp_service.py:183 resolve_system_prompt` | BotConfig > PERSONALITY_PROMPT + bloque de acceso por rol |
| `app/services/mcp_service.py:586 _select_local_tools` | BM25 `ToolRetriever` k=8 + tool de fecha siempre presente |
| `app/services/mcp_service.py:610-943` | `_LOCAL_FORCE_TOOLS` (hardcoded, a eliminar) + `_force_intent_tool` |
| `app/services/mcp_service.py:989 _build_local_system_prompt` | prompt local compacto + entity resolver |
| `app/services/mcp_service.py:1021 _build_tool_prompt` | catálogo remoto de tools en texto |
| `app/services/personality_prompt.py` | `PERSONALITY_PROMPT` (116 líneas) y `LOCAL_BASE_PROMPT` (26 líneas) |
| `app/services/retrieval.py:209 ToolRetriever` | índice BM25 + sinónimos de tools |
| `app/services/faq_service.py` | `match_faq`, `auto_propose_faq`, `hourly_auto_grow` |
| `app/services/tools_registry.py:31/164/234` | registro, core names, `get_tools_for_mode` |
| `edysync/src/app/shared/components/ai-chat/ai-chat.ts:554-635` | `handleStreamEvent` (vista de las capturas) |
| `edysync/src/app/shared/components/ai-chat/ai-chat.html:158-186` | tarjeta "Pensamiento y herramientas" (`@if (loading)`) |
| `edysync/src/app/shared/components/ai-chat/ai-chat.html:136-155` | chips de tool dentro de la burbuja (fuera de la tarjeta) |
| `edysync/src/app/features/ai-assistant/pages/chat/chat.ts:155-169` | **`thinking` escribe dentro de la burbuja** (bug "se va redactando") |
| `edysync/src/app/core/layout/admin-layout/admin-layout.html:31` | `<app-ai-chat>` (panel visible en capturas) |

### Contrato de eventos SSE actual vs propuesto

```
actual                                  propuesto (aditivo, retrocompatible)
thinking {content}                      thinking {content, step:{kind, n}}   # paso de traza
chunk    {content}                      chunk    {content}                   # solo texto final
text     {content}                      text     {content}                   # igual (OJO: se concatena en el front)
tool_call  {name,args}                  tool_call  {name,args}               # igual (paso de traza)
tool_result {name,result,success}       tool_result {name,result,success}     # igual (paso de traza)
chips / confirm / error                 idem
done {tool_calls}                       done {tool_calls, trace:[Step]}      # trace = traza completa
```
`Step = {kind: 'route'|'tool'|'result'|'synth'|'guard', text: str, tool?: str, ok?: bool}`.
Regla de oro: **los `chunk` solo llevan texto final**; ningún texto de estado puede ir en `chunk`/`text`.

### Validation Commands

```bash
# Lint (solo los archivos tocados; la deuda global es preexistente)
venv/bin/ruff check app/routes/mcp_routes.py app/services/mcp_service.py app/services/prompt_builder.py app/services/tool_intents.py app/services/faq_service.py
venv/bin/ruff format --check <archivos tocados>

# Tests (baseline: 25 failed / 348 passed)
venv/bin/python -m pytest tests/ -q --tb=no --no-cov
venv/bin/python -m pytest tests/test_mcp_orchestration.py tests/test_ai_chat_regressions.py -q --no-cov

# Sintaxis
venv/bin/python -c "import py_compile; py_compile.compile('app/routes/mcp_routes.py', doraise=True)"

# Frontend
cd edysync && npx ng build

# Smoke en VM (tras deploy): rev + JSON del stream
```

### Pre-existing Issues (don't reintroduce)

- **25 tests fallando** (baseline de login/therapist routes) — no tocar.
- Deuda ruff global (~280 errores) en archivos legacy; **no** aumentarla en archivos tocados (`per-file-ignores` en `pyproject.toml` es el patrón aceptado si algo es inseparable).
- `chat_routes.py` ya tiene `per-file-ignores` (PLC0415/E501/PLW2901/S603).
- NO volver a emitir `full_content` como `text` tras los `chunk` (bug de respuesta doble ya corregido; regresión cubierta por `tests/test_ai_chat_regressions.py`).
- `WTF_CSRF_ENABLED` en tests está en False; los tests de rutas usan JWT (`create_access_token(identity=str(user.id))`).

### Code Conventions

- Python: snake_case, servicios en `app/services/`, rutas en `app/routes/`, sin `print`, logging con `logger = logging.getLogger('app.*')`.
- Tests: fixtures `app`, `client`, `session`, `test_user` de `tests/conftest.py`; patrón de admin: crear `User(role='admin')` + JWT Bearer.
- Angular: standalone + `OnPush`, `markForCheck()` tras mutaciones, templates con `@if/@for` (Angular 20), estilos Tailwind + clases BEM del componente (`think-panel__*`).
- Commits: `<type>(<scope>): <desc>` en inglés/español del repo, validado por `scripts/validate-commit.sh`; **solo commitear cuando el usuario lo pida**.

---

## Implementation Blueprint

### Fase A — Traza de eventos en backend
```yaml
Task A1: Crear app/services/mcp_trace.py
  - Step dataclass(kind, text, tool, ok) + TraceBuilder.add()/as_list()
  - helpers: step_route(text), step_tool(name,args), step_result(name,ok,summary), step_guard(text)
Task A2: mcp_routes.py — acumular trace y emitir step en cada thinking/tool
  - MODIFY: app/routes/mcp_routes.py (generate() de /mcp/chat/stream)
  - Sustituir los 4 yield de "thinking" sueltos por yield con step adjunto
  - Inyectar trace en el done final (línea 782) y en el done de confirmación (603/724)
  - Mantener payload legacy de thinking (content) intacto
Task A3: Regresión de contrato
  - ADD: tests/test_mcp_orchestration.py::test_stream_emits_trace_and_steps
    monkeypatch llm_chat_stream (chunks) + execute_tool (dict) →
    assert orden: thinking(step=route) → tool_call → tool_result → chunk* → done.con trace
```

### Fase B — Detección de tools generada (elimina FAQ/keywords hardcodeadas)
```yaml
Task B1: Crear app/services/tool_intents.py
  - generate_phrases(tool): por cada tool de lectura, frases ES derivadas de
    description + name + params (plantillas: "cuántas X hay", "lista de X",
    "ver/detalle de X", "X de hoy/mes", "resumen de X" + params como slot)
  - build_intent_index(TOOL_REGISTRY, allowed) -> [(phrases, tool, arg_spec)]
  - match_intent(message, allowed_tools) -> (tool, args) | None
    usando extractores GENÉRICOS ya existentes: _extract_date_arg,
    _extract_month_arg, inferencia de role/ids (reubicar en tool_intents)
Task B2: mcp_service.py — _force_intent_tool delega a match_intent
  - ELIMINAR: _LOCAL_FORCE_TOOLS (~330 líneas hardcodeadas, mcp_service.py:610-943)
  - Mantener la firma de _force_intent_tool (la llama mcp_routes) para no tocar el flujo
Task B3: Tests
  - test_intent_index_covers_all_read_tools: cada tool CORE de categoría read
    genera ≥1 frase y match_intent la resuelve en mensaje canónico
  - test_canonical_queries: "cuántos terapeutas hay"→list_users con role=terapista;
    "sesiones de hoy"→get_sessions_day con fecha; "cuántas sedes"→list_sedes
```

### Fase C — System prompt generado desde las funciones
```yaml
Task C1: Crear app/services/prompt_builder.py
  - build_system_prompt(role, user_id, mode, tools, compact=False)
    secciones: IDENTIDAD (Diego/centro/Lima) · REGLAS (datos exactos, no inventar,
    confirmación en escritura, formato <function=...>, fecha del contexto) ·
    CATÁLOGO (generado: "- {name}: {1-linea de description} | params | cuándo usarla",
    agrupado por category read/write/report) · ACCESO (bloque de rol, existe:
    get_role_access_block)
  - compact=True (modo local) → catálogo en 1 línea por tool, sin flows largos,
    presupuesto ~1200 tokens (hoy LOCAL_BASE_PROMPT es lo que intenta ser a mano)
Task C2: Cablear
  - mcp_service.resolve_system_prompt → build_system_prompt(..., compact=False)
  - mcp_service._build_local_system_prompt → build_system_prompt(..., compact=True)
    + entity resolver (se mantiene)
  - _build_tool_prompt deja de existir como fuente separada (el catálogo vive en C1)
  - PERSONALITY_PROMPT queda como fallback si BotConfig.system_prompt está vacío
    (override del admin gana; documentar en el docstring)
Task C3: Tests
  - test_prompt_lists_only_allowed_tools (rol terapista no ve delete_user/logs)
  - test_prompt_local_is_compact (líneas/tokens < umbral y contiene las tools del turno)
  - test_prompt_mentions_date_context (get_current_date_context inyectado en la ruta)
```

### Fase D — FAQ generada desde las funciones
```yaml
Task D1: faq_service.generate_faq_from_tools()
  - Para cada tool de lectura con description clara: 1-3 preguntas plantilla ES
    ("¿Cuántos pacientes hay?", "Lista de usuarios", "¿Qué sesiones hay hoy?")
    + respuesta plantilla que EXPlica qué tool resuelve y qué devolverá
  - Dedup por pregunta normalizada (_normalize existente); source='generated',
    status='active'; reutiliza Faq model (question/answer/category/keywords/source)
Task D2: Cableado
  - Invocar en hourly_auto_grow (tasks.py:549) con cap (máx 1 por corrida)
  - Telegram mantiene match_faq (ahora alimentado por generadas)
  - VERIFICAR (test) que mcp_routes NUNCA consulta faq_service → el chat web
    responde siempre con tools (hoy ya es así; el test lo protege)
Task D3: Tests
  - test_generated_faq_has_no_duplicates + test_webchat_does_not_use_faq
```

### Fase E — Frontend: tarjeta con traza + burbuja limpia (2 componentes)
```yaml
Task E1: ai-chat.ts — traza persistente
  - Mantener thinkingLog al llegar chunk (clearThinking solo limpia thinkingText);
    limpiar TODO al enviar un mensaje nuevo (sendMessage/streamToServer ya lo hacen)
  - Capturar event.trace del done → this.messages[last].trace = trace
  - streamToolCalls NO se adjunta a la buruja: updateLastAssistant(recibe solo texto)
  - Panel: visible mientras loading (traza viva) y para el último msg asistente
    con trace (colapsado por defecto, resumen "· N herramientas · M pasos")
Task E2: ai-chat.html — chips de tool DENTRO de la tarjeta
  - Mover el markup .tool-calls (líneas 136-155) al body de think-panel
  - think-panel__body: pasos de traza + tool rows (icono, nombre, badge OK,
    args resumidos, resultado ≤200 chars)
  - La burbuja del asistente renderiza SOLO msg.content (sin toolCalls)
  - Estado vacío del panel: nunca "Pensando..." si hay traza
Task E3: chat.ts — dejar de redactar dentro de la burbuja
  - case 'thinking' NO toca messages: acumula en this.trace (o msg.trace en vivo)
  - tool_call/tool_result se adjuntan al msg asistente (toolCalls) en vez de
    crear messages con role='tool_call' (los estilos existentes de burbuja siguen)
  - chunk solo appendea texto final
Task E4: ng build + smoke visual (LAN /app/) con agent-browser si hay deploy
```

### Fase F — Validación y entrega
```yaml
Task F1: suite completa + ruff + ng build (comparar contra baseline)
Task F2: pedir commit+push+deploy y verificar en VM
  - curl del stream con JWT: ver trace en done, sin prefijos en chunk
```

---

## Validation Loop

### Level 1: Syntax & Style
```bash
venv/bin/ruff check app/routes/mcp_routes.py app/services/mcp_service.py app/services/tool_intents.py app/services/prompt_builder.py app/services/mcp_trace.py app/services/faq_service.py
venv/bin/python -c "import py_compile; py_compile.compile('app/routes/mcp_routes.py', doraise=True)"
cd edysync && npx ng build
```

### Level 2: Tests
```bash
venv/bin/python -m pytest tests/test_mcp_orchestration.py tests/test_ai_chat_regressions.py -q --no-cov   # nuevos + regresiones
venv/bin/python -m pytest tests/ -q --tb=no --no-cov   # no bajar de 25 failed / 348 passed
```

### Level 3: Smoke (tras deploy)
```bash
# en VM: provider order y rev
# stream real: SSE con JWT debe mostrar step en thinking y trace en done
```

---

## Anti-Patterns to Avoid

- ❌ Emitir estado de progreso dentro de `chunk`/`text` (los frontends lo concatenan a la respuesta).
- ❌ Borrar `thinkingLog` al primer chunk (es el bug reportado).
- ❌ Añadir keywords nuevas a mano: el índice de intenciones se **genera** del registro.
- ❌ Saltear el guard `_DATA_CLAIM_RE`/`_ACTION_CLAIM_RE` (son la red anti-alucinación).
- ❌ Romper el contrato legacy de eventos (2 frontends + tests de regresión dependen de él).
- ❌ Dejar que FAQ corte el chat web (solo Telegram).
- ❌ Reintroducir deuda ruff en archivos tocados ni tocar los 25 tests fallidos preexistentes.
- ❌ Commit/push sin pedirlo explícitamente.
