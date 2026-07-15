# Informe de Cumplimiento — EduSync AI vs Línea de Base Técnica

**Fecha:** 2026-07-14
**Evaluado por:** Gentle AI (SDD Orchestrator)
**Fuente:** `docs/edu-sync-ai-baseline.md`
**Alcance:** Backend `app/` + Frontend `edysync/`

---

## Resumen General

| Estado  | Ítems |
|---------|-------|
| ✅ **Cumple** | 3 |
| ⚠️ **Parcial** | 7 |
| ❌ **No implementado** | 3 |

---



## A1 — Gestión de Incidentes (Matriz ITIL)

**Estado: ⚠️ PARCIAL**

**✔️ Lo que existe:**
- Modelo `Incidente` completo con `prioridad` (1–4), `categoria`, `estado`, `escalamiento_nivel`, `fecha_limite_sla`
- `CrisisMonitor` con detección automática (DB connections, brute force, latency) y creación de incidentes
- `IncidentDetectionService` con chequeos diarios y en tiempo real (bajo cumplimiento, gaps de scheduling, latencia API, errores de modelo, SLA vencidos)
- `IncidentEscalationService` con SLA configurable por categoría y prioridad
- `IncidentNotificationService` con notificaciones vía Slack, Email, Telegram
- Dashboard de incidentes en frontend (`IncidentService` en Angular)
- `IncidenteHistorial` y `IncidenteComentario` para trazabilidad completa

**❌ Lo que falta:**
- La matriz ITIL del baseline define `Prioridad = Impacto × Urgencia`, pero el código implementa un sistema simplificado de prioridad 1–4 sin combinar explícitamente impacto y urgencia
- No hay una correspondencia explícita en código entre la matriz (Alto×Alta → Crítica, etc.) y el campo `prioridad`
- El protocolo de 3 pasos documentado (Diagnosticar → Workaround → Escalar) no está codificado como procedimiento ejecutable; existe como comportamiento implícito de los servicios pero no como workflow formal

**Recomendación:** Documentar la correspondencia entre la matriz ITIL y los valores de `prioridad` en los modelos. Opcional: agregar un decorador o FSM que guíe el flujo diagnóstico → mitigación → escalamiento.

---

## A2 — Diagnóstico y Workaround (Protocolo de 3 Pasos)

**Estado: ⚠️ PARCIAL**

**✔️ Lo que existe:**
- Health endpoint `/api/health` con chequeo de DB, Groq, Gemini, Ollama y alertas del CrisisMonitor
- Docker HEALTHCHECK con 3 reintentos y 30s de intervalo
- Railway `healthcheckPath: /api/health` con timeout de 100s
- Error handlers globales (400, 403, 404, 429, 500, Exception no manejada)
- Logging con rotación y formato JSON
- `before_request` captura request_id, duración, user_id para trazabilidad

**❌ Lo que falta:**
- No hay un **workflow procedural explícito** Diagnóstico → Workaround → Escalamiento documentado como código
- Los comandos de referencia del baseline (`SHOW VARIABLES LIKE 'log_error'`, `systemctl status mysql`, `tail -n 100 /var/log/mysql/error.log`) no tienen equivalente en Railway.app (no hay acceso a shell del servidor MySQL en Aiven)
- El paso de "Solución Temporal Inmediata" (reinicio de servicio) no está automatizado — no hay un `/api/health/restart-db` o mecanismo similar

**Recomendación:** Crear un runbook digital o script de diagnóstico ejecutable vía CLI (`flask diagnose-db`) que automatice los pasos 1 y 2 del protocolo.

---

## B1 — Arquitectura de Monitoreo (Agentless, Accionabilidad)

**Estado: ✅ CUMPLE**

**✔️ Lo que existe:**
- **Sentry SDK** integrado en `__init__.py` (líneas 380–398) con FlaskIntegration y sample rate configurable
- **Métricas in-memory** via `MetricsCollector` en `middleware/metrics_middleware.py` (latencia, status codes, DB queries, conteos)
- **Railway native metrics** para CPU, RAM, disco (accesibles vía Railway Dashboard)
- **CrisisMonitor** con chequeos periódicos y alertas multicanal (Slack, Telegram, Email)
- **IncidentDetectionService** ejecutándose cada 15 min (realtime) y diario
- Sin necesidad de agentes externos — todo es SDK/librería

**❌ Lo que falta:**
- Nada significativo. El diseño agentless con Sentry + Railway cumple el requisito.

---

## B2 — Umbrales Técnicos (Warning/Critical)

**Estado: ⚠️ PARCIAL**

**✔️ Lo que existe:**
- `ALERT_DB_CONN_THRESHOLD` (default: 50 conexiones)
- `ALERT_BRUTE_FORCE_THRESHOLD` (default: 20 intentos en 15 min)
- CrisisMonitor detecta: latencia API > p95 800ms, conexiones DB > threshold, brute force
- Métricas de latencia, conteo de requests y errores en MetricsCollector
- Logs con rotación y niveles configurables (`LOG_LEVEL`)

**❌ Lo que falta:**
- Los umbrales de **CPU** (≥70% Warning, ≥80% Critical), **RAM** (≥80% Warning, ≥90% Critical) y **Disco** (≥80% Warning, ≥85% Critical) del baseline **no están implementados en código**. Estos dependen exclusivamente del observability nativo de Railway
- No hay un mecanismo programático para alertar cuando CPU/RAM/disco exceden los umbrales definidos — no hay polling a Railway API ni webhook de Railway hacia el CrisisMonitor
- El threshold de **tiempo de respuesta API** (≥2.0s Warning, ≥3.0s Critical) del baseline difiere del implementado en CrisisMonitor (p95 > 800ms)

**Recomendación:** Implementar un chequeo periódico que consuma las métricas de Railway vía API o Railway CLI y dispare alertas del CrisisMonitor cuando CPU/RAM/disco excedan los umbrales documentados. Estandarizar los thresholds de latencia.

---

## B3 — Teoría de Capacidad (Ley de Utilización)

**Estado: ❌ NO IMPLEMENTADO**

**✔️ Lo que existe:**
- Nada en código. La Ley de Utilización se menciona exclusivamente en el documento baseline como concepto de dimensionamiento

**❌ Lo que falta:**
- No hay cálculos de `U = λ × S / C` en ningún servicio
- No hay auto-scaling basado en utilización
- No hay monitoreo de λ (tasa de llegada de requests) ni S (tiempo promedio de servicio) para alertar sobre capacidad
- No hay recomendaciones dinámicas de escalamiento basadas en la ley

**Recomendación:** Implementar un `CapacityService` que calcule utilización proyectada usando métricas del `MetricsCollector` y emita alertas predictivas antes de llegar a zona roja. Muy bajo esfuerzo, alto valor preventivo.

---

## C1 — Cadena de Escalamiento (3 Niveles)

**Estado: ✅ CUMPLE**

**✔️ Lo que existe:**
- `IncidentEscalationService` con `MAX_ESCALAMIENTO = 2` (3 niveles: 0→1→2)
- SLA configurable por categoría/prioridad (`SLA_HOURS`):
  - SOFTWARE P1: 2h, P4: 48h
  - HARDWARE P1: 4h, P4: 72h
  - OPERACIONES P1: 4h, P4: 96h
  - RED P1: 1h, P4: 24h
  - ACCESOS P1: 2h, P4: 72h
- `IncidenteHistorial` con trazabilidad de cambio de responsable y nivel
- `IncidentNotificationService` notifica en cada escalamiento
- Escalamiento automático cada 15 min vía scheduler (tarea `run_incident_escalation`)
- Escalamiento manual endpoint `POST /api/incidents/check-escalations` (solo admin)
- Tiempos máximos de respuesta implícitos en los SLA

**❌ Lo que falta:**
- Los niveles del baseline (N1=Warning/Líder Técnico/30min, N2=Error/Equipo TI/1h, N3=Crítico/Dirección/3h) no tienen correspondencia 1:1 con los niveles del código (que son más genéricos: N0→N1→N2 con escalamiento basado en SLA)
- No hay canales de notificación diferenciados por nivel (Slack para todos los niveles, el baseline sugiere email para N1, Sentry+email para N2, llamada directa para N3)
- El responsable por defecto para todos los escalamientos es `admin`, sin distinción del tipo de evento

**Recomendación:** Mapear explícitamente los 3 niveles del negocio a los niveles técnicos. Diferenciar canales de notificación por severidad.

---

## C2 — Criterios de Rollback

**Estado: ⚠️ PARCIAL**

**✔️ Lo que existe:**
- Docker HEALTHCHECK con 3 reintentos (retries=3) — equivalente a "falla tras 3 intentos"
- Railway healthcheckPath con timeout configurable
- Railway restartPolicyType: ALWAYS (auto-recovery del contenedor)
- DB session rollback en error handlers (500, Exception)

**❌ Lo que falta:**
- **No hay un plan de rollback documentado ni ejecutable.** Los criterios del baseline ("500 en login de administradores", "caída de módulos clínicos críticos durante ventana de cambio") no tienen triggers automáticos más allá del healthcheck
- No hay mecanismo de feature flags para desactivar módulos problemáticos en producción (el `feature_flags.py` existe pero no está atado a rollback automático)
- No hay versionado de despliegues con `rollback` automatizado (GitHub releases, Railway rollback)

**Recomendación:** Definir un `RollbackService` que evalúe los criterios del baseline post-deploy y pueda desactivar módulos vía feature flags o gatillar un rollback de Railway.

---

## C3 — Ciclo Post-Evento (4 Pasos: Detección → Mitigación → Validación → Reporte)

**Estado: ⚠️ PARCIAL**

**✔️ Lo que existe:**
- **Detección:** CrisisMonitor (automático), IncidentDetectionService (diario/realtime), Sentry (excepciones en vivo)
- **Mitigación:** Creación de incidentes con `fecha_limite_sla`, notificaciones, escalamiento automático
- **Validación:** Health endpoint, E2E tests con Playwright, test suite existente (18 archivos)
- Logging JSON con rotación para trazabilidad

**❌ Lo que falta:**
- **No hay generación de reporte post-evento.** El paso 4 "Reporte y Cierre" no está implementado — no se genera un documento post-mortem automático con hallazgos, acciones tomadas, lecciones aprendidas
- Los **smoke tests post-despliegue** no están automatizados como pipeline CI/CD — los E2E tests existen pero deben ejecutarse manualmente
- No hay verificación de "cero errores críticos en 72h" (chequeo posterior automático)

**Recomendación:** Agregar un flujo `Incidente → PostMortemReport` que genere automáticamente un resumen ejecutivo al cerrar un incidente. Automatizar smoke tests post-deploy en Railway.

---

## D1 — Privilegio Mínimo (RBAC + Filtrado de Datos)

**Estado: ⚠️ PARCIAL**

**✔️ Lo que existe:**
- **Modelo `User` con campo `role`**: admin, terapista, jugador (paciente), supervisor, operador
- **`RoleGuard` en frontend**: verifica rol del usuario antes de activar rutas protegidas
- **Filtrado por `therapist_id` en backend**: la mayoría de queries en `therapist_routes.py` y `patient_routes.py` filtran por `therapist_id` usando el `current_user`
- **`login_required` decorator** en `auth_compat.py`: protege rutas críticas
- **App-Key validation** para acceso a API sin sesión
- **JWT con cookies HttpOnly y SameSite**
- **CSRF protection** habilitado
- **Rate limiting** por endpoint
- **MFA** soportado en modelo de usuario

**❌ Lo que falta:**
- **No hay un decorador `role_required` genérico en el middleware.** Las verificaciones de rol se hacen inline en cada ruta con condiciones ad-hoc (`if current_user.role != 'admin': return 403`), lo que es propenso a errores
- **No hay una matriz de permisos centralizada.** Los permisos se dispersan en 20+ archivos de rutas
- El filtrado estricto por `therapist_id` no es consistente en **todas** las rutas que exponen datos de pacientes — algunas rutas admin pueden retornar datos de todos los therapists sin verificar que el admin tenga permiso explícito
- **No hay separación física de módulos** (Admin, Terapista, Operador) como describe el baseline — todo está en un mismo Flask app blueprint
- El frontend guard de roles en `role.guard.ts` permite "escalamiento" de permisos (ej. admin puede ver rutas de terapista), lo que es intencional pero inconsistente con el principio de privilegio mínimo estricto

**Recomendación:** Crear un decorador `@role_required('admin', 'supervisor')` centralizado. Implementar una `PermissionMatrix` en `middleware/authorization.py` con todas las reglas de acceso.

---

## D2 — Inyección de Fallas

**Estado: ❌ NO IMPLEMENTADO**

**✔️ Lo que existe:**
- `test_security_integration.py`: Pruebas de SQL injection (7 payloads contra login y URL params)
- `test_security_integration.py`: Pruebas de XSS (4 payloads contra endpoints de contacto y chat)
- `test_error_handling.py`: Pruebas de errores HTTP (404, 405, malformed JSON, CORS, security headers)
- Playwright E2E tests para login y accesibilidad

**❌ Lo que falta:**
- **No hay inyección de carga pesada** (el baseline pide "25 req/s en endpoints analíticos como `/api/analytics`")
- **No hay inyección de transacciones concurrentes bloqueantes** para auditar tolerancia de la DB a lock contention
- **No hay chaos engineering** simulado (caída de dependencias, latencia de red, DB timeout)
- **No hay pruebas de estrés** automatizadas con herramientas como Locust, k6 o Artillery
- Las pruebas de seguridad cubren SQLi y XSS básico pero faltan: CSRF bypass, JWT tampering, path traversal, IDOR (Insecure Direct Object Reference)

**Recomendación:** Agregar `test_fault_injection.py` con simulación de:
- Carga concurrente pesada usando `concurrent.futures` o `locust`
- Bloqueo de DB con transacciones lentas
- Timeout de dependencias externas (Groq, Gemini, Ollama)
- IDOR testing contra endpoints de pacientes/citas

---

## Extras Evaluados

### CI/CD (Monitoreo como Código)

**Estado: ❌ NO IMPLEMENTADO**

**❌ Lo que falta:**
- **No existe `.github/workflows/`** — no hay pipeline de GitHub Actions
- No hay integración continua (tests automáticos en cada PR)
- No hay despliegue continuo automatizado
- El baseline específicamente pide: "Automatización del pipeline de CI/CD mediante GitHub Actions" y "Versionar los umbrales de alerta directamente en repositorios de código"

**Recomendación:** Crear workflow de GitHub Actions que ejecute la suite de tests en cada push/PR, y opcionalmente deploy automático a Railway.

### Cache

**Estado: ✅ CUMPLE PARCIAL**

**✔️ Lo que existe:**
- Flask-Caching configurado con `CACHE_TYPE` (simple/redis)
- Soporte Redis vía `CACHE_REDIS_URL`
- El baseline sugiere Redis para optimizar tiempo de respuesta API

**❌ Lo que falta:**
- No se usa cache agresivamente en los endpoints (el baseline sugiere activar caché cuando el tiempo de respuesta supera 2.0s)

---

## Prioridades de Acción

| Prioridad | Ítem | Impacto | Esfuerzo |
|-----------|------|---------|----------|
| 🔴 **Alta** | D1 — Decorador `role_required` y matriz de permisos centralizada | Seguridad | Bajo |
| 🔴 **Alta** | D2 — Pruebas de inyección de fallas y estrés | Robustez | Medio |
| 🔴 **Alta** | CI/CD — GitHub Actions pipeline | Automatización | Medio |
| 🟡 **Media** | B2 — Umbrales CPU/RAM/Disco programáticos contra Railway API | Monitoreo | Bajo |
| 🟡 **Media** | C3 — Reporte post-evento automático | Mejora continua | Bajo |
| 🟡 **Media** | B3 — Cálculo de capacidad por Ley de Utilización | Capacidad | Bajo |
| 🟢 **Baja** | A2 — Runbook de diagnóstico ejecutable | Operaciones | Bajo |
| 🟢 **Baja** | C2 — Rollback automático vía feature flags | Resiliencia | Medio |

---

## Detalle de Archivos Clave Examinados

| Archivo | Propósito |
|---------|-----------|
| `app/__init__.py` | Factory de app, Sentry, Talisman, logging, error handlers, blueprints |
| `app/extensions.py` | Extensiones Flask (SQLAlchemy, JWT, Cache, Mail, etc.) |
| `app/middleware/metrics_middleware.py` | Colector de métricas en memoria con percentiles |
| `app/services/crisis_monitor.py` | Monitor de crisis con alertas multicanal y creación de incidentes |
| `app/services/incident_detection_service.py` | Detección automática de incidencias (diaria/realtime) |
| `app/services/incident_escalation_service.py` | Escalamiento automático con SLA por categoría |
| `app/services/incident_notification_service.py` | Notificaciones Slack/Email para cada estado de incidente |
| `app/models/incidente.py` | Modelo Incidente con SLA, evidencia, historial |
| `app/models/user.py` | Modelo User con roles, sedes, therapists asignados |
| `app/routes/health_routes.py` | Health check con DB, LLMs, crisis alerts |
| `app/routes/incident_routes.py` | CRUD de incidentes con dashboard y escalamiento |
| `app/routes/therapist_routes.py` | Rutas de terapista con filtrado por therapist_id |
| `app/auth_compat.py` | Decorador login_required, current_user proxy |
| `config.py` | Configuración con thresholds de alertas y SLA |
| `railway.json` | Config Railway con healthcheck |
| `Dockerfile` | Build multi-stage con HEALTHCHECK |
| `edysync/src/app/core/guards/role.guard.ts` | Guard de roles en frontend |
| `edysync/src/app/core/services/incident.service.ts` | Servicio Angular para incidentes |
| `edysync/src/app/core/interceptors/auth.interceptor.ts` | Interceptor JWT/CSRF |
| `edysync/src/app/core/interceptors/error.interceptor.ts` | Interceptor de errores HTTP |
| `tests/test_security_integration.py` | Pruebas SQLi y XSS |
| `tests/test_incident_services.py` | Pruebas de SLA y escalamiento |
| `tests/test_metrics.py` | Pruebas del MetricsCollector |
