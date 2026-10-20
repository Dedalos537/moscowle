# PRP: Correos con MJML (diseño, frecuencia y seguimiento) y notificaciones por tipo

> **Version:** 1.0
> **Created:** 2026-10-20
> **Status:** Aprobado (2026-10-20). Orden: primero **E (notificaciones por tipo)**, luego correos (A–D).
> **Decisiones del usuario (2026-10-20):**
> 1. Diseño de correo con el **estilo del frontend**.
> 2. Envío por **Gmail SMTP**.
> 3. Se miden **aperturas y clics** (con aviso en el pie).
> 4. Resumen **diario a las 7:00 + opción semanal** (lunes).
> 5. Notificaciones presentadas como **Badge, Push, Banner, Snackbar, Toast o Modal** según el tipo, en **móvil y PC**.
> **Depende de:** PRP 010 (avisos del servidor como un tipo más), PRP 008 (cobranza: recordatorios y confirmaciones de pago)

---

## Goal

1. **Un solo diseño de correo**, hecho con **MJML**: responsive, accesible, que se vea bien en Gmail, Outlook, Apple Mail y el celular. Una plantilla por tipo de correo y una base común (cabecera, pie, botones).
2. **Frecuencia controlada**: cada correo pertenece a una clase (transaccional, recordatorio, alerta, mensaje, resumen) con reglas claras de cuándo se envía, cuántos por día y en qué horario. Cada usuario elige por categoría: al momento, en el resumen diario, semanal o nunca.
3. **Seguimiento**:
   - registro de cada correo (enviado, falló, abierto, clic);
   - tablero en Configuración → Correos con tasas por plantilla;
   - vista previa y envío de prueba de cada plantilla.
4. **Notificaciones preparadas para dividirse por tipo**:
   - un registro de **tipos** (`kind`) con su categoría, prioridad, canales, ícono y **la interfaz que lo muestra**;
   - un `payload` con los datos de cada tipo, para que el frontend pinte una tarjeta distinta por tipo.

   Los diseños de cada tipo los defines tú después; este PRP deja la base lista para enchufarlos.

## Why

### Hallazgos en el código (2026-10-20)

| Hallazgo | Dónde | Efecto |
|---|---|---|
| **15 tipos de correo construidos a mano y dispersos**: f-strings de texto plano o HTML con estilos en línea, cada uno con su propio diseño | `email_service.py` (9 métodos); `mail.send(` directo en 7 archivos: `crisis_monitor`, `automated_reports_service`, `incident_notification_service`, `messaging`, `daily_digest_service`, `bot_conversation_service`, `email_service` | Sin identidad visual; los textos planos se ven pobres; cambiar el diseño exige tocar 7 archivos |
| **El resumen diario arma ~200 líneas de HTML a mano** | `daily_digest_service._build_digest_html` (líneas 659–860) | Frágil; en Outlook y en modo oscuro se rompe |
| **Envío en la misma petición**: `mail.send()` se llama dentro del request o del job | todos | Si Gmail tarda o falla, la pantalla espera o el correo se pierde sin reintento |
| **Sin registro**: no se sabe qué se envió, a quién, si falló o si se abrió | — | No se puede auditar ni medir |
| **Frecuencia solo para «nuevo mensaje» (30 min) y SLA** | `EmailThrottle`, `NEW_MESSAGE_COOLDOWN_MINUTES` | Recordatorios de pago y alertas sin tope diario ni horario |
| **Lo que ya está bien y se conserva** | `_make_message` | Alternativa de texto, `List-Unsubscribe` + `List-Unsubscribe-Post` (RFC 8058), `Auto-Submitted`, remitente con nombre |
| **Notificaciones sin tipo canónico** | `notify_user(category, notif_type, event_type…)`; categorías sueltas (`system`, `alert`, `security`, `therapist_payment`, `operational`, `message`, `contact`, `herramientas`, `auto`…); ~25 `event_type` en `notification_intelligence` | El frontend no sabe qué es cada notificación más allá de un texto: todas se ven igual |
| Preferencias por categoría y Telegram ya existen | `UserNotificationPreference` (`debt_enabled`, `payment_enabled`, `telegram_level`, `digest_channel`…) | Se extienden, no se reemplazan |

### Restricciones del entorno

- **El deploy no instala paquetes nuevos** (`scripts/server_deploy.sh` no corre `pip install` ni `npm install`; lo vimos en PRP 010). Por eso **MJML se compila en CI y en desarrollo**: al servidor solo llegan los `.html` ya compilados, que Jinja2 rellena. Sin Node en el servidor para los correos y sin dependencias nuevas en Python.
- **El envío sale por Gmail SMTP** (`MAIL_SERVER=smtp.gmail.com`). Gmail limita a ~500 destinatarios/día por cuenta y **no avisa de rebotes por API**: llegan como correos de vuelta al buzón. El seguimiento de aperturas y clics se hace en Moscowle.
- **Gmail y Outlook no muestran SVG**: el logo (`assets/img/logo.svg`) necesita una versión **PNG** (2× para pantallas retina) en una URL pública.

## What

### A. Diseño con MJML

```
emails/                              ← fuente (se versiona)
  package.json                       ← mjml con versión fija + script build/watch/validate
  build.mjs                          ← compila src/*.mjml → app/templates/email/*.html
  src/
    _base.mjml                       ← mj-head: fuentes, colores, preheader, modo oscuro; cabecera con logo; pie
    _partials/button.mjml            ← botón «a prueba de balas» (MJML ya lo resuelve para Outlook)
    _partials/card.mjml, _partials/amount.mjml, _partials/table.mjml
    bienvenida.mjml
    codigo_restablecer.mjml
    contrasena_cambiada.mjml
    recordatorio_pago.mjml           ← variantes: vence en N días / hoy / vencido
    pago_recibido.mjml               ← con el detalle de cuotas cubiertas (PRP 008)
    sesion.mjml                      ← creada / reprogramada / cancelada / completada
    nuevo_mensaje.mjml
    alerta.mjml                      ← incidentes, SLA, crisis, avisos del servidor (PRP 010)
    reporte_pagos_admin.mjml
    resumen_diario.mjml              ← BSC + notificaciones agrupadas (reemplaza el HTML a mano)
    reporte_automatico.mjml
app/templates/email/                 ← salida compilada (se versiona; la usa Python)
  *.html  +  *.txt                   ← la versión de texto también es plantilla (no se deriva del HTML)
```

**Línea visual:**

- **Fondo y tipografía:** fondo `#f8fbed` (surface), tarjeta blanca de 600 px, texto `#1a1c16` y acento `#75a83a` (primary).
- **Botón:** fondo `#75a83a` con texto `#0a2100`, contraste AA 6:1 (el mismo criterio del frontend; blanco sobre verde daba 2,8:1).
- **Montos:** grandes y con su estado.
- **Preheader:** cada correo tiene su texto de vista previa.
- **Modo oscuro:** `prefers-color-scheme` en `mj-style`; para Gmail, que invierte colores, el logo PNG va con fondo transparente y borde suave.
- **Accesibilidad:**
  - `lang="es"`;
  - tablas de diseño con `role="presentation"` (MJML lo pone);
  - `alt` en imágenes;
  - texto mínimo de 14 px;
  - el enlace nunca es solo un ícono.
- **Pie, igual en todos:**
  - dirección y teléfono del centro;
  - por qué recibes este correo;
  - enlace «Gestionar avisos» (preferencias);
  - «Dejar de recibir este tipo» (baja por categoría; la baja total ya existe).

> «con este mjml mails»: se usa **MJML** (mjml.io), el lenguaje de plantillas de correo responsive. Si tienes un diseño o kit de plantillas MJML en particular, pásamelo y lo tomo como base en vez de partir de cero.

### B. Un solo punto de envío, con cola y reintentos

```python
mailer.send(template='pago_recibido', to=user, context={...}, kind='payment.received',
            dedupe_key=f'pay:{payment.id}')
```

1. Valida la plantilla y el contexto, y respeta las preferencias del usuario y las reglas de frecuencia (C).
2. Renderiza `email/<template>.html` y `.txt` con Jinja2 (autoescape activado). Agrega preheader, enlaces de baja y, si aplica, el seguimiento (D).
3. **Encola** en `EmailOutbox`. No envía dentro de la petición: la pantalla responde al instante.
4. **Un job del scheduler cada minuto** envía la cola:
   - Lotes pequeños, respetando el tope diario de Gmail.
   - Reintentos con espera creciente (1, 5 y 30 min, 2 h). Después queda `failed`, con el error visible en el tablero.
   - Los transaccionales (código de restablecer, bienvenida) **saltan la cola**: se envían en el momento y, si fallan, se encolan para reintento.
5. `_make_message` se conserva: cabeceras RFC 8058, `Auto-Submitted`, remitente con nombre.
6. Se migran los 9 métodos de `EmailService` y los 7 `mail.send(` directos a `mailer.send`. `EmailService` queda como fachada fina por compatibilidad.

### C. Frecuencia

| Clase | Ejemplos | Cuándo | Tope |
|---|---|---|---|
| **Transaccional** | código de restablecer, bienvenida, contraseña cambiada, pago recibido | al momento, siempre (no se puede desactivar) | sin tope; dedupe por `dedupe_key` |
| **Alerta** | incidente, SLA, crisis, servidor caído (PRP 010) | al momento, también en horario de silencio si es `urgent` | 1 por clave cada 30 min (`EmailThrottle`, generalizado) |
| **Recordatorio** | pago por vencer / vencido | calendario fijo: **D-3, D0, D+3, D+7**, luego semanal hasta 4 semanas; a las 9:00 Lima | 1 por cuota y día |
| **Mensaje** | nuevo mensaje del chat | si no lo leyó en la app en 15 min; agrupa los de un mismo remitente | 1 por remitente cada 30 min (como hoy) |
| **Resumen** | resumen diario (BSC), reporte automático | a la hora que elija el usuario (por defecto 7:00); opción semanal (lunes) | 1 por periodo |

- **Horario de silencio:** 21:00–07:00 Lima. Lo no urgente se guarda y sale a las 7:00.
- **Tope por usuario:** 6 correos no transaccionales al día. Lo que exceda pasa al resumen siguiente; no se pierde.
- **Preferencias:** por cada categoría (pagos, sesiones, mensajes, alertas, reportes), el usuario elige **al momento / en el resumen diario / semanal / nunca**. Extiende `UserNotificationPreference` con un JSON `email_frequency` sin borrar columnas. En la UI va como una fila más en «Mis notificaciones».

### D. Seguimiento

**Modelo `EmailLog`:**

- **Identificación:** `id`, `message_id` (cabecera `Message-ID` propia), `user_id`, `to_email`, `template`, `kind`, `category`, `subject`.
- **Ciclo de vida:** `status` (`queued`, `sent`, `failed`, `skipped_pref`, `skipped_throttle`, `deferred`), `attempts`, `error`.
- **Momentos:** `queued_at`, `sent_at`.
- **Interacción:** `opened_at` y `open_count`, `clicked_at` y `click_count`, `last_link`.

**Cómo se mide:**

- **Aperturas:** píxel `GET /api/public/email/o/<token>.gif`, con el token firmado y su vencimiento.
  - **Son aproximadas:** Apple Mail las precarga (Mail Privacy Protection) y Gmail las cachea. El tablero lo dice.
- **Clics:** fiables. Los enlaces pasan por `GET /api/public/email/c/<token>`.
  - El token firmado lleva el `EmailLog` y el destino.
  - **Solo se redirige a dominios propios** (lista blanca: los dos frontends y el API). Nunca es un redireccionador abierto.
- **Rebotes:** Gmail no da API. Fase opcional: un job que lee por IMAP el buzón del remitente, busca los avisos `mailer-daemon` y marca `bounced` el `EmailLog` por `Message-ID`.
- **Privacidad (Ley 29733):**
  - El pie explica que se mide la lectura para mejorar los avisos.
  - El usuario puede desactivar el seguimiento en sus preferencias.
  - Los transaccionales de seguridad (código de restablecer) **no llevan píxel**.
  - Retención del registro: 180 días.

**Tablero:** Configuración → **Correos** (solo admin).

- **Por plantilla:** enviados, fallidos, % aperturas (aprox.), % clics, último envío.
- **Lista filtrable de envíos:** por usuario, plantilla, estado y fecha, con el error si falló.
- **Vista previa** de cada plantilla con datos de ejemplo, en claro y oscuro, escritorio y celular, más **«Enviarme una prueba»**.
- **Cola:** pendientes, reintentos y diferidos por horario.

### E. Notificaciones por tipo (preparación)

**Registro de tipos** (`app/services/notification_kinds.py`), la fuente única de verdad:

```python
KINDS = {
  'payment.due':        Kind(category='payment', priority='normal', icon='calendar-day',  ui='payment-card',
                             channels={'inapp', 'email:reminder', 'telegram:important'}, group_ttl=86400,
                             payload={'patient_id': int, 'installment_id': int, 'amount': float, 'due_date': date}),
  'payment.overdue':    …  'payment.received': …  'payroll.due': …
  'session.created' / 'session.rescheduled' / 'session.cancelled' / 'session.completed': … ui='session-card'
  'message.new':        … ui='message-card'      (remitente, fragmento, chat_id)
  'incident.new' / 'incident.escalated' / 'sla.breach': … ui='incident-card'
  'server.alert':       … ui='alert-banner'      (PRP 010: servicio, severidad, resuelto)
  'mimo.paused':        … ui='alert-banner'
  'security.event':     … ui='security-card'
  'report.ready':       … ui='report-card'       (enlace al archivo)
  'contact.lead':       … ui='lead-card'         (landing)
  'task.*':             … ui='task-card'         (kanban)
  'game.completed':     … ui='progress-card'
  'user.*', 'broadcast', 'chatbot.action', 'whatsapp.reminder': …
  'legacy':             … ui='generic'           (todo lo que aún no se migró)
}
```

**Backend:**

- **Columnas nuevas:** `Notification.kind` (con índice) y `NotificationGroup.kind`.
  - Se reutiliza `metadata_json` como `payload`, validado contra el esquema del tipo.
- **Migración de datos:**
  - Las filas actuales reciben su `kind` a partir de `event_type` o `category`; si no se puede, quedan como `legacy`.
  - No se borra nada.
- **Una entrada nueva:** `notify(kind, user_ids, payload, link=None)`.
  - Decide los canales a partir del registro y de las preferencias del usuario: la app, Telegram y el correo (con la frecuencia de la sección C).
  - `notify_user` sigue funcionando como envoltorio (`kind='legacy'` o inferido) mientras se migran los ~20 lugares que lo llaman.
- **API:** `/api/notifications/groups` y `/items` devuelven además `kind`, `ui` y `payload`.

**Frontend** (`core/notifications/`):

- `notification-kinds.ts`: el mismo registro (tipo → `ui`, ícono, color), generado desde el backend en build o servido por `GET /api/notifications/kinds`.
- `NotificationRenderer`: recibe la notificación y pinta el componente de su `ui` (`@switch` sobre `ui` o carga diferida). Mientras no exista el componente de un tipo, usa la tarjeta **genérica actual**, así nada se rompe.
- **Una carpeta por interfaz** (`payment-card/`, `session-card/`, `alert-banner/`…) con **solo el esqueleto y el contrato de entrada** (`input<PaymentPayload>()`). **El diseño de cada una lo defines tú** cuando las dividamos.

### E2. Cómo se muestra cada tipo (decisión 5)

**Seis formas de mostrar una notificación.** El **badge siempre** se actualiza; las demás dependen del tipo y de la prioridad:

| Forma | Para qué | PC | Móvil | Duración |
|---|---|---|---|---|
| **Badge** | contador de la campana; todo lo que no merece interrumpir | número en la campana | igual (también en el ícono si está instalada como app) | hasta leer |
| **Toast** | confirmación o dato breve, sin acción | arriba a la derecha | arriba, ancho completo (como los toasts actuales) | 4 s |
| **Snackbar** | algo pasó y hay **una acción** («Abrir», «Ver», «Ver agenda») | abajo al centro, máx. 560 px | abajo, ancho completo, sobre la barra inferior | 8 s; se pausa con el puntero o el foco |
| **Banner** | **estado que sigue vigente** hasta que se resuelve | franja bajo la cabecera, con acción y cerrar | franja compacta; con 2 o más se pliegan en «N avisos» | hasta resolver o cerrar |
| **Modal** | exige **acuse de lectura** (riesgo, seguridad, crítico) | diálogo centrado con «Entendido» y acción | hoja inferior (bottom sheet) | hasta confirmar; uno a la vez, en cola |
| **Push** | avisar **fuera de la pestaña** | notificación del sistema | notificación del sistema (Android; iOS solo si se instala como app, iOS 16.4+) | la gestiona el sistema |

**Matriz por tipo** (por defecto; la prioridad `urgent` **sube** de nivel y las preferencias del usuario pueden **bajarlo**):

| `kind` | Badge | Toast | Snackbar | Banner | Modal | Push |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `message.new` | ✓ | | ✓ «Abrir chat» | | | ✓ si la pestaña no está visible |
| `payment.received` | ✓ | | ✓ «Ver pago» | | | |
| `payment.due` | ✓ | | | | | |
| `payment.overdue` (resumen admin) | ✓ | | | ✓ «N cuotas vencidas · Ver» | | |
| `payroll.due` | ✓ | | ✓ «Pagar» | | | |
| `session.created` / `rescheduled` / `cancelled` | ✓ | | ✓ «Ver agenda» | | | ✓ solo `cancelled` |
| `session.completed`, `game.completed` | ✓ | | | | | |
| `incident.new` | ✓ | | ✓ «Ver incidencia» | | | |
| `incident.escalated`, `sla.breach` | ✓ | | | ✓ | ✓ si es crítico | ✓ |
| `crisis.alert` (riesgo de paciente) | ✓ | | | ✓ | ✓ | ✓ |
| `server.alert` (PRP 010) | ✓ | | | ✓ hasta «resuelto» | ✓ si `critical` | ✓ si `critical` |
| `mimo.paused` | ✓ | | | ✓ «Usando el modelo de respaldo» | | |
| `security.event` (contraseña cambiada, acceso nuevo) | ✓ | | | | ✓ | ✓ |
| `report.ready` | ✓ | ✓ «Reporte listo» | | | | |
| `contact.lead` (landing) | ✓ | | ✓ «Ver solicitud» | | | ✓ |
| `task.assigned` | ✓ | | ✓ «Ver tarea» | | | |
| `task.updated` / `moved` / `deleted`, `user.*`, `broadcast`, `chatbot.action`, `whatsapp.reminder` | ✓ | | | | | |
| `action.confirmed` (lo que el usuario acaba de hacer: guardado, enviado) | | ✓ | | | | |
| `legacy` (aún sin migrar) | ✓ | ✓ si `high`/`urgent` | | | | |

**Reglas comunes:**

- **Contexto:** si el usuario ya está donde ocurre (por ejemplo, el chat abierto con esa persona), no se muestran toast, snackbar ni push; solo se marca como leído.
- **Sin duplicados:** la misma notificación por socket y por la lista REST se muestra una vez (por `id`). Hay como máximo **3 toasts y 1 snackbar** a la vez; los modales van en cola.
- **No molestar:** de 21:00 a 07:00, o si el usuario lo activa, solo badge. Las `urgent` sí suenan y usan push.
- **Accesibilidad:**
  - toast y snackbar con `role="status"` (`aria-live="polite"`); banner y modal críticos con `role="alert"`;
  - el foco va al modal y vuelve al cerrar;
  - nada se cierra solo si tiene una acción que el usuario podría estar leyendo con lector de pantalla;
  - se respeta `prefers-reduced-motion`.
- **Push en dos pasos:**
  - **N1:** la API `Notification` del navegador cuando la pestaña no está visible. Ya existe en `notification.service.ts:145` (`browser_notifications`); se amplía por tipo.
  - **N3:** **Web Push real** con service worker y VAPID, para avisar con la app cerrada. Requiere `pywebpush` en el servidor, y el deploy hoy no instala paquetes: se agrega al deploy un `pip install -r requirements.txt` cuando cambie ese archivo, o se instala a mano una vez. iOS solo recibe push si la app está instalada (manifest + «Agregar a inicio»).

**Arquitectura (frontend, `core/notifications/`):**

- **`notification-kinds.ts`:** tipo → formas por defecto, ícono, color y acción.
- **`NotificationPresenterService`:**
  - recibe cada evento del socket con `{id, kind, presentation[], title, message, payload, action, link}`;
  - decide según contexto, prioridad, preferencias y «no molestar»;
  - reparte a `ToastService` (existente), `SnackbarService`, `BannerService`, `NotificationModalService` y `PushService`.
- **Componentes nuevos** en `shared/components/`: `snackbar`, `notice-banner` y `notification-sheet` (modal en PC, hoja inferior en móvil). El toast ya existe.

**Backend:**

- `notification_kinds.py`: el registro (`kind` → categoría, prioridad, `presentation` por defecto, grupo y canales).
- `notify_user(..., kind=None)` infiere el `kind` de `event_type` o `category` mientras se migran las llamadas. El evento de socket y la API agregan `kind`, `presentation`, `payload` y `action`.
- **Columnas nuevas:** `notification.kind` y `notification_group.kind`. Más adelante, en `user_notification_preference`, `presentation_overrides` (JSON por categoría).

### Success Criteria

- [ ] `npm run build` en `emails/` compila sin errores con `--validation-level=strict`, y CI falla si el `.html` versionado no coincide con lo que genera el `.mjml`.
- [ ] Las 11 plantillas se ven bien en:
  - Gmail web y Android, Outlook escritorio y web, Apple Mail iOS;
  - claro y oscuro.

  La revisión se hace con capturas reales o un servicio de pruebas, si se aprueba uno.
- [ ] Ningún `mail.send(` fuera de `mailer`.
- [ ] Registrar un pago no espera al SMTP: el correo va a la cola.
- [ ] Un recordatorio de pago nunca sale dos veces el mismo día por la misma cuota. Nada no urgente sale entre 21:00 y 07:00.
- [ ] Un usuario no recibe más de 6 no transaccionales al día; el excedente aparece en su resumen.
- [ ] El tablero muestra enviados, fallidos, aperturas y clics por plantilla. El redireccionador de clics rechaza dominios fuera de la lista blanca (test).
- [ ] Cada notificación nueva tiene `kind` y `payload` válidos. El frontend pinta la tarjeta genérica para cualquier tipo sin componente, sin errores en consola.
- [ ] Tests:
  - render de cada plantilla con su contexto de ejemplo;
  - cola y reintentos;
  - frecuencia (horario, tope, dedupe);
  - firma de tokens;
  - lista blanca de clics;
  - validación de `payload` por tipo;
  - migración de `kind`.

## All Needed Context

### Archivos actuales

| Archivo | Qué hay |
|---|---|
| `app/services/email_service.py` | `_make_message` (cabeceras RFC 8058, texto alternativo) y 9 métodos de envío |
| `app/services/daily_digest_service.py:659-860` | `_build_digest_html` hecho a mano |
| `app/models/email_throttle.py` | `EmailThrottle.allow(key, cooldown)`: se generaliza para la frecuencia |
| `app/utils/email_tokens.py` | `make_unsubscribe_token`: patrón para firmar los tokens de píxel y clic |
| `app/routes/public_routes.py` | `/api/public/email/unsubscribe`: aquí van `/o/` y `/c/` |
| `app/services/notification_service.py:32` | `notify_user(...)`, entrada actual |
| `app/services/notification_intelligence.py` | `GROUP_TTL` por categoría, ~25 `event_type` (base del registro de tipos) |
| `app/models/notification.py`, `notification_group.py` | `Notification`, `UserNotificationPreference`, `NotificationGroup/Item` |
| `edysync/src/app/core/components/header/header.ts` | campana de notificaciones (donde se enchufa el renderer) |
| `edysync/src/app/shared/components/notification-prefs/` | preferencias (aquí va la frecuencia de correo) |
| `app/tasks.py` | scheduler: aquí van los jobs de la cola y de los recordatorios |

### Validation Commands

```bash
cd emails && npm ci && npm run validate && npm run build && git diff --exit-code ../app/templates/email
venv/bin/ruff check app tests
venv/bin/python -m pytest tests/test_mailer.py tests/test_email_tracking.py tests/test_notification_kinds.py -q   # en CI
cd edysync && npx ng build                                                                                       # en CI
```

## Implementation Blueprint

### Fase 1 — Base MJML y tres plantillas

- `emails/` con `package.json` (mjml de versión fija), `build.mjs` (compila y escribe `.html`), `_base.mjml` y los parciales.
- Plantillas iniciales: **pago_recibido**, **recordatorio_pago** y **codigo_restablecer** (las que más llegan a pacientes).
- Logo PNG en `edysync/public/assets/img/logo-email@2x.png`, publicado en ambos frontends.
- Paso de CI que compila y compara.

### Fase 2 — `mailer` + cola + registro

- Modelos `EmailOutbox` y `EmailLog` (`db.create_all` los crea; columnas nuevas con el patrón ALTER de `app/__init__.py`).
- `app/services/mailer.py` con `send()`, `render()` y `flush_outbox()`; job cada minuto en `app/tasks.py`.
- Se migran los métodos de `EmailService` y los 7 `mail.send(` directos.

### Fase 3 — Frecuencia y preferencias

- Clases, horario de silencio, tope diario, calendario de recordatorios D-3/D0/D+3/D+7 y paso al resumen.
- `email_frequency` en preferencias; filas por categoría en «Mis notificaciones».

### Fase 4 — Seguimiento y tablero

- Píxel, clics firmados con lista blanca y retención de 180 días.
- Configuración → Correos: métricas, lista, vista previa claro/oscuro/celular y envío de prueba.
- (Opcional) Rebotes por IMAP.

### Fase 5 — Resto de plantillas

- Bienvenida, contraseña cambiada, sesiones, nuevo mensaje, alerta, reporte de pagos, reporte automático y **resumen diario**. El resumen reemplaza `_build_digest_html`.

### Fase 6 — Tipos de notificación (preparación)

- `notification_kinds.py`, columna `kind` y migración de datos, `notify()`, y `notify_user` como envoltorio.
- API con `kind`, `ui` y `payload`.
- Frontend: registro, `NotificationRenderer` con caída a la tarjeta genérica y carpetas esqueleto por `ui`.
- **Después, contigo:** el diseño de cada tarjeta.

## Anti-Patterns to Avoid

- ❌ Compilar MJML en el servidor o en cada envío: Node no está para eso y el deploy no instala paquetes.
- ❌ Seguir armando HTML con f-strings, o mezclar estilos en línea a mano con MJML.
- ❌ Enviar dentro de la petición (vuelve la lentitud) o sin reintentos (se pierden correos).
- ❌ Píxel en correos de seguridad, o contar aperturas como dato exacto.
- ❌ Redirector de clics que acepte cualquier URL.
- ❌ Romper `notify_user`: debe seguir funcionando hasta que el último lugar que lo llama esté migrado.
- ❌ Diseñar las tarjetas por tipo antes de que definas la división: este PRP solo deja el contrato y el esqueleto.

## Preguntas abiertas (resueltas el 2026-10-20: ver la cabecera)

1. **Diseño:** ¿tienes un diseño o kit MJML de referencia («con este mjml mails»)? Si no, parto de la línea visual de arriba (la del frontend).
2. **Proveedor de envío:** ¿seguimos con Gmail SMTP (gratis, ~500/día, sin rebotes por API)? ¿O usamos un proveedor transaccional con plan gratuito, que da rebotes y mejor entrega? Por ejemplo Brevo, 300/día gratis. Requiere configurar DNS: SPF, DKIM y DMARC del dominio.
3. **Seguimiento:** ¿medimos aperturas además de clics? Las aperturas son imprecisas y el seguimiento requiere avisarlo en el pie.
4. **Resumen:** ¿solo diario o también la opción semanal? ¿A qué hora por defecto (propuesta 7:00)?
5. **Tipos de notificación:** ¿la lista de `kind` de arriba te sirve como punto de partida para la división que vas a hacer, o ya tienes tu propia lista de tipos?
