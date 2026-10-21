# PRP: Revisión de actividad por usuario (Configuración → Actividad)

> **Version:** 1.0
> **Created:** 2026-10-21
> **Status:** Para aprobar
> **Depende de:** PRP 011 (tipos de notificación y destinatarios por rol), PRP 010 (Prometheus, para la parte técnica)

---

## Goal

Un módulo en **Configuración → Sistema → Actividad** (solo admin) para revisar, **por cada usuario**, dos cosas:

1. **Lo hecho:** línea de tiempo de lo que hizo en la plataforma.
   - Entró y desde dónde.
   - Creó, completó o canceló sesiones.
   - Registró pagos.
   - Movió tareas.
   - Atendió incidencias.
   - Pidió acciones.
   - Imprimió.
   - Usó el asistente.
2. **Lo pendiente (lo que no se hizo):** lista calculada al momento, según su rol.
   - Sesiones pasadas sin cerrar.
   - Tareas vencidas.
   - Incidencias asignadas abiertas o fuera de SLA.
   - Solicitudes sin revisar.
   - Cuotas vencidas del paciente.
   - Juegos asignados sin jugar.
   - Perfil incompleto.

Con filtros (rango de fechas, tipo, sede), exportación a Excel, móvil y PC, y sin registrar datos sensibles (contraseñas, contenido clínico, cuerpos de mensajes).

## Why

- Hoy **no existe un registro general de actividad**: no hay un `AuditLog` (`app/models/` no tiene ninguno). Para saber qué hizo alguien hay que mirar cada tabla.
- Lo que sí existe, y alcanza para la mayor parte:

| Fuente | Qué dice | Modelo |
|---|---|---|
| Inicios de sesión | cuándo, dispositivo e IP | `UserSession` |
| Cambios de estado de cuenta | quién lo cambió y por qué | `UserStatusLog` |
| Sesiones de terapia | creadas, completadas, canceladas, sin cerrar | `Appointment` (`created_at`, `status`) |
| Pagos y gastos | quién los registró | `Payment`, `Expense` (`created_by_id` en `AuditMixin`) |
| Asignaciones de pagos e importaciones | qué cuota cubrió cada pago y quién importó | `PaymentAllocation`, `BillingImport` (PRP 008) |
| Tareas | creadas, movidas, vencidas | `kanban_*` |
| Incidencias | asignadas, resueltas, SLA | `Incidente` |
| Solicitudes | pedidas, aprobadas, rechazadas | `ActionRequest` |
| Impresiones | qué imprimió | `PrintJob` |
| Uso de IA externa | cuándo y qué tipo (sin contenido) | `AiExternalCall` (PRP 009) |
| Mensajes enviados (bot, WhatsApp) | a quién y por qué canal | `MessageLog` |
| Juegos | jugados por el paciente | modelos de `game` |

- Lo que **falta** es un registro de las **acciones de escritura** que no dejan rastro propio: editar un paciente, cambiar un contrato, borrar un archivo del drive, cambiar ajustes. Para eso entra un registro liviano nuevo (ver «Diseño»).

## What

### Pantalla

**Lista de usuarios:**

- **Columnas:** nombre (con «Solo códigos» si está activo), rol, sede, último acceso, acciones en los últimos 7 días y **pendientes**, con un badge de color según cuántos y qué tan atrasados.
- **Filtros:** rol, sede, «solo con pendientes» y búsqueda por nombre, código o correo.
- **Orden por defecto:** primero quien tiene más pendientes vencidos.

**Detalle de un usuario** (panel lateral en PC, pantalla completa en móvil), con dos pestañas:

- **Pendiente:**
  - Agrupado por tipo, con su antigüedad y un botón **«Ir»** que abre el lugar donde se resuelve (la sesión, la tarea, la cuota…).
  - Ejemplos:
    - «3 sesiones pasadas sin cerrar (la más vieja hace 9 días)».
    - «Tarea "Informe mensual" vencida hace 2 días».
    - «Incidencia #45 fuera de SLA».
- **Hecho:**
  - Línea de tiempo por día con ícono por tipo y filtros por tipo y rango de fechas.
  - Cada evento dice qué, cuándo y sobre qué (con enlace).
  - Paginada.
- **Cabecera del detalle:**
  - último acceso y dispositivos;
  - sesiones activas, con «Cerrar sesiones» si ya existe en la app;
  - acciones por día (sparkline de 30 días).

**Exportar:** Excel con la línea de tiempo del rango elegido, para un usuario o para todos.

### Qué cuenta como «pendiente» por rol

| Rol | Pendientes |
|---|---|
| **Terapeuta** | sesiones pasadas en `scheduled` sin completar ni cancelar · sesiones completadas sin notas o sin juegos asignados (si el centro lo exige) · tareas asignadas vencidas o sin mover en 7 días · incidencias asignadas abiertas (y fuera de SLA) · solicitudes suyas rechazadas sin leer · su nómina por cobrar (PRP 008), solo informativo |
| **Admin / supervisor** | solicitudes por aprobar · restablecimientos de contraseña por revisar · incidencias sin asignar o fuera de SLA · pagos «sin clasificar» del Excel (PRP 008) · nóminas vencidas de terapeutas · comprobantes leídos sin registrar |
| **Paciente** | cuotas vencidas · juegos asignados sin jugar · sesiones de la semana sin confirmar (si se usa la confirmación) · perfil incompleto (sin apoderado, sin correo real, sin teléfono) |

Cada regla es una función `pending_<tipo>(user)` en un registro, igual que los tipos de notificación (PRP 011). Agregar una regla nueva es agregar una entrada.

### Diseño técnico

**1. Línea de tiempo: dos fuentes.**

- **Derivada:** se lee de las tablas que ya existen (tabla de arriba) con una consulta por fuente, unida y ordenada por fecha. Sin duplicar datos.
- **Nueva:** tabla `activity_event`. Guarda solo las acciones de escritura que no dejan rastro, con estos campos:
  - quién: `user_id`, `role`;
  - qué: `action` (`patient.updated`, `contract.updated`, `drive.deleted`, `settings.changed`…), `entity_type`, `entity_id`, `summary` (texto corto sin datos sensibles);
  - desde dónde: `ip`;
  - cuándo: `created_at`.

  Se escribe con un `after_request` **solo** en `POST/PUT/PATCH/DELETE` exitosos de rutas de una **lista blanca**, mapeadas a `action`. **Nunca se guarda el cuerpo de la petición.**
- **Retención:** 180 días, que se borran con un job nocturno.

**2. Pendientes, calculados al momento:**

- Con caché de 60 s por usuario y conteos baratos (`COUNT` con índices).
- La lista usa una sola consulta agregada por tipo de pendiente para todos los usuarios, nunca N consultas por usuario.

**3. API (solo admin):**

- `GET /admin/api/activity/users?role=&sede=&only_pending=`: lista con conteos.
- `GET /admin/api/activity/users/<id>/pending`.
- `GET /admin/api/activity/users/<id>/timeline?from=&to=&types=&page=`.
- `GET /admin/api/activity/export.xlsx?user_id=&from=&to=`.

**4. Privacidad:**

- **Sin contenido de mensajes, notas clínicas ni contraseñas.** El `summary` describe la acción («Editó el perfil de «P1»»), no los datos.
- **Cada consulta del módulo queda registrada** como `activity.viewed` (quién miró a quién).
- **Solo admin.** El supervisor ve solo su sede, si se aprueba.

### Success Criteria

- [ ] Configuración → Actividad lista a todos los usuarios con último acceso, acciones de 7 días y pendientes. Ordena por pendientes vencidos y carga en menos de 1 s con 100 usuarios.
- [ ] El detalle muestra «Pendiente» y «Hecho» con enlaces que abren el lugar exacto.
- [ ] Una sesión pasada sin cerrar aparece como pendiente del terapeuta y desaparece al cerrarla.
- [ ] Editar un paciente, un contrato, un archivo del drive o un ajuste queda en la línea de tiempo con `activity_event`, sin el cuerpo de la petición.
- [ ] Exportar a Excel respeta el rango y el usuario.
- [ ] En móvil el detalle es pantalla completa y la línea de tiempo se lee sin desplazamiento horizontal.
- [ ] Tests:
  - cada regla de pendientes por rol;
  - la línea de tiempo une fuentes y ordena;
  - la lista blanca del registro (una ruta no listada no se registra);
  - no se guarda el cuerpo;
  - solo admin;
  - retención.

## Implementation Blueprint

1. **Fase A: pendientes.** Registro `activity_pending.py` con las reglas por rol, `GET …/pending` y la lista con conteos. Esto ya da valor sin tabla nueva.
2. **Fase B: línea de tiempo derivada.** Una función por fuente que devuelve `{at, type, summary, link}`, más la unión y la paginación.
3. **Fase C: `activity_event`.** Modelo, `after_request` con lista blanca, job de retención y registro de `activity.viewed`.
4. **Fase D: UI.**
   - Configuración → Sistema → **Actividad**: lista y detalle con pestañas, responsive.
   - Reutiliza `personLabel`, chips de estado y el panel lateral de Finanzas.
5. **Fase E:** Excel y sparkline.

## Anti-Patterns to Avoid

- ❌ Guardar cuerpos de peticiones o contenido clínico «por si acaso».
- ❌ Registrar cada `GET`: llenaría la base sin valor. Solo escrituras de la lista blanca, más los accesos, que ya existen.
- ❌ Calcular pendientes con N+1 consultas por usuario.
- ❌ Duplicar en `activity_event` lo que ya está en otras tablas (sesiones, pagos, incidencias…).

## Preguntas abiertas

1. ¿El **supervisor** ve este módulo (solo su sede) o solo el admin?
2. ¿Las sesiones completadas **sin notas** cuentan como pendiente del terapeuta? ¿Y sin juegos asignados?
3. ¿Cuánto tiempo guardamos la actividad nueva: 180 días o más?
4. ¿Agregamos **«Cerrar todas sus sesiones»** desde el detalle (útil si alguien pierde el teléfono)?
