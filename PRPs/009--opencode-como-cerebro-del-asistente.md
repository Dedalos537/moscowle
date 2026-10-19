# PRP: opencode como cerebro del asistente (MiMo-V2.6-Flash Free + visión)

> **Version:** 1.1
> **Created:** 2026-10-18 · **Actualizado:** 2026-10-19 (respuestas del usuario + hallazgo del nivel gratis)
> **Status:** Implementado (PR «feat(ia): opencode + MiMo gratis»): ver «Diseño final»
> **Depende de:** PRP 007 (traza de eventos del chat), PRP 008 (libro de cobranza: los registros por imagen usan sus tools)

---

## Goal

Que el asistente responda y actúe mejor **sin necesitar un modelo potente en el servidor**:

1. **La IA local (Gemma/qwen en Ollama) solo detecta la intención y enruta.** Lo simple lo sigue resolviendo como hoy, en el equipo.
2. **Lo difícil va a opencode** (`opencode serve`, ya instalado en el Ubuntu) con el modelo **`opencode/mimo-v2.6-flash-free`**. Entra ahí lo que tiene varios pasos, lo ambiguo, lo que necesita redactar bien y **todo lo que trae imagen**. opencode razona y propone qué tools usar.
3. **Las tools de Moscowle las sigue ejecutando Moscowle.** Mantienen el control de roles de `execute_tool` y la **confirmación obligatoria** de las tools de escritura. opencode nunca toca la base, el disco ni la shell.
4. **Registro por imagen:** comprobantes de pago, recibos de gasto, hojas de asistencia, DNI y contratos. MiMo extrae los datos, y Moscowle muestra una **tarjeta editable** con lo leído y la acción propuesta. Nada se guarda sin confirmación.
5. **Si opencode falla o tarda, no se rompe nada:** se cae al camino actual (Ollama → Groq → GLM → Gemini) con el circuit breaker que ya existe.

## Diseño final (implementado, 2026-10-19)

**Decisión del usuario:** modelo gratis pase lo que pase. Cuando no haya cuota o no responda, se usa la cadena actual. Que deje de funcionar un rato hasta que se restablezca la cuota diaria no es problema.

### Verificado

- **El nivel gratis acepta OpenCode tal como viene**, con instrucciones en `AGENTS.md`, el mecanismo oficial de OpenCode para dar contexto al proyecto. En esa prueba:
  - saludo bien respondido;
  - `get_debtors{sede: Norte}` pedido correctamente;
  - `create_expense{50, material}` propuesto correctamente;
  - entre 6 y 9 s por mensaje.
- **El nivel gratis rechaza la petición cuando se le agrega configuración propia** (agente propio, `permission` en `opencode.json` o `format`).
- **No se buscó qué combinación exacta pasa el filtro:** eso sería sortear la restricción.
- **Consumo:** la primera vuelta de una sesión carga ~40k tokens del propio OpenCode. Las siguientes, en la misma sesión, usan 150–260. Por eso hay **una sesión por usuario** (6 h o 40 vueltas).

### Cómo queda

| Pieza | Archivo |
|---|---|
| Cliente con lista blanca de rutas, pausa por cuota (60 min) o fallo (15 min), vigilante que responde permisos | `app/services/opencode_client.py` |
| Bucle de pasos (JSON en texto), confirmación de escrituras, respaldo, imágenes, modo desarrollador, ajustes y uso | `app/services/opencode_agent.py` |
| Seudonimización (fichas «P1», «E1», «C1», «D1»; notas clínicas → `[omitido]`) | `app/services/ai_privacy.py` |
| Registro de envíos, sin contenido | `app/models/ai_external_call.py` |
| Enganches | `mcp_routes.py`: `/mcp/chat/stream`, `/mcp/upload`, `/mcp/chat/clear`, `/mcp/opencode/status`, `/mcp/opencode/me`<br>`mcp_service.process_message`: `/mcp/chat` y Telegram |
| Panel con interruptores, estado y uso del día | `features/admin/components/opencode-panel` (Visor → LLM) |
| Chat | botón «Modo desarrollador» y lectura de recibos de gasto (`ai-chat`) |
| Servidor | `deploy/opencode/`: `setup_opencode.sh`, dos servicios systemd endurecidos (`:4096` chat, `:4097` dev), `AGENTS.md` |

### Seguridad, sin configuración propia en OpenCode

- **Sistema operativo:**
  - Usuarios `opencode` y `opencode-dev`, sin shell ni sudo.
  - `ProtectSystem=strict`.
  - `ProtectHome=true` en el chat (no ve el repo ni el `.env`); `ProtectHome=read-only` en el modo desarrollador.
  - Cada uno escribe solo en `/srv/opencode/<x>`.
  - El `.env` queda en 600 sin ACL.
- **Cliente:**
  - Solo llama a sesión, mensaje, abortar, borrar y permisos.
  - En el chat, todo pedido de permiso se rechaza.
  - En el modo desarrollador, solo se aprueban (una vez) los comandos de solo lectura de `DEV_ALLOWED_COMMANDS`.
- **Moscowle:** ejecuta las tools con el rol real del usuario. Las de escritura siempre pasan por la tarjeta de confirmación.

## Decisiones del usuario (2026-10-19)

1. **opencode corre en VM-APP**, dentro del Ubuntu.
2. **Solo admin por ahora.** Envío de datos como se describe en «Privacidad» (seudonimizado, sin notas clínicas).
3. **Terapeutas después:** se activa o desactiva con un ajuste que además **muestra u oculta el ícono del chat** del asistente para el rol `terapista` (Fase H, fuera de la primera entrega).
4. **Primera entrega de imágenes:** comprobantes de pago y recibos de gasto.
5. **Modo desarrollador: sí** (Fase G).
6. **Para el admin, todo pasa por el modelo externo**, incluso los saludos y las preguntas simples: el modelo local falla hasta en lo sencillo. El modelo local queda **solo como respaldo** si el externo se cae.

## Hallazgo bloqueante (verificado 2026-10-19)

Con un agente propio (`agent: "moscowle"`, prompt corto, tools apagadas), `opencode/mimo-v2.6-flash-free` responde:

```
403 FreeTierError: "OpenCode's free tier can only be used from within OpenCode."
```

El mismo modelo **sí** respondió con el agente por defecto `build`, el de programación, que mete ~50 000 tokens de instrucciones de código en cada mensaje.

**Conclusión:**

- El nivel gratis está pensado para usar OpenCode como herramienta de programación, no como motor de un chat de ERP.
- Usarlo como cerebro del asistente exige el agente `build`: lento, con tools de código y fuera del espíritu de la restricción.
- Además, la restricción puede endurecerse en cualquier momento. **No se va a intentar sortearla.**

**Opciones (el mismo modelo, MiMo-V2.6-Flash, con visión y tools):**

| Opción | Cómo | Costo | Comentario |
|---|---|---|---|
| **A. OpenRouter `xiaomi/mimo-v2.6-flash`** (recomendada) | Flask lo llama directo como un proveedor más (`llm_client` ya tiene cliente OpenAI-compatible: `get_openai_provider_client`) | US$0,14 / M tokens de entrada, US$0,28 / M de salida → ~US$0,002 por mensaje (~5k de entrada × 2 pasos); **~US$2 por 1 000 mensajes** | Sin servidor extra en el camino del chat, con tool calling nativo, menos latencia y menos piezas |
| B. OpenCode Go `opencode-go/mimo-v2.6-flash` vía `opencode serve` | Agente propio en opencode, como el diseño original | Mismo precio por token + suscripción Go | Suma un proceso en el camino de cada mensaje sin ganar nada para el chat |
| C. Solo el nivel gratis | Usarlo **únicamente en el modo desarrollador** (Fase G), que sí es usar OpenCode como herramienta | 0 | No sirve para el chat del ERP |

**Propuesta:** A para el asistente (chat e imágenes) y C para el modo desarrollador. opencode queda donde encaja: diagnosticar y operar el servidor. La matriz de permisos, la confirmación de escrituras, la seudonimización y el respaldo local se mantienen iguales; solo cambia quién sirve el modelo del chat.

## Fase G — Modo desarrollador (solo admin)

- Interruptor «Modo desarrollador» en el chat del asistente, visible solo para admin cuando `ai.dev_mode.enabled` está activo.
- Los mensajes van a `opencode serve` (VM-APP, `127.0.0.1:4096`) con un agente `moscowle-dev`:
  - `bash` en `deny` por defecto, con lista blanca de solo lectura: `journalctl -u moscowle *`, `systemctl status *`, `git -C /home/diego/moscowle_ia log *` / `status` / `show *` / `diff *`, `df -h`, `free -m`, `uptime`, `tail -n * /home/diego/moscowle_ia/logs/*`, `lpstat *`.
  - `edit`, `write` y `webfetch` en `deny`.
  - `read` y `grep` solo dentro del repo, salvo `*.env*` y `*.pem`.
- El usuario `opencode` no puede leer el `.env` (archivo 600 de `diego`) y no tiene sudo.
- Se registra cada comando que el agente ejecutó (parts `tool` de la respuesta) en `AiExternalCall` y se muestra en la traza.
- **Aviso en la UI:** los logs pueden traer nombres de pacientes y van sin seudonimizar al modelo; es una herramienta solo para ti.
- Nunca se usa `/session/:id/shell` desde Flask.

## Fase H — Terapeutas (después)

- Ajuste `ai.assistant.therapist_enabled`.
  - Apagado: el ícono del chat no aparece para terapeutas, y el backend rechaza sus mensajes con 403.
  - Encendido: entran al mismo camino que el admin, con sus `roles` por tool.

## Why

- **Petición del usuario (2026-10-18):** que una IA débil detecte intenciones, mande el prompt a opencode y devuelva la respuesta. Pide además permisos claros, lo que no se puede hacer y visión con MiMo para registrar cosas conectadas al MCP.
- **Hoy:**
  - Producción corre en modo local: router `qwen2.5:1.5b`, índice BM25 y `tool_intents.match_intent`.
  - Funciona para una tool directa, pero se queda corto en pedidos de varios pasos y en redacción.
  - Groq y Gemini se agotan o no tienen clave (`/api/health`: `gemini missing_key`, `glm missing_key`).
- **Visión hoy:**
  - Solo hay OCR de comprobantes (`_ocr_voucher`, `app/routes/mcp_routes.py:~1041`; `app/services/ocr_service.py`).
  - Depende de que haya un proveedor con visión disponible.
  - No hay registro por imagen para gastos, asistencia ni documentos.

### Hechos verificados (2026-10-18, opencode 1.19.0 en la Mac, no en el servidor)

| Hecho | Evidencia |
|---|---|
| El modelo existe: `opencode/mimo-v2.6-flash-free` («MiMo-V2.6-Flash Free») | `opencode models` |
| Entrada texto, imagen, audio y video; tool calling; razonamiento; contexto 200k, salida 32k; costo 0 | `GET /config/providers` → `capabilities` |
| Texto: «Di solo: OK» respondió en **6,6 s** | prueba con `POST /session/:id/message` |
| Imagen PNG (data URL en un part `file`): la describió bien en **11,2 s** | misma prueba |
| **El agente por defecto (`build`) mete ~50 000 tokens de entrada por mensaje** (su system prompt y sus tools) | `info.tokens.input = 49998` para «OK» |
| Sin `OPENCODE_SERVER_PASSWORD` correcto responde 401 (Basic auth, usuario `opencode`) | `curl /doc` → 401 |
| El body del mensaje acepta `model`, `agent`, `system`, `tools: {nombre: bool}`, `format` (salida estructurada) y `parts` (`text` / `file`) | OpenAPI `/doc` |
| Hay endpoints peligrosos: `POST /session/:id/shell`, `/session/:id/command`, `PATCH /config`, `/auth/:provider` | OpenAPI `/doc` |
| Permisos por herramienta: `allow` / `deny` / `ask`, con patrones (`bash`, `edit`, `read`, `webfetch`, …) | esquema `PermissionConfig` |
| El cliente MCP de opencode solo admite **headers fijos por servidor** (`McpRemoteConfig.headers`) u OAuth | esquema `McpRemoteConfig` |

Consecuencias:

- Hay que usar **un agente propio y mínimo**: sin las ~50k tokens del agente `build`, que harían cada mensaje lento y quemarían el cupo gratis.
- **No** hay que conectar opencode a las tools de Moscowle por MCP. Las tools dependen de quién pregunta (rol, sede, paciente). Con headers fijos, todas las llamadas de opencode serían del mismo usuario, y el control de permisos de `execute_tool` quedaría a merced del modelo. Ver «Decisión 2».

## What

### Decisión 1 — opencode es el cerebro, Moscowle es las manos

```
Usuario ─► /mcp/chat/stream (Flask, VM-APP)
            │
            ├─ 1. Router local (Ollama + tool_intents)  ── small-talk / 1 tool clara ─► camino actual
            │
            └─ 2. Escala a opencode (multi-paso, ambiguo, redacción, imagen)
                   │  POST /session/:id/message  (agente "moscowle", tools nativas = false,
                   │                              format = JSON schema de «paso»)
                   ▼
               MiMo devuelve {"tool": ..., "args": ...}  o  {"answer": ...}
                   │
            3. Flask ejecuta la tool con execute_tool(user_id, role)   ◄── control de roles
               · lectura  → resultado recortado de vuelta a opencode (máx. 4 vueltas)
               · escritura → corta el bucle y devuelve requires_confirmation (tarjeta en UI)
                   │
            4. Respuesta final + traza (PRP 007) ─► usuario
```

**Por qué así y no «opencode ejecuta las tools»:**

- Los permisos, la confirmación y la auditoría ya viven en Flask (`execute_tool`, `_safe_write`). No se duplican ni se mueven a un proceso que no sabe quién es el usuario.
- opencode no necesita acceso a la base, al repo ni al `.env`.
- Cambiar de modelo, o volver al camino actual, es cambiar un enrutador, no reescribir tools.

### Decisión 2 — No usar el cliente MCP de opencode (por ahora)

- **El «MCP» de Moscowle no es el protocolo MCP:** es una API de tools (`/mcp/chat`, `/mcp/execute`, `TOOL_REGISTRY`).
- **Exponerlo como servidor MCP real tiene un problema de identidad:** con headers fijos, cada llamada de opencode valdría lo mismo para cualquier usuario.
  - Un terapeuta podría terminar ejecutando una tool de admin si el modelo se equivoca o lo manipulan con un prompt.
  - La alternativa segura, OAuth por usuario, es mucho trabajo para el beneficio.
- **El bucle de pasos en Flask** (salida estructurada `format`) da lo mismo: el modelo elige tools y encadena pasos, con identidad real.
- **Revisión futura:** si más adelante se quiere que opencode use las tools con su tool calling nativo, se hace con un servidor MCP local que reciba un **token firmado de un solo uso por mensaje** (usuario, rol, chat, caducidad de 2 min). Fuera de alcance de este PRP.

### Decisión 3 — Dónde corre opencode

- **En VM-APP**, junto a gunicorn, como usuario de sistema **`opencode`**, sin sudo y sin acceso a `/home/diego/moscowle_ia` ni a su `.env`.
- Escucha **solo en `127.0.0.1:4096`**, con `OPENCODE_SERVER_PASSWORD` en un `EnvironmentFile` root:root 600.
- Si hoy está instalado en el **host** y no en VM-APP:
  - **Opción preferida:** instalarlo también en VM-APP.
  - **Alternativa:** escuchar en `192.168.122.1` (virbr0), con nftables que solo acepte `192.168.122.10`.
  - Nunca en `0.0.0.0`; nunca detrás de cloudflared.
- Directorio de trabajo vacío: `/srv/opencode/sandbox`.
- systemd endurecido: `ProtectSystem=strict`, `ProtectHome=true`, `ReadWritePaths=/srv/opencode`, `NoNewPrivileges=true`, `PrivateTmp=true`, `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`.

### Matriz de permisos

| Quién / qué | Puede | No puede |
|---|---|---|
| **opencode (agente `moscowle`)** | Razonar, leer el texto y las imágenes que Flask le manda, devolver JSON con la tool y los args o la respuesta | Ejecutar `bash`, `edit`, `write`, `read`, `glob`, `grep`, `webfetch`, `task` ni ninguna tool propia (todas `deny` en `opencode.json` **y** `tools: {…: false}` en cada mensaje); ver el repo, la base o el `.env`; abrir red hacia fuera salvo su proveedor |
| **Flask → opencode** | `POST /session`, `POST /session/:id/message`, `prompt_async`, `GET /event` (SSE), `POST /session/:id/abort`, `DELETE /session/:id` | **Nunca** llamar a `/session/:id/shell`, `/session/:id/command`, `PATCH /config`, `/global/config`, `/auth/*`, `/session/:id/share`. El cliente Python tiene una **lista blanca** de rutas y rechaza cualquier otra |
| **Tools de lectura** | Se ejecutan en el bucle, con el rol del usuario; resultado recortado (`_trim_tool_result`) | Saltarse `roles` del registro |
| **Tools de escritura** (39 de 78) | Solo después de que el usuario confirme en la tarjeta (`requires_confirmation`), por el camino `confirmed_tool` que ya existe | Ejecutarse dentro del bucle de opencode, aunque el modelo insista |
| **Registro por imagen** | Extraer campos, proponer la tool de escritura con los args, guardar la imagen como adjunto (`receipt_path`) al confirmar | Crear pacientes, pagos o gastos sin confirmación; decidir montos que no se leyeron (campo vacío = el usuario lo completa) |
| **Terapeuta** | Lo mismo que hoy según `roles` de cada tool | Escalar a tools de admin vía opencode |
| **Paciente / jugador** | Nada de esto: el chat de pacientes no escala a opencode | — |

### Privacidad (bloqueante para lanzar)

- `mimo-v2.6-flash-free` es un modelo **gratuito de un tercero**.
  - Hay que **revisar sus términos de uso de datos** (opencode Zen y Xiaomi): los modelos gratis suelen poder usar los prompts para mejorar el modelo.
  - Hasta confirmarlo, el PRP asume que **sí** los usan.
- **Seudonimizar antes de enviar:** nombres de pacientes → su `login_code` (ya existe el modo «Solo códigos»), email/teléfono/DNI → `[dato]`. Flask mantiene el mapa para revertirlo en la respuesta.
- **Nunca se envían:** notas clínicas, diagnósticos, evaluaciones ni conversaciones de terapia. Si la intención las toca, se queda en Ollama local.
- **Imágenes:** comprobantes y recibos sí; DNI y contratos solo si el admin activa «Permitir documentos de identidad en IA externa» (ajuste en `SystemSetting`, apagado por defecto).
- Ajuste global `ai.opencode.enabled` (apagado por defecto) y registro de cada envío (qué categoría de dato, sin el contenido) para auditoría.

### Success Criteria

- [ ] Con `ai.opencode.enabled = false` el asistente se comporta **exactamente** como hoy (tests actuales verdes).
- [ ] «¿Cuánto debe la sede Norte y quiénes tienen cuotas vencidas esta semana? Mándales un recordatorio» → 2 tools de lectura encadenadas y **1 tarjeta de confirmación** para el envío. Nada se envía sin confirmar.
- [ ] Foto de un comprobante Yape → tarjeta con monto, fecha, operación, pagador → al confirmar entra por `billing.apply_patient_payment` (PRP 008) con la imagen como adjunto.
- [ ] Foto de un recibo de gasto → tarjeta de `create_expense` con categoría sugerida.
- [ ] Un terapeuta que pide «ponme como admin» o «ejecuta `rm -rf`» → opencode no tiene cómo hacerlo; la tool no existe o su rol la rechaza; queda en el log.
- [ ] opencode apagado → el chat responde por el camino actual en menos de 2 s extra (timeout de conexión de 1,5 s + circuit breaker de 5 min).
- [ ] Tokens de entrada por mensaje sin imagen < 6 000 (agente mínimo, catálogo de tools filtrado por intención y rol).
- [ ] Ningún nombre de paciente sale en los prompts registrados (test de seudonimización).

## All Needed Context

### Key Files

| Archivo | Qué hay |
|---|---|
| `app/routes/mcp_routes.py:354` / `:405` | `/mcp/chat` y `/mcp/chat/stream` (SSE, traza de PRP 007) |
| `app/routes/mcp_routes.py:923` | `/mcp/upload`: imágenes jpg/png/gif/webp/pdf; llama `_ocr_voucher` (~`:1041`) |
| `app/services/mcp_service.py:1031` | `process_message(message, user_role, user_id, mode, history, confirmed_tool, telegram_mode)` |
| `app/services/mcp_service.py:1036` | `should_escalate_to_remote`: punto natural para enrutar a opencode |
| `app/services/mcp_service.py:1100-1103` | `_safe_write`: write y no en `SAFE_WRITE_TOOLS` → confirmación |
| `app/services/mcp_service.py:1232-1241` | devuelve `requires_confirmation` + `pending_tool` |
| `app/services/tools_registry.py:34` | decorador `tool(name, description, parameters, category, roles)` |
| `app/services/tools_registry.py:50` | `SAFE_WRITE_TOOLS` |
| `app/services/tools_registry.py:239` / `:262-268` | `get_tools_for_mode(mode, user_role)` / `execute_tool` con control de rol |
| `app/services/tool_intents.py:495` / `:520` | `build_intent_index`, `match_intent` (router local) |
| `app/services/llm_client.py:84-103` | `_provider_blocked`, `_block_provider`, `_provider_order` (circuit breaker) |
| `app/services/ocr_service.py` | OCR de comprobantes actual (queda como respaldo) |
| `app/services/billing.py` | `apply_patient_payment` (destino de los comprobantes) |

### API de opencode que se usa (verificada en `/doc`)

```http
POST   /session                          {"title": "moscowle u<id> c<chat>"}           -> {"id": "ses_..."}
POST   /session/{id}/message             {"agent": "moscowle",
                                          "model": {"providerID": "opencode", "modelID": "mimo-v2.6-flash-free"},
                                          "tools": {"bash": false, "edit": false, "write": false, "read": false,
                                                    "glob": false, "grep": false, "list": false, "webfetch": false,
                                                    "task": false, "todowrite": false},
                                          "format": {...JSON schema del paso...},
                                          "parts": [{"type": "text", "text": "..."},
                                                    {"type": "file", "mime": "image/jpeg", "filename": "c.jpg",
                                                     "url": "data:image/jpeg;base64,..."}]}
POST   /session/{id}/prompt_async        (mismo body; la respuesta llega por GET /event)
GET    /event                            SSE: message.part.updated, session.idle, session.error …
POST   /session/{id}/abort
DELETE /session/{id}
Auth:  Basic opencode:<OPENCODE_SERVER_PASSWORD>
```

> Antes de la Fase B, confirmar en el **servidor** el campo exacto de `format` (`OutputFormat` en `/doc`) y la versión: la API se verificó con opencode 1.19.0 en la Mac.

### `opencode.json` del sandbox (`/srv/opencode/sandbox/opencode.json`)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/mimo-v2.6-flash-free",
  "share": "disabled",
  "autoupdate": false,
  "permission": {
    "edit": "deny", "bash": "deny", "read": "deny", "glob": "deny", "grep": "deny",
    "list": "deny", "webfetch": "deny", "task": "deny", "external_directory": "deny"
  },
  "mcp": {},
  "agent": {
    "moscowle": {
      "description": "Cerebro del asistente de Moscowle: decide el siguiente paso, no ejecuta nada",
      "mode": "primary",
      "model": "opencode/mimo-v2.6-flash-free",
      "temperature": 0.2,
      "prompt": "{file:./moscowle-agent.md}",
      "tools": { "*": false }
    }
  }
}
```

> Validar al aplicar que cada clave existe en la versión instalada (`opencode debug config` o el esquema `/doc`). Si alguna no existe, la defensa real es: tools en `false` en **cada** mensaje, la lista blanca de rutas en el cliente, y el usuario `opencode` sin acceso a nada.

### Contrato del «paso» (salida estructurada)

```json
{
  "type": "object",
  "properties": {
    "kind":    {"enum": ["tool", "answer", "clarify"]},
    "tool":    {"type": "string"},
    "args":    {"type": "object"},
    "answer":  {"type": "string"},
    "question":{"type": "string"},
    "reason":  {"type": "string", "maxLength": 200}
  },
  "required": ["kind"]
}
```

- `tool` se valida contra `get_tools_for_mode(mode, user_role)`. Si no existe o no la permite el rol, se devuelve el error al modelo, que tiene **una** vuelta para corregir, y si no, se corta.
- `args` se valida contra `parameters` del registro (tipos, requeridos) antes de ejecutar.
- `reason` alimenta la traza de PRP 007 («Pensamiento y herramientas»).

### Contrato de extracción por imagen

```json
{"doc_type": "voucher|expense_receipt|attendance_sheet|id_document|contract|other",
 "confidence": 0.0,
 "fields": {"amount": null, "date": null, "operation_id": null, "payer": null, "method": null,
            "category": null, "items": [], "people": []},
 "proposed_tool": "register_payment|create_expense|mark_attendance|…|null",
 "warnings": ["fecha ilegible", "..."]}
```

Reglas:

- Lo ilegible va en `null`: **nunca se inventa**.
- `confidence < 0.7` o algún `null` requerido → la tarjeta lo marca y exige completar.
- `payer` se cruza con pacientes por código, nombre o DNI con la búsqueda que ya existe. Si hay más de un candidato, el usuario elige (igual que la regla «cobrar solo a paciente inequívoco» de PRP 008).
- `operation_id` repetido → aviso de **comprobante duplicado** (consulta `Payment.reference`).

### Validation Commands

```bash
venv/bin/ruff check app/ tests/ && venv/bin/ruff format --check app/ tests/
venv/bin/python -m pytest tests/test_opencode_client.py tests/test_ai_router.py tests/test_vision_intake.py -q
venv/bin/python -m pytest tests/ -q          # en CI (iCloud cuelga la suite local)
cd edysync && npx ng build                   # en CI
# Servidor (VM-APP):
systemctl status opencode-moscowle
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:4096/doc            # 401 sin clave
ss -ltnp | grep 4096                                                           # solo 127.0.0.1
```

### Code Conventions

- snake_case en Python, camelCase en Angular.
- Tools nuevas en `tools_registry.py` y en `CORE_TOOL_NAMES`.
- Las de escritura, con confirmación (no se agregan a `SAFE_WRITE_TOOLS`).
- Ajustes en `SystemSetting` (como `payroll.*` en PRP 008).
- UI en español.

## Implementation Blueprint

### Fase A — Servicio opencode en el servidor (infra, sin tocar el chat)

1. Confirmar dónde está instalado opencode y la versión (`which opencode; opencode --version` en host y VM-APP).
2. Instalar en VM-APP y crear el usuario de sistema `opencode`, con `/srv/opencode/{sandbox,home}`, `opencode.json` y `moscowle-agent.md`.
3. Iniciar sesión del proveedor Zen si el modelo gratis lo pide (`opencode auth login` como usuario `opencode`).
4. Unit `opencode-moscowle.service`:
   - `ExecStart=opencode serve --hostname 127.0.0.1 --port 4096`
   - `EnvironmentFile=/etc/opencode-moscowle.env`, que solo lleva `OPENCODE_SERVER_PASSWORD`
   - Hardening de la Decisión 3, `Restart=on-failure`, `MemoryMax=1G`
5. En el `.env` de Moscowle: `OPENCODE_URL=http://127.0.0.1:4096` y `OPENCODE_PASSWORD` (misma clave).
6. Smoke: `/doc` da 401 sin clave; un «OK» con el agente `moscowle` da menos de 6k tokens de entrada.

### Fase B — Cliente `app/services/opencode_client.py`

- `OpencodeClient.step(session_id, text, images=(), schema=STEP_SCHEMA) -> dict` y `create_session(title)`, `abort`, `close`.
- **Lista blanca de rutas** (`/session`, `/session/{id}/message`, `/prompt_async`, `/abort`, `DELETE /session/{id}`, `/event`). Cualquier otra lanza `OpencodeForbidden`.
- Siempre manda `agent="moscowle"`, el modelo, `tools` todo en `false` y `format`.
- Timeouts: conexión 1,5 s, respuesta 45 s (60 s con imagen).
- Errores 429/5xx → `_block_provider('opencode')` del circuit breaker existente.
- Sesiones: una por chat de Moscowle (mapa en `ChatSession`, nueva columna `opencode_session_id`). Se cierra con `chat/clear` o tras 24 h. La memoria vive en Moscowle; opencode solo ve las últimas N vueltas que Flask le pasa.
- `eventlet`: `requests` está parcheado (`monkey_patch` en `server.py`), así que no bloquea los sockets. Los reintentos usan `eventlet.sleep`.

### Fase C — Router y bucle de pasos en `mcp_service.process_message`

- `ai_router.route(message, history, has_image, role) -> 'local' | 'opencode'`:
  - `local`: small-talk; `match_intent` con una sola tool y args completos; rol paciente; intención con datos clínicos (lista de tools y palabras clave clínicas); `ai.opencode.enabled=false`; circuit breaker abierto.
  - `opencode`: imagen adjunta; más de una intención detectada; pedido con «y», «luego», «después» y verbos de acción; `should_escalate_to_remote` verdadero; el local devolvió `clarify` dos veces.
- Bucle: máximo 4 pasos, 90 s en total.
  - El catálogo enviado es solo el de `get_tools_for_mode(mode, role)` filtrado por las 12 tools más afines (índice de `tool_intents`), en formato corto.
  - Lectura: ejecutar, recortar y devolver al modelo.
  - Escritura: cortar y devolver `requires_confirmation` + `pending_tool` (mismo contrato de hoy, así la UI no cambia).
- Al confirmar, la ejecución va por `confirmed_tool`, **sin** pasar por opencode.
- Seudonimización: `privacy.pseudonymize(text) -> (text, mapping)` antes de enviar; `restore(answer, mapping)` al responder.
- Eventos de traza (PRP 007): `route` (local u opencode), `step` (tool + reason), `tool_result`, `fallback`.

### Fase D — Registro por imagen

1. `/mcp/upload` guarda la imagen como hoy.
   - Si opencode está activo, llama `vision_intake.extract(path, hint)`: redimensiona a ≤1600 px, convierte a JPEG (la primera prueba con un PNG con transparencia no devolvió texto) y aplica el contrato de extracción.
   - Si no, cae a `_ocr_voucher`.
2. Mapeo `doc_type` → tool:
   - `voucher` → `register_payment` (por el libro de PRP 008)
   - `expense_receipt` → `create_expense`
   - `attendance_sheet` → `mark_attendance`, una por persona y todas en una sola tarjeta
   - `id_document` → completar datos de un paciente existente, nunca crear
   - `contract` → `create_payment_plan` con monto, día y cuotas
   - `other` → solo describe
3. Tarjeta editable en los dos chats (`ai-chat`, `chat` de la página del asistente):
   - Campos con su confianza, aviso de duplicado y selector de paciente si hay más de un candidato.
   - Botones «Registrar» / «Corregir» / «Descartar».
   - Lo editado viaja en `confirmed_tool.args`.

### Fase E — Ajustes y auditoría (admin)

- En Configuración → Asistente IA:
  - interruptor `ai.opencode.enabled`
  - `ai.opencode.allow_id_documents`
  - estado del servicio (ping a `/doc` con clave → conectado o caído)
  - tokens y latencia del día
- Tabla `AiExternalCall(user_id, route, doc_type, categories, tokens_in, tokens_out, ms, ok, created_at)`, **sin el contenido**.
- Tool de lectura `get_ai_usage` para el admin.

### Fase F — Validación y entrega

1. Tests:
   - `test_opencode_client.py`: lista blanca (llamar `/shell` lanza), timeouts y el circuit breaker; servidor falso con `responses`.
   - `test_ai_router.py`: paciente nunca escala; clínico nunca escala; imagen escala; apagado igual a hoy.
   - `test_vision_intake.py`: JSON con `null` exige completar; duplicado por `operation_id`; un terapeuta no obtiene tools de admin.
   - Seudonimización: ningún `username` ni email de paciente en el body enviado.
2. PR → CI verde → merge → deploy Ubuntu y cPanel (frontend).
3. Smoke en producción con `ai.opencode.enabled` apagado (nada cambia). Luego encenderlo solo para el admin 48 h (`ai.opencode.roles=admin`) y después para terapeutas.

## Validation Loop

### Level 1: Syntax & Style

`venv/bin/ruff check app/ tests/` · `npx ng build`.

### Level 2: Tests

Los tres archivos nuevos más la suite completa en CI. Baseline: los preexistentes documentados en la skill.

### Level 3: Smoke (tras deploy)

- `ss -ltnp | grep 4096` → solo `127.0.0.1`.
- `curl http://127.0.0.1:4096/session/x/shell` desde VM-APP sin clave → 401.
- Chat admin: «resumen de deuda por sede y quién vence esta semana» → traza con `route=opencode` y 2 tools.
- Foto de comprobante → tarjeta → confirmar → aparece en Pagos con su adjunto y la cuota aplicada.
- `systemctl stop opencode-moscowle` → el chat responde por el camino local; el evento `fallback` aparece en la traza.

## Anti-Patterns to Avoid

- ❌ Darle a opencode `bash`, `edit` o `read`, o su directorio de trabajo en el repo. Es un ERP con datos clínicos, no un entorno de desarrollo.
- ❌ Llamar a `/session/:id/shell` o `/command`, aunque sea «para diagnóstico».
- ❌ Escuchar en `0.0.0.0` o publicar opencode por cloudflared.
- ❌ Conectar las tools de Moscowle por MCP con un token fijo: todas las llamadas valdrían como el mismo usuario.
- ❌ Ejecutar tools de escritura dentro del bucle «porque el modelo ya las confirmó».
- ❌ Usar el agente `build` por defecto (~50k tokens por mensaje).
- ❌ Mandar notas clínicas o nombres reales al modelo gratuito.
- ❌ Inventar montos o fechas ilegibles de una imagen.
- ❌ Hacer del camino opencode el único: siempre hay respaldo local.

## Preguntas abiertas (resueltas el 2026-10-19, ver «Decisiones del usuario»)

1. **Dónde está instalado opencode hoy:** ¿host o VM-APP? El plan asume que se instala en VM-APP.
2. **Términos de datos del modelo gratis:** si usan los prompts para entrenar, ¿aceptas comprobantes y recibos seudonimizados, o se limita a admin y pruebas hasta tener un modelo de pago (`opencode-go/mimo-v2.6-flash`)?
3. **Tipos de imagen a registrar en la primera entrega:** propuesta comprobante y gasto (Fase D 1–2). Asistencia, DNI y contrato en una segunda.
4. **«Modo desarrollador»** (opencode con `bash` limitado a `journalctl`, `systemctl status` y `git log` para diagnosticar el servidor desde el chat, solo para ti): ¿lo quieres? Está fuera de este PRP a propósito; sería un PRP aparte con su propio usuario y su propia lista de permisos `ask`.
