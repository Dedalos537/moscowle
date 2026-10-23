# PRP: Pantalla del asistente para el admin («mini ChatGPT» del centro)

> **Version:** 1.0
> **Created:** 2026-10-23
> **Status:** Implementado (2026-10-23), fases A–D.
> **Decisiones:** (1) el supervisor también la tiene, limitada a su sede; (2) sí a los reportes programados (cada día o semana, por correo y/o Telegram); (3) las conversaciones se pueden compartir con los demás admins (un supervisor solo ve las compartidas por supervisores de su sede); (4) **es la pantalla de inicio** del admin y del supervisor al entrar.
> **Depende de:** PRP 009 (OpenCode + MiMo con caída a la cadena actual), PRP 011 (tipos de notificación), PRP 013 (móvil sin desplazamiento horizontal)

---

## Goal

Una pantalla completa **Asistente** (ruta `/admin/assistant`, entrada en el menú lateral, solo admin y supervisor) donde se conversa con la IA del centro como en ChatGPT. Las respuestas no son solo texto: son **bloques ricos** que el frontend dibuja con los componentes del sistema.

- **Gráficas:** línea, barras, barras apiladas, dona y área, con Chart.js (ya instalado, `ng2-charts`).
- **Tablas comparativas:** ordenables, con totales, exportables a Excel o CSV.
- **Tarjetas de cifras (KPI):** con la variación frente al período anterior.
- **Listas de personas:** con enlace a su ficha (paciente, terapeuta).
- **Acciones con confirmación**, como hoy: crear sesión, registrar pago, asignar, etc.

Las preguntas típicas:

- «¿Cómo vamos este mes contra el anterior?»
- «Compara la asistencia de las sedes en el trimestre.»
- «¿Qué terapeutas tienen más sesiones sin cerrar?»
- «¿Quiénes deben más de dos cuotas?»
- «Arma una tabla de pagos por método de las últimas 8 semanas.»

## Why

- El chat flotante (`app-ai-chat`) sirve para preguntas cortas y acciones. En un panel de 380 px no caben gráficas ni tablas anchas, y la conversación se pierde al cerrarlo.
- Los datos ya existen:
  - **89 herramientas MCP**, filtradas por rol, en `tools_registry.py`.
  - **OpenCode/MiMo**, que hoy decide qué herramienta usar y redacta la respuesta.
  - Los endpoints de reportes, finanzas, sesiones e incidencias.

  Lo que falta es una **superficie** que muestre resultados estructurados y deje volver a ellos.
- El admin hoy junta esos datos a mano entre Reportes, Finanzas y el Dashboard.

## What

### 1. La pantalla

```
┌──────────────┬──────────────────────────────────────────────┬──────────────┐
│ Conversacio- │  Hilo                                         │ Contexto     │
│ nes          │  ┌ Tú: compara asistencia por sede (trimestre)│ (plegable)   │
│ + Nueva      │  └ IA: texto breve                            │ · Período    │
│ ─ Hoy        │       [ gráfica de barras agrupadas ]         │ · Sede       │
│ ─ Ayer       │       [ tabla: sede · sesiones · % · Δ ]      │ · Fuentes    │
│ ─ Fijadas ★  │       Fuente: sesiones · 1 jul–30 sep  ⓘ      │   usadas     │
│ Buscar…      │       [Fijar] [Exportar] [Ver en Reportes]    │ · Modelo     │
│              │  ┌───────────────────────────────────────┐   │              │
│              │  │ Pregunta… (/ comandos · 📎 · 🎤)    ➤ │   │              │
└──────────────┴──────────────────────────────────────────────┴──────────────┘
```

- **Columna izquierda:** conversaciones guardadas (hoy, ayer, esta semana), fijadas y búsqueda. En móvil es un panel deslizable.
- **Centro:**
  - Hilo con **streaming**: se reutiliza `/mcp/chat/stream`, que ya existe.
  - Mientras responde, un indicador muestra qué consulta: «Consultando pagos…», «Comparando sedes…».
  - Respuestas en bloques: texto, gráfica, tabla, KPIs, lista, acción.
- **Columna derecha (plegable):**
  - Contexto activo: período, sede y rol.
  - **Fuentes usadas:** herramientas MCP y rango de fechas, para saber de dónde sale cada número.
  - Modelo que respondió (MiMo o la cadena de respaldo).
- **Pantalla vacía:**
  - Sugerencias según el momento: fin de mes → cobranza, lunes → semana.
  - Atajos `/comparar`, `/deudores`, `/sesiones`, `/sede`.
- **Móvil:** una sola columna y bloques al 100 % de ancho. Las tablas pasan a tarjetas (`.mtable`, PRP 013). Ninguna pantalla se desliza a los lados.

### 2. El contrato de bloques (lo que el backend devuelve)

Cada respuesta de la IA es una lista de bloques tipados. El modelo **no inventa números**: los bloques de datos los arma el backend con el resultado de las herramientas. El modelo solo elige cuál mostrar y escribe el texto.

```json
{
  "blocks": [
    {"type": "text", "md": "En el trimestre **Piura** asistió más (87 %)…"},
    {"type": "kpis", "items": [{"label": "Asistencia", "value": 0.82, "format": "pct", "delta": 0.05}]},
    {"type": "chart", "kind": "bar", "title": "Asistencia por sede",
     "x": ["Talara", "Piura"], "series": [{"name": "Asistió", "data": [120, 150]}, {"name": "Faltó", "data": [30, 22]}],
     "unit": "sesiones"},
    {"type": "table", "title": "Comparativo", "columns": [{"key": "sede", "label": "Sede"}, {"key": "pct", "label": "%", "format": "pct"}],
     "rows": [{"sede": "Talara", "pct": 0.8}], "totals": true},
    {"type": "people", "items": [{"id": 12, "name": "…", "link": "/admin/patients/12"}]},
    {"type": "action", "tool": "create_session", "args": {"…": "…"}, "confirm": true}
  ],
  "sources": [{"tool": "get_attendance_by_sede", "range": "2026-07-01..2026-09-30"}],
  "model": "opencode/mimo-v2.6-flash-free"
}
```

- **Validación:** el backend valida cada bloque con un esquema (tipos, tamaños: máx. 500 filas y 12 series). Si el modelo devuelve algo inválido, se responde solo con el texto.
- **Formato:** fechas, soles (`S/`) y porcentajes con los mismos formatos de la app. El nombre de cada persona sigue la preferencia «solo códigos».

### 3. Herramientas de análisis (backend)

Nuevas herramientas **de solo lectura** en `tools_registry.py`. Devuelven series y tablas listas para un bloque y van en `CORE_TOOL_NAMES`, solo para admin y supervisor.

| Herramienta | Qué devuelve |
|---|---|
| `compare_periods(metric, period_a, period_b, sede?)` | KPIs con delta: ingresos, sesiones, asistencia, deuda, pacientes activos |
| `series(metric, granularity, range, sede?)` | serie temporal para gráfica de línea o área |
| `breakdown(metric, by, range)` | desglose por sede, terapeuta, método de pago o terapia, para barras o dona |
| `top(entity, metric, n, range)` | ranking: terapeutas con más sesiones sin cerrar, deudores, etc. |
| `table(query_id, params)` | tablas predefinidas: pagos por método y semana, asistencia por paciente… |

Las consultas son **predefinidas y parametrizadas**: sin SQL libre del modelo. Además:

- Se cachean 60 s por parámetros.
- Respetan el alcance del rol: el supervisor solo ve su sede.

### 4. Conversaciones guardadas

- **Modelo `assistant_thread`:** `id`, `user_id`, `title` (lo propone la IA), `pinned`, `created_at`, `updated_at`.
- **Modelo `assistant_message`:** `thread_id`, `role`, `blocks` (JSON), `sources`, `model`, `created_at`.
- Se guardan **los bloques ya calculados**: al reabrir no se vuelve a consultar. El botón «Actualizar» los recalcula con datos de hoy.
- **Retención:** 180 días, igual que la actividad (PRP 012). Las fijadas no expiran.
- **Privacidad:** el contenido clínico sigue la regla de `ai_privacy.py` (no sale a MiMo). Cada conversación es solo de su autor.

### 5. Experiencia (frontend)

- **Componentes nuevos** en `features/admin/pages/assistant/`, generados con `ng generate`: `assistant-page`, `thread-list`, `message-blocks`, `block-chart`, `block-table`, `block-kpis`, `composer`.
- **Gráficas:** Chart.js con los colores del sistema de diseño, validados contra daltonismo, con tooltip al pasar el cursor. Cada gráfica trae **«Ver como tabla»** (accesibilidad), respeta modo oscuro y la preferencia «Ocultar gráficos» (si está activa, se muestra la tabla).
- **Tablas:**
  - Orden por columna, totales y formato de números alineado a la derecha.
  - Exportar a Excel (ya se usa en Actividad) o CSV.
  - En móvil pasan a tarjetas.
- **Composer:**
  - Varias líneas (Enter envía, Shift+Enter salta de línea).
  - Comandos con `/` y autocompletado.
  - Adjuntar archivo (voucher, Excel): reutiliza `/mcp/upload`.
  - Dictado: reutiliza `/mcp/transcribe`.
- **Acciones de cada respuesta:**
  - Fijar.
  - Copiar como texto.
  - Exportar.
  - «Abrir en Reportes» con los mismos filtros.
  - Regenerar.
  - 👍 / 👎, que se guarda para mejorar los prompts.
- **Acciones de escritura:** el mismo `chat-confirm-dialog` de hoy. Nada se escribe sin confirmación (`SAFE_WRITE_TOOLS`).
- **Estados:**
  - Cargando: esqueleto del bloque que viene («preparando gráfica…»).
  - Error de una herramienta: el bloque muestra qué falló y deja reintentar.
  - Sin tokens de MiMo: respuesta por la cadena de respaldo, con un aviso discreto.
- **Teclado:** `⌘K` o `Ctrl+K` abre una conversación nueva desde cualquier pantalla del admin.

### 6. Relación con el botón flotante

- **El flotante sigue** para preguntas rápidas en cualquier pantalla y lleva el enlace «Abrir en el Asistente», que continúa la conversación en la pantalla completa.
- **La visibilidad del flotante por tipo de usuario** se decide en Configuración → Apariencia (hecho el 23-oct).
- **La pantalla completa** es solo para admin y supervisor.

## Success Criteria

- [ ] Ante «compara la asistencia por sede este trimestre», responde con una gráfica, una tabla y un texto de 2–3 líneas en menos de 8 s, con las fuentes visibles.
- [ ] Los números de la gráfica y de la tabla coinciden con Reportes, con los mismos filtros (test de contrato por herramienta).
- [ ] Las conversaciones se guardan y se reabren sin volver a consultar. «Actualizar» recalcula.
- [ ] Toda tabla se exporta. En móvil nada se desliza a los lados (auditoría del PRP 013 en `/admin/assistant`).
- [ ] Ninguna escritura sin confirmación. El supervisor no ve otras sedes. Ningún contenido clínico sale a MiMo.
- [ ] Si MiMo no responde, la cadena de respaldo contesta y la pantalla lo indica.

## Implementation Blueprint

1. **Fase A — Contrato y herramientas.**
   - Esquema de bloques y validación.
   - `compare_periods`, `series`, `breakdown`, `top` y `table`, con tests de contrato contra los endpoints de Reportes.
2. **Fase B — Backend de conversación.**
   - `assistant_thread` y `assistant_message`.
   - `/mcp/chat/stream` acepta `thread_id` y devuelve bloques.
   - Título automático y retención.
3. **Fase C — Pantalla.** Ruta, menú, lista de conversaciones, hilo con bloques (texto, KPIs, tabla, gráfica), composer con comandos.
4. **Fase D — Pulido.** Exportar, fijar, «Abrir en Reportes», feedback, `⌘K`, enlace desde el flotante, modo oscuro y auditoría móvil.

## Anti-Patterns to Avoid

- ❌ Que el modelo escriba números o SQL: los datos salen de herramientas tipadas y el modelo solo narra.
- ❌ Gráficas sin la alternativa en tabla, o con colores que no pasan daltonismo.
- ❌ Una gráfica nueva por cada pregunta igual: se cachea y se reutiliza.
- ❌ Guardar conversaciones con contenido clínico en un servicio externo.
- ❌ Copiar el panel flotante a pantalla completa: aquí los bloques y la persistencia son lo principal.

## Notas de implementación

- **Router de intención determinista.** Reconoce resumen, sedes, equipo, deudores, riesgo, altas y bajas, tendencia y pagos por método. Arma los bloques con `center_dashboard` y `sede_scorecard`, así los números son los mismos del Dashboard. Lo que no reconoce va a la IA general (OpenCode/MiMo con respaldo) como texto.
- **Bloques:** `text`, `kpis`, `chart` (line, bar, doughnut), `table` (ordenable, totales, exportar a CSV) y `people`. Se validan en `assistant_analytics.validate_block`.
- **Persistencia:** `assistant_thread`, `assistant_message` y `assistant_schedule` (se crean solas con `create_all`). El job corre cada hora en el minuto 2. La retención es de 180 días para las no fijadas.
- **Botón flotante:** en esta pantalla se oculta, porque sobra.
