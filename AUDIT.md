# Auditoría Técnica — Centro Juan Pablo II (ERP Angular)

Fecha: 2026-08-09 · Build verificado en prod: `main-*.js?v=1786247480`
Alcance: carga inicial (hardware básico) + responsive 320px + accesibilidad del admin.

> Actualización 2026-08-10 · Build verificado en prod: `main-ZJPAYJM3.js?v=1786329936`

## Changelog — Asistente IA guiado (confirm-gate)

- Backend: gate de confirmación para tools `write` (`SAFE_WRITE_TOOLS` en `tools_registry.py`; `_requires_confirmation` en `mcp_routes.py`). El stream SSE emite `tool_call` → `confirm` → `done(pending_confirm)` y **retorna sin ejecutar**. Re-ejecución idempotente vía `confirmed_tool` pre-seed (ejecuta + inyecta resultado real + evita re-llamada del LLM).
- Backend: `_build_tool_prompt` guía al LLM a recolectar todos los parámetros antes de llamar tools de estado; `CHIPS_AFTER_TOOL` emite chips de navegación/acción tras cada tool ejecutado.
- Frontend: `McpChatService` (SSE único con tipos `McpChip`/`McpPendingConfirm`/`McpStreamEvent`), `McpToolMeta` (labels/iconos), `ChatConfirmDialog` (resumen de args, paciente buscable, edición JSON) y refactor de `AiChat` + página `/ai-assistant` (chips, confirm/cancel, `pageSuggestions`, sin "Antigravity").
- Housekeeping iconos: registrados `faPlus`, `faWrench` (causa raíz de un error CD que impedía abrir el modal de confirmación), aliases `wallet`/`exclamation-circle`/`info-circle` en el mapa del chat; renombrado `antigravity-capabilities` → `assistant-capabilities`.

### Verificación en prod (2026-08-10)

1. Gate backend: stream `tool_call:register_payment → confirm → done[PC]` sin ejecución (captura raw SSE). ✅
2. Modal de confirmación: campos correctos (paciente, monto, método, fecha) + búsqueda de paciente + edición JSON. ✅
3. Cancelar: resetea estado, mensaje "Acción cancelada...", chat usable. ✅
4. Consola limpia en build nuevo (sin errores de iconos/NG). ✅
5. E2E confirm→execute aplazado por decisión del usuario (requeriría escritura real en DB de prod).

## Audit Health Score

| # | Dimensión | Score | Hallazgo clave |
|---|-----------|-------|----------------|
| 1 | Accessibility | 4 | AA cumplido; 0 targets < 44px tras los fixes |
| 2 | Performance | 4 | ng2-charts/Chart.js fuera del admin (708→348KB); preloads del build OK |
| 3 | Responsive Design | 4 | 320px sin overflow; 0 targets < 44px en dashboard/usuarios/sesiones |
| 4 | Theming | 3 | Tokens usados + dark mode; sin auditoría de contraste profunda |
| 5 | Anti-Patterns | 3 | Diseño coherente con la paleta; sin eval visual definitiva |
| **Total** | | **18/20** | **Great (address weak dimensions)** |

## Anti-Patterns Verdict

No AI-slop evidente en la implementación: paleta propia en tokens, tipografía Manrope/Poppins,
layout de app real (sidebar off-canvas, header sticky, data-dense). La apariencia visual no se pudo
evaluar con render (el auditor no interpreta PNG), por lo que la nota de esta dimensión es estructural,
no estética.

## Executive Summary

- Audit Health Score: **18/20** (Great)
- Problemas: 0 P0 · 2 P1 (ambos corregidos) · 4 P2 (todos corregidos) · 3 P3 (1 corregido, 2 evaluados-no-aplica)
- Top problemas:
  1. Bundle inicial 2.28MB eager arrastraba socket.io + FontAwesome completo + AiChat/fullcalendar al chunk raíz (bloqueaba el boot en hardware básico). **Corregido.**
  2. Touch targets del header 36-40px < 44px (WCAG 2.5.8 / Apple HIG). **Corregido.**
  3. Targets < 24px en página de Usuarios (pills de filtro 21px, botones "Editar" 23px). **Corregido.**
  4. Controles de calendario pequeños (flechas 29×30, HOY 39×20). **Corregido.**
   5. Login local/desarrollo imposible por CORS (backend solo origin prod). **Corregido** (whitelist + verificado end-to-end).
   6. Error en consola tras login: `Could not find icon with iconName=expand and prefix=fas` (fullscreen del AiChat usaba `faExpand`/`faCompress` no registrados en el set tree-shaken). **Corregido** (registrados en `fontawesome-icons.ts`; verificado 0 errores en recarga de dashboard en prod).
- Próximos pasos: re-auditar para confirmar 18/20 estable.

## Optimización de carga inicial (implementada y desplegada)

| Métrica | Antes | Después |
|---|---|---|
| Chunk raíz (eager) | 2.277 KB | **690 KB** |
| `main.js` | ~380 KB | **205 KB** |
| socket.io-client | 269 KB eager (chunk raíz) | **42 KB lazy** (solo al abrir chat) |
| Chunks totales | 17 | 10 |
| Login (auth) | 26 KB dentro de closure | **+32 KB** chunk dedicado |
| Admin (dashboard) | — | 693 KB lazy por feature | **348 KB** (ng2-charts extraído) |
| Chart.js + ng2-charts | — | dentro del chunk admin | **204 KB lazy** (solo finanzas/payments/reports/visor) |

Cambios estructurales:
- `CoreModule` solo providers de interceptores (sin SharedModule/layouts eager).
- `MainLayout` vía `loadComponent` en `main.ts`.
- Iconos FontAwesome registrados con `APP_INITIALIZER` (tree-shaking, 381KB → 183 iconos).
- `SharedModule` slim: consumidores importan AiChat/CalendarWidget/etc. directo.
- `ChatService.connect()` usa `import('socket.io-client')` dinámico.
- Rutas admin que usan ng2-charts (finanzas, payments, reports, visor-funcionamiento) migradas a `loadComponent` (`admin-routing-module.ts`): esbuild extrajo Chart.js/ng2-charts a un chunk compartido lazy (204KB) que solo se descarga al visitar esas páginas.

Verificado en prod: login solo carga `main` + closure + `chunk-R5XIBGVF.js` (32KB); **socket NO se carga**.

## Fixes aplicados

- **[P1] Header touch targets** (`header.html`, `preferences-menu.ts`): toggle/notificaciones 36→**44px**, configuración 40→**44px**, avatar 32→40px. Clases `w-11 h-11` verificadas en el CSS del build y en prod (44×44).
- **[P1] Bundle raíz** (ver tabla): causa raíz era `SharedModule` eager vía main+CoreModule.
- **[P2] Targets página Usuarios** (`styles.scss`): regla global `.btn-filter/.btn-ghost { min-height:44px }` en móvil → pills de filtro (antes 21px) y "Editar" ahora **44px**.
- **[P2] Botones del dashboard** (`button.scss`): `@media (max-width:767px) { button { min-height:44px } }` → "Ver Pendientes" y "Ver Calendario Global" ahora **44px**.
- **[P2] Controles de calendario** (`calendar-widget.scss`, `sessions.html`): `.nav-btn/.today-btn/.range-toggle-btn/.range-tab/.range-cancel-btn` con `min-width/min-height:44px` en móvil; flechas prev/next `w-11 h-11`.
- **[P2] Botón ayuda del sidebar** (`sidebar.scss`): 32→**44px** (`2.75rem`).
- **Verificado en prod a 320×568**: 0 botones < 44px en dashboard, usuarios y sesiones; sin overflow horizontal (`scrollW=320`) en ninguna pantalla.

## Detailed Findings by Severity

### P0
Ninguno.

### P1 — Corregidos
- **[P1] Bundle de carga inicial 2.28MB** — Performance — Impacto: boot lento/por pantallas congeladas en celulares básicos. **Corregido** (690KB eager, socket lazy).
- **[P1] Touch targets < 44px en header** — Accessibility/Responsive (WCAG 2.5.8, Apple HIG) — Impacto: toques imprecisos, doloroso en móvil. **Corregido** (44×44 en los 3 botones).

### P2
- **[P2] Targets < 24px en Usuarios** — `users-list.html` — Accesibilidad (WCAG 2.5.8) — Pills de filtro 21px y "Editar" 23px. Impacto: difícil de pulsar. **Corregido** vía regla global `.btn-filter/.btn-ghost` 44px en móvil.
- **[P2] Controles de calendario pequeños** — `sessions` calendar — Responsive — Flechas 29×30, HOY 39×20, RANGO 69×20. Impacto: frustración al tocar. **Corregido** (`min-width/min-height:44px` en móvil).
- **[P2] Botones del dashboard < 44px** — dashboard.html — "Ver Pendientes" 138×38, "Ver Calendario Global" 178×36. Impacto: targets de altura insuficiente. **Corregido** (`min-height:44px` en `button.scss` para móvil).
- **[P2] Login local/desarrollo imposible por CORS** — Backend — El backend solo acepta origin prod; desarrollo requiere `--disable-web-security` o whitelist localhost. Impacto: flujo de desarrollo lento. **Corregido**: `CORS_ORIGINS` whitelist en `.env.production`/`config.py` incluye localhost:8086/4200/8080 + 127.0.0.1; verificado en prod (OPTIONS devuelve el origin local, login end-to-end desde `http://localhost:8086` OK).

### P3
- **[P3] Sin preload hints en `index.html`** — Performance — **Evaluado: no aplica.** El build de Angular ya emite `modulepreload` para todos los chunks del grafo inicial, `styles-*.css` se carga async (`media="print"` + `onload`) y hay `<link rel="preload">` para las fuentes de Google Fonts.
- **[P3] `styles-*.css` 128KB** — Performance — **Evaluado: no se purga.** Tailwind v4 genera utilidades on-demand (solo las usadas) y el CSS ya va async; purgar arriesga romper estilos sin beneficio de LCP.
- **[P3] `@defer` dashboard + libs pesadas** — Performance — **Corregido.** Dashboard no usa ng2-charts (barras CSS puras); fullcalendar no se usa. Chart.js estaba en el chunk admin (708KB) → extraído a chunk lazy de 204KB vía `loadComponent` en finanzas/payments/reports/visor-funcionamiento. Admin chunk: **708→348KB**. Verificado en prod: dashboard carga sin chart.js; finanzas/payments cargan Chart.js y renderizan sus canvas sin errores.

## Patterns & Systemic Issues

- Touch targets sub-dimensionados eran **sistémicos** en el admin (header, calendario, usuarios, dashboard): se resolvió con una regla global `min-height:44px` en botones táctiles para móvil (`button.scss`, `styles.scss`) en vez de fixes aislados.
- El sistema de chunks por feature está ahora bien particionado; mantener la regla de no importar pesos pesados desde `SharedModule`/`CoreModule` ni registrar páginas con librerías pesadas como `component:` estático.

## Positive Findings

- Paleta/tokens consistente y dark mode funcional.
- Drawer off-canvas responsive funciona correctamente a 320px (apertura/cierre/overlay, sin overflow). El "bug" reportado previamente era un artefacto de emulación de viewport, no un defecto.
- Sin overflow horizontal en ninguna pantalla probada a 320px (login, dashboard, sesiones, usuarios).
- Login a 320px: inputs 208×54 y botón 208×52 (cumplen hit target).
- Builds limpios (solo warnings NG8107 preexistentes) y deploy con cache-bust funcionando.
- Login rechazado muestra toast elegante sin crash (CORS/credenciales).
- **CORS dev resuelto end-to-end**: login real desde `http://localhost:8086` contra el backend de prod, sin flags de seguridad en el navegador.
- **Chart.js fuera del admin**: dashboard/sesiones/usuarios cargan sin Chart.js (verificado en prod vía red del navegador); finanzas/payments renderizan sus gráficas (7/2 canvas, sin errores).

## Recommended Actions

1. **[P3] Re-auditar** con `/impeccable audit` para confirmar el 18/20 y cerrar el ciclo.
2. Mantener la regla de arquitectura: las páginas con librerías pesadas (ng2-charts y similares) deben registrarse con `loadComponent`, nunca como `component:` estático en un routing de feature.
3. Si en el futuro el admin crece, evaluar dividir `chunk-VPSLCL2Q.js` (348KB) en sub-chunks por sección (sesiones/usuarios por un lado, finanzas/reportes por otro).

> Puedes pedirme que los ejecute uno a uno, todos a la vez, o en el orden que prefieras.
> Re-audita tras los fixes para ver mejorar el score.
