# PRP: Todas las pantallas en móvil sin desplazamiento horizontal

> **Version:** 1.0
> **Created:** 2026-10-21
> **Status:** Propuesto. La fase 0 (Configuración, tablas de Finanzas/Reportes, Solicitudes, Incidencias, menú de preferencias) ya se hizo en los PR #81 y #82.
> **Regla única:** en un celular **la página solo se desplaza hacia abajo**. Nada se corre a la derecha, nada queda cortado, en ningún rol ni pantalla.

---

## Goal

Que las **~60 pantallas** (admin 27 rutas + secciones de Configuración, terapeuta 14, paciente 11, login y públicas) se vean bien:

- desde **320 px** de ancho (teléfonos chicos) hasta 899 px;
- con **texto grande** (A+ de Preferencias o el tamaño de fuente del sistema);
- en **modo claro y oscuro**;
- en el **navegador** y dentro de la **app Android**.

Y que **no vuelva a romperse**: una revisión automática en CI falla si una pantalla se desborda.

## Why

Lo que encontramos al revisar con capturas a 360/390 px (PR #81 y #82) no fueron errores sueltos. Son **siete patrones** que se repiten en todo el frontend:

| # | Patrón | Ejemplo real | Arreglo estándar |
|---|---|---|---|
| 1 | `display: grid` **sin columnas**: la columna implícita es `auto` y crece al ancho del hijo más largo (filtros, chips) | Solicitudes, Incidencias, avisos (`.nb`), `.il`, `.ar` | `grid-template-columns: minmax(0, 1fr)` |
| 2 | Tablas con `min-w-[600px…1000px]` dentro de `overflow-x-auto` | Tokens de API, CSP, Pagos, Finanzas, Yape, dashboard | Vista de **tarjetas** con `.mtable` + `data-label` (como Usuarios) |
| 3 | `minmax(180px, 1fr)` / `minmax(13rem, 1fr)` fijos en grids `auto-fill`/`auto-fit` | Bot (canales), Monitor (recursos) | `minmax(min(100%, 13rem), 1fr)` |
| 4 | Fila flex con control al lado del texto (switch, segmentado, select) que **aprieta el texto** a una columna angosta | Barra lateral, Mostrar personas, «Enviar el resumen por» | En móvil el control **baja a su línea** (`flex-wrap` + `flex: 1 1 100%`) |
| 5 | Popovers anclados a un botón (`absolute right-0`) que **no está** en el borde derecho | Menú de preferencias (salía 54 px por la izquierda) | En móvil `fixed` con `inset-x-3` y alto máximo con scroll |
| 6 | `white-space: nowrap` / `min-width` en textos técnicos (fechas ISO, rutas, tokens, logs) | Visor de logs, Configuración de LLM | Se parten (`overflow-wrap: anywhere`) o se cortan con «…» |
| 7 | Reglas globales con `!important` dentro de `@layer base` que **le ganan** a los arreglos de componentes | Centrado de columnas de tablas | Excepciones en el **mismo layer**; no agregar más `!important` en layers |

Además, el **contenedor** que se puede desplazar en vertical (`overflow-y: auto`) también se desplaza en horizontal si algo se sale. Por eso en el teléfono la hoja de Configuración aparecía «corrida».

## What

### 1. Barandas globales (una sola vez, en `styles.scss`)

- `html, body { overflow-x: clip; }` como red de seguridad: nunca hay barra horizontal en la página. Ojo: oculta, no arregla. La revisión automática (punto 3) sigue fallando si algo se sale de su contenedor.
- Todo contenedor con scroll propio que no sea una tira de pestañas: `overflow-x: hidden` (`.settings-pane`, paneles laterales, drawers, modales).
- Utilidades: `.mtable` (ya existe), `.mstack` (fila que en móvil apila el control debajo del texto) y `.mscroll-x` (tiras de pestañas/chips que **sí** se deslizan a los lados, pero dentro de su caja, con degradado en el borde).
- Tipos de letra: los tamaños en `rem`, nunca `px` fijos en contenedores, para que A+ no rompa nada.

### 2. Pasada por pantalla (por rol)

| Rol | Pantallas | Riesgos ya conocidos |
|---|---|---|
| Admin | dashboard, sedes, usuarios, paciente, finanzas, pagos, historial de pagos, sesiones, revisión, gastos, mensajes, reportes, juegos, CSP, tokens, perfil, Yape, IA, visor, operaciones, incidencias (+detalle), solicitudes, restablecer contraseñas, drive, kanban, configuración (15 secciones) | tablas con `min-w` (finanzas, pagos, Yape, tokens, CSP), calendario de sesiones, drive (grilla + vista previa), visor |
| Terapeuta | dashboard, sesiones (+revisión), mensajes, perfil, juegos, pacientes (+detalle), revisión de sesión, reportes, analítica, incidencias, solicitudes, kanban | agenda semana/mes, formulario de solicitudes, reportes |
| Paciente | dashboard, sesiones, pagos, progreso, juegos, calendario, mensajes, perfil, mi terapeuta, incidencias, kanban | calendario, juegos a pantalla completa, tabla de cuotas |
| Público / auth | login, restablecer, crear contraseña, nosotros, contacto | — |

Por cada pantalla:

- se aplica el patrón de la tabla de arriba que corresponda;
- las tablas pasan a tarjetas;
- los modales y drawers ocupan la pantalla completa en móvil;
- los gráficos se ajustan al ancho (`viewBox` + `width: 100%`).

### 3. Revisión automática (para que no vuelva)

`scripts/mobile_audit.mjs` (Playwright, ya está en `node_modules`):

1. Levanta el backend con SQLite y **datos de ejemplo**, porque una tabla vacía no se desborda. El seed tiene nombres largos, montos grandes y 20+ filas.
2. Entra con un usuario de **cada rol** y recorre todas sus rutas y las secciones de Configuración.
3. Prueba anchos de **320, 360 y 390 px**, con texto normal y con A+.
4. En cada pantalla falla si:
   - `document.documentElement.scrollWidth > innerWidth`;
   - o algún elemento visible se sale de su contenedor con scroll, salvo los marcados `.mscroll-x`.
5. Guarda una captura por pantalla en un artefacto de CI para revisarlas de un vistazo.

Se agrega como job `Mobile Audit` en `ci.yml`. Al principio solo avisa; cuando la fase 2 termine, bloquea el merge.

### Success Criteria

- [ ] `mobile_audit` en verde para los 3 roles, a 320/360/390 px, con texto normal y A+.
- [ ] Ninguna tabla con `min-w-[…]` sin su vista de tarjetas.
- [ ] Ningún `display: grid` de layout sin `grid-template-columns` explícito en los componentes tocados.
- [ ] Popovers y menús dentro de la pantalla en móvil (menú de usuario, notificaciones, preferencias, selects personalizados).
- [ ] Modo oscuro revisado con las mismas capturas.
- [ ] En la app Android, el mismo resultado: la WebView usa el mismo frontend.

## Implementation Blueprint

1. **Fase A: auditoría.**
   - Script `mobile_audit.mjs` + seed de datos largos.
   - Correrlo y sacar la lista real de pantallas rotas, con capturas, en `docs/mobile-audit/`.
2. **Fase B: barandas globales.** `overflow-x: clip`, utilidades `.mstack` y `.mscroll-x`, regla de layers.
3. **Fase C: tablas.** Finanzas, pagos (vista principal), Yape, tokens, CSP, dashboard y drive a `.mtable` (2–3 PR).
4. **Fase D: pantallas por rol.**
   - Primero paciente, porque las familias lo usan en el celular.
   - Después terapeuta y admin.
5. **Fase E: CI.** El job `Mobile Audit` pasa de aviso a bloqueante.

## Anti-Patterns to Avoid

- ❌ «Arreglar» con `overflow-x: hidden` en un padre y dejar el contenido cortado. La revisión debe ver el elemento, no solo la página.
- ❌ Esconder columnas o acciones en móvil: se reorganizan, no se quitan. Excepción: duplicados que ya están en otro lugar de la misma pantalla.
- ❌ Anchos fijos en `px` para contenedores, `min-width` en textos y `nowrap` en descripciones.
- ❌ Más `!important` dentro de `@layer`.
- ❌ Revisar solo a 390 px con texto normal: los problemas reales aparecieron a 360 px con A+.

## Preguntas abiertas

1. ¿Hay algún teléfono del centro con pantalla más chica que 360 px que debamos usar como referencia (320 px)?
2. ¿El job de CI debe bloquear el merge desde el inicio, o primero solo avisar mientras se arreglan las pantallas?
