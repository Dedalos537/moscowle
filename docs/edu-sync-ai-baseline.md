# Línea de Base de Cumplimiento Técnico y Gestión de Eventos/Incidentes - EduSync AI

Este documento recopila la normativa técnica, buenas prácticas, arquitectura de monitoreo y protocolos de respuesta ante incidentes establecidos para el proyecto **EduSync AI** (Sección 26214 - Curso Integrador II, 2026). Está diseñado con una estructura lógica y semántica optimizada para que un sistema de Inteligencia Artificial (IA) actúe como evaluador de conformidad de cualquier entrega, arquitectura o cambio del proyecto.

---

## CONTEXTO DEL PROYECTO Y METADATOS DE REFERENCIA
* **Nombre del Proyecto (PROY):** EduSync AI
* **Organización Beneficiaria:** Centro de Terapias Juan Pablo II (Entidad sin fines de lucro)
* **Entorno de Producción:** PaaS Railway.app (Contenedores Docker administrados con servidor Gunicorn/eventlet)
* **Base de Datos en Producción:** MySQL 8.0 hospedada en Aiven Cloud (Motor InnoDB con soporte MVCC)
* **Base de Datos de Desarrollo:** SQLite (utilizada previo a la migración estructural)
* **Framework Backend:** Flask (Python)
* **Frontend:** Angular (Cliente stateless que consume endpoints pero no emite métricas de infraestructura)
* **Líder Técnico de Referencia:** Diego Centeno

---

## MÓDULO 1: ESTÁNDAR DE GESTIÓN DE INCIDENTES (MARCO ITIL)

Este módulo establece las reglas de priorización y primeros auxilios técnicos ante fallos críticos en entornos de producción, tomando como referencia el caso de caída de base de datos MySQL.

### 1.1. Matriz de Priorización ITIL
La prioridad de un incidente es una función directa del **Impacto** (grado de afectación del servicio) y la **Urgencia** (velocidad requerida para evitar daños mayores).

$$\text{Prioridad} = \text{Impacto} \times \text{Urgencia}$$

| Urgencia / Impacto | Bajo | Medio | Alto |
| :--- | :--- | :--- | :--- |
| **Alta** | Media | Alta | **CRÍTICA** (Incidente Activo) |
| **Media** | Baja | Media | Alta |
| **Baja** | Baja | Baja | Media |

* **Criterio de Impacto Alto:** Interrupción total del servicio que afecta al 100% de los usuarios activos, comprometiendo procesos críticos del negocio sin alternativa operacional.
* **Criterio de Urgencia Alta:** Amenaza de daño reputacional irreversible o pérdidas financieras directas debido a la inactividad durante picos de tráfico (ej. temporada de rebajas o picos de atención).

### 1.2. Protocolo de Respuesta Técnica de 3 Pasos del DBA
Ante un incidente de prioridad **CRÍTICA** (ej. caída de base de datos MySQL con Error 500 y usuarios concurrentes bloqueados), se debe ejecutar rigurosamente la siguiente secuencia de diagnóstico, mitigación (workaround) y escalamiento:

#### Paso 1: Diagnóstico Inicial (Sin asumir causas)
* **Acciones:**
  1. Verificar la ubicación y leer el archivo de registro de errores de MySQL para identificar el mensaje exacto.
  2. Comprobar el estado del proceso del sistema de base de datos.
* **Comandos de referencia:**
  ```sql
  -- Verificar ubicación del log
  SHOW VARIABLES LIKE 'log_error';
  ```
  ```bash
  -- Leer las últimas 100 líneas del log de errores
  tail -n 100 /var/log/mysql/error.log

  -- Comprobar estado del servicio
  systemctl status mysql
  ```

#### Paso 2: Solución Temporal (Workaround) Inmediata
* **Acciones:**
  1. Intentar reiniciar el servicio de base de datos para restablecer la operación en el menor tiempo posible.
  2. Si el servicio no levanta, verificar el estado de los recursos de infraestructura subyacente (espacio en disco y memoria RAM).
* **Comandos de referencia:**
  ```bash
  -- Reiniciar el servicio
  systemctl restart mysql

  -- Verificar espacio en disco disponible
  df -h

  -- Verificar memoria RAM libre
  free -m
  ```

#### Paso 3: Escalamiento y Comunicación
Si el servicio no se restablece en un plazo **menor a 5 minutos**, o se detecta una condición técnica que excede la autoridad del operador, se activa el protocolo de escalamiento:

| Tipo de Escalamiento | Criterio de Activación | Ruta de Escalamiento |
| :--- | :--- | :--- |
| **Funcional** | Detección de corrupción de datos física o lógica en la base de datos | Soporte N1 $\rightarrow$ DBA $\rightarrow$ Arquitecto de Base de Datos |
| **Jerárquico** | Superación de los tiempos de respuesta del SLA o fallo de workaround | Notificación inmediata al Gerente de TI / Director Técnico |

### 1.3. Requisitos Obligatorios del Registro del Ticket
El ticket del incidente debe abrirse en el **primer minuto** del fallo para garantizar la trazabilidad. Debe contener obligatoriamente:
1. **Identificador único** del incidente.
2. **Instancia afectada:** (producción, staging, etc.).
3. **Hora de inicio** exacta del incidente.
4. **Número de usuarios impactados** (métricas de concurrencia).
5. **Logs de error adjuntos** (MySQL Error Log o stack traces).

---

## MÓDULO 2: ARQUITECTURA DE MONITOREO DE EVENTOS

La estrategia de monitoreo de EduSync AI está diseñada bajo un enfoque **agentless** y basada en el **Principio de Accionabilidad** (toda alerta enviada al equipo de operaciones debe requerir obligatoriamente una acción humana correctiva, mitigando la fatiga de alertas).

### 2.1. Arquitectura de Flujo de Eventos
1. **Fuentes de Eventos:** Código de la aplicación Flask (Gunicorn/eventlet), MySQL 8.0 en Aiven Cloud, módulo de tareas programadas (`tasks.py` / APScheduler) y el componente interno de detección clínica `CrisisMonitor`.
2. **Mecanismo de Recolección (Agentless):**
   * El SDK de **Sentry** integrado en el código Python intercepta excepciones en tiempo real.
   * La plataforma **Railway.app** recopila de forma nativa la telemetría de infraestructura del contenedor Docker.
3. **Almacenamiento y Procesamiento:**
   * Sentry Backend clasifica y agrupa los errores.
   * El motor de métricas de Railway almacena series temporales (CPU, RAM, disco y latencia) por un histórico de **30 días**.
4. **Visualización Central:**
   * Railway Dashboard (Observability/Metrics) para salud de hardware.
   * Sentry Dashboard para errores a nivel de aplicación.

### 2.2. Justificación de Herramientas frente a Alternativas
* Se **descartó Datadog** debido a restricciones presupuestarias del proyecto al ser el Centro de Terapias Juan Pablo II una organización sin fines de lucro.
* Se **descartó la combinación Prometheus/Grafana** para el despliegue de infraestructura, ya que al utilizar un PaaS (Railway) con contenedores Docker administrados, la plataforma expone de forma nativa métricas de CPU, RAM, disco y tiempo de respuesta sin requerir agentes adicionales ni mantenimiento de infraestructura de monitoreo.

---

## MÓDULO 3: MATRIZ DE UMBRALES, ALERTAS Y MÁQUINAS DE ESTADOS

Este módulo define las métricas críticas del sistema de producción, sus rangos normales (línea base) y los niveles de umbral de alerta que dictan las acciones inmediatas.

### 3.1. Matriz de Métricas Críticas de Infraestructura y Aplicación

| Métrica de Servicio | Línea Base (Normal) | Umbral WARNING (Zona Amarilla) | Umbral ERROR/CRITICAL (Zona Roja) | Acción Remediativa Asociada |
| :--- | :--- | :--- | :--- | :--- |
| **Utilización de CPU** (Railway.app) | 18% promedio (mín. 5% - pico 48%) | $\ge 70\%$ | $\ge 80\%$ | Escalar réplicas en Railway (Scale-Out) y notificar al líder técnico. |
| **Uso de Memoria RAM** (Gunicorn + ORM + Modelos SVM) | 52% promedio (mín. 35% - pico 75%) | $\ge 80\%$ | $\ge 90\%$ | Ampliar la memoria dinámica asignada al contenedor y generar alerta técnica. |
| **Uso de Disco** (BD, uploads, modelo SVM) | 22% promedio (mín. 12% - pico 28%) | $\ge 80\%$ | $\ge 85\%$ | Limpiar registros/logs antiguos e imágenes/audios temporales; ampliar volumen de almacenamiento. |
| **Tiempo de Respuesta de la API** | 0.35 s promedio (mín. 0.08 s - pico 1.2 s) | $\ge 2.0$ segundos | $\ge 3.0$ segundos | Activar almacenamiento en caché vía Redis y optimizar las consultas (queries) SQL del ORM. |

*Nota técnica: El health check de la aplicación (`GET /api/health`) debe responder idealmente en un promedio de 68 ms confirmando `{ "status": "ok", "database": "connected" }`.*

### 3.2. Cálculo de Capacidad por Teoría de Colas (Ley de Utilización)
Los umbrales y escalamientos del proyecto se dimensionan aplicando rigurosamente la **Ley de Utilización**:

$$U = \frac{\lambda \times S}{C}$$

Donde:
* $U$ = Tasa de utilización del sistema (Meta de operación: $< 75\%$).
* $\lambda$ = Tasa de solicitudes por segundo (Tasa de llegada).
* $S$ = Tiempo promedio de servicio por solicitud (en segundos).
* $C$ = Número de núcleos de CPU (Capacidad).

**Caso de Estudio de Sobrecarga:**
* Con la carga pico actual en un entorno básico de 2 núcleos ($\lambda = 25$ req/s, $S = 0.12$ s, $C = 2$ vCPU):
  $$U = \frac{25 \times 0.12}{2} = 1.50 \quad (150\% \text{ de utilización, sistema colapsado y con encolamiento infinito})$$
* **Sustento del Plan de Escalamiento:** Para garantizar el cumplimiento de la meta de utilización ($U \le 75\%$), el sistema debe escalar a un mínimo de 6 vCPU ($C = 6$):
  $$U = \frac{25 \times 0.12}{6} = 0.50 \quad (50\% \text{ de utilización, operación segura y estable})$$

---

## MÓDULO 4: POLÍTICAS DE DETECCIÓN, ESCALAMIENTO Y AUTO-RECUPERACIÓN

Se documenta la cadena de mando operativa organizada en tres niveles de escalamiento, junto con los planes de acción ante eventos anómalos.

### 4.1. Cadena de Escalamiento de Eventos de Monitoreo

| Nivel | Tipo de Evento | Criterio Técnico | Responsable | Canal de Notificación | Tiempo Máx. de Respuesta |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Nivel 1** | **Advertencia (Warning)** | Cualquier métrica en zona Amarilla (CPU $\ge 70\%$, RAM $\ge 80\%$, disco $\ge 80\%$, respuesta API $\ge 2.0$ s). | Líder Técnico (Diego Centeno) | Alerta automática por correo electrónico / Dashboard de Railway. | 30 minutos |
| **Nivel 2** | **Error / Crítico Técnico** | Cualquier métrica en zona Roja (CPU $\ge 80\%$, RAM $\ge 90\%$, disco $\ge 85\%$, respuesta API $\ge 3.0$ s) o detección de errores HTTP 500 persistentes. | Equipo de TI + Oficial de Seguridad | Alertas en tiempo real en Sentry + Notificaciones automáticas de Railway. | 1 hora hábil |
| **Nivel 3** | **Incidente Crítico de Negocio** | Falla de `/api/health` tras 3 intentos, error 500 en login de administradores o caída de módulos clínicos críticos durante ventana de cambio. | Diego Centeno (Líder Técnico) | Activación de Plan de Reversión inmediata + Notificación directa a la Dirección de la organización. | Máximo 3 horas de tolerancia (Rollback ejecutable en 55 min). |

### 4.2. Procedimiento de Acción Post-Evento (Estructura de 4 Pasos)
Cuando ocurre una anomalía (ej. detección de excepciones concurrentes `database is locked` por el uso de SQLite en transacciones de citas concurrentes), el equipo debe seguir este ciclo de resolución:

```
[Detección Automática] ──> [Mitigación Estructural] ──> [Validación y Smoke Tests] ──> [Reporte y Cierre]
```

1. **Detección (Automática):** Sentry captura la excepción con el stack trace detallado, y el panel de Railway correlaciona la saturación de CPU con las solicitudes sobre el endpoint afectado (ej. `POST /api/citas`).
2. **Mitigación (Manual de Alto Riesgo):** Ejecución de cambios estructurales planificados mediante un plan de implementación detallado (ej. migración de motor SQLite a MySQL 8.0 InnoDB en Aiven Cloud para soportar concurrencia mediante control de concurrencia multiversión - MVCC), siguiendo un RFC (Request for Comments) aprobado y con respaldo previo.
3. **Validación (Smoke Test Post-Despliegue):** Realización de pruebas básicas de salud del sistema:
   * Consumir `curl /api/health` esperando HTTP 200 OK y conectividad DB estable ($< 200$ ms).
   * Probar login con los tres roles principales.
   * Realizar pruebas CRUD en pacientes.
   * Monitorear Sentry durante las 72 horas posteriores al cambio buscando cero errores críticos.
4. **Reporte:** Documentar los criterios de éxito del despliegue en la bitácora del proyecto y cerrar formalmente la solicitud de cambio (RFC).

---

## MÓDULO 5: RECOMENDACIONES DE SEGURIDAD Y MEJORA OPERATIVA

Para mantener la robustez del proyecto, la arquitectura debe ser auditada frente a las siguientes 4 buenas prácticas operativas:

1. **Principio de Privilegio Mínimo mediante RBAC (Role-Based Access Control):**
   * Control de accesos a nivel de endpoint en el backend.
   * Restricciones lógicas basadas en datos: cada terapista solo puede acceder a las citas de sus propios pacientes asignados (filtrado estricto por `therapist_id` en el ORM).
   * Separación física de funciones en módulos diferenciados para los roles de **Administrador**, **Terapista** y **Operador**, asegurando que ningún rol clínico acceda a funciones de configuración del sistema o creación de usuarios fuera de su rol.
2. **Monitoreo como Código (Observability as Code):**
   * Automatización del pipeline de integración y despliegue continuo (CI/CD) mediante **GitHub Actions**.
   * Resguardo y control de variables de entorno críticas de forma encriptada (`SQLALCHEMY_DATABASE_URI`, `SECRET_KEY`, etc.).
   * *Mejora pendiente:* Versionar los umbrales de alerta directamente en repositorios de código (ej. reglas de alerta de Prometheus/Railway).
3. **Pruebas de Inyección de Fallas:**
   * Simulación y validación continua en entornos de prueba para estresar el sistema.
   * Inyección de carga pesada concurrente (ej. 25 req/s en endpoints analíticos como `/api/analytics`) para verificar si las alertas de CPU Warning se disparan según lo diseñado.
   * Inyección de transacciones concurrentes bloqueantes para auditar la tolerancia de base de datos a bloqueos de escritura.
4. **Mejora Continua de Umbrales:**
   * Ajuste periódico de los límites de alertas (Warning/Critical) basado en análisis de capacidad reales (ej. Ley de Utilización) y el crecimiento de la base de usuarios activos (personal terapéutico).

---

## GUÍA DE EVALUACIÓN PARA IA (CHECKLIST DE CUMPLIMIENTO)

Si estás utilizando esta base de conocimientos para evaluar un proyecto de software, puedes usar el siguiente checklist estructurado de cumplimiento técnico.

### Checklist de Evaluación

- [ ] **A1: Gestión de Incidentes (Matriz ITIL):** ¿El proyecto define explícitamente sus incidentes críticos combinando Impacto Alto y Urgencia Alta?
- [ ] **A2: Diagnóstico y Workaround:** ¿Existe un protocolo claro de tres pasos (Diagnosticar $\rightarrow$ Aplicar Workaround $\rightarrow$ Escalar) para las caídas de base de datos o API?
- [ ] **B1: Arquitectura de Monitoreo:** ¿El esquema de monitoreo es centralizado, agentless (donde sea viable) y sigue el principio de accionabilidad para evitar la fatiga de alertas?
- [ ] **B2: Umbrales Técnicos:** ¿Se especifican niveles de alerta Warning (Amarillo) y Critical (Rojo) para CPU, RAM, Disco y Tiempo de Respuesta con acciones remediativas claras?
- [ ] **B3: Teoría de Capacidad:** ¿Se calculan los umbrales o capacidades de los servidores usando la Ley de Utilización para evitar colapsos por sobrecarga concurrente?
- [ ] **C1: Cadena de Escalamiento:** ¿Se definen al menos 3 niveles de escalamiento con responsables específicos, canales y tiempos máximos de respuesta de negocio?
- [ ] **C2: Criterios de Rollback:** ¿Están establecidos de forma medible los criterios técnicos que obligan a realizar un Rollback (ej. caída de health check tras 3 intentos)?
- [ ] **C3: Ciclo Post-Evento:** ¿Se ejecutan los pasos de Detección, Mitigación, Validación (Smoke Test) y Reporte de forma secuencial?
- [ ] **D1: Privilegio Mínimo:** ¿Se aplica RBAC y filtrado de datos a nivel de consulta de base de datos (ej. `therapist_id` para aislar datos sensibles clínicos)?
- [ ] **D2: Inyección de Fallas:** ¿El equipo de desarrollo valida las alertas inyectando cargas y fallas intencionales en entornos controlados?
