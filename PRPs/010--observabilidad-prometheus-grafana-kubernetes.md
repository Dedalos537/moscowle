# PRP: Observabilidad con Prometheus + Grafana y viabilidad de Kubernetes

> **Version:** 1.0
> **Created:** 2026-10-20
> **Status:** Fases 1 y 2 implementadas (2026-10-20); Fase 3 (Redis + scheduler) y Kubernetes pendientes
> **Decisiones (2026-10-20, «dale, avanzamos con prometheus y grafana»):**
> - Grafana **solo en la LAN**.
> - Avisos por el **bot del centro** a los admins (notificación + Telegram según preferencias).
> - **Sin Redis ni scheduler aparte** por ahora.
> - **Sin Kubernetes**.
> **Regla de oro:** no romper lo que ya funciona. Ningún paso de este PRP puede afectar:
> - PRP 006: topología host + VM-APP + VM-DB.
> - PRP 008: cobranza, nómina, Excel.
> - PRP 009: opencode/MiMo en `127.0.0.1:4096/4097`.
> - Lo agregado después: escáner y vigilante de impresora en `192.168.122.1:8631`, webhook de deploy, túnel de Cloudflare.

---

## Goal

1. **Saber de verdad cómo está el servidor**:
   - qué servicio cae, cuándo y por qué;
   - con historial de semanas, no de 7 días;
   - con avisos antes de que el usuario lo note (Telegram, que ya existe).
2. **Prometheus + Grafana** como base de métricas, sin reemplazar el panel «Estado del servidor» de Moscowle: el panel sigue y se alimenta de Prometheus cuando esté.
3. **Decidir con datos** si Kubernetes conviene, cuándo y qué partes, y dejar el proyecto listo para dar ese paso sin rehacerlo.

## Why

### Problemas reales encontrados (2026-10-20)

| Hallazgo | Evidencia | Estado |
|---|---|---|
| **El panel marcaba 5 servicios «Detenido» que funcionaban.** Preguntaba a `systemctl` de **VM-APP** por nginx, CUPS, cloudflared y Ollama (viven en el **host**) y por MySQL (vive en **VM-DB**). | captura del panel; `server_monitor.SERVICES` | **Corregido en PR #69**: cada servicio se sondea donde vive (HTTP, TCP, `SELECT 1`, ida y vuelta por el túnel) |
| **429 para toda la clínica.** El limitador cuenta a los usuarios sin sesión por IP; toda la clínica sale por **una** IP pública. El frontend (`/app/`, ~60 archivos por carga) pasaba por el limitador (600/h). | `x-ratelimit-limit: 600`, `retry-after: 2912` el 2026-10-19 | **Corregido en PR #69**: estáticos, `/api/health` y `/api/time` exentos |
| La impresora cambió de IP (DHCP) y CUPS siguió apuntando a la vieja. | `ping 192.168.1.137` → unreachable | **Corregido en PR #65** (vigilante + botón), pendiente correr `setup_scanner.sh` en el host |
| Corte de conexión desde el navegador (`ERR_CONNECTION_TIMED_OUT`) sin explicación: no hay registro de cuándo cayó el túnel ni por cuánto. | consola del usuario, 2026-10-20 | **Sin visibilidad hoy** → lo resuelve este PRP |
| El historial del panel guarda 7 días en MySQL, una foto cada pocos minutos, y no mide latencia, errores HTTP ni la cuota de MiMo. | `ServerSnapshot`, `RETENTION_DAYS = 7` | Este PRP |

### Hardware real (medido en PRP 006; a re-medir en la Fase 0)

| Máquina | CPU | RAM | Disco | Uso |
|---|---|---|---|---|
| Host bare metal (i5-4590T) | 4 núcleos | **7,2 GB** | 98 GB | cloudflared, nginx, socat, **Ollama**, CUPS, escáner, libvirt |
| VM-APP | 2 vCPU | **2 GB** (1,9 GB útiles, **70 % en uso** el 2026-10-20) | 30 GB | gunicorn (eventlet, 1 worker), puente WhatsApp, **opencode ×2** (PRP 009) |
| VM-DB | 1 vCPU | 1,5 GB | 30 GB | MySQL (~540 MB RSS) |
| **Asignado** | | **~6 de 7,2 GB** | | Quedan ~1–1,5 GB libres en el host |

> **Esto define todo el PRP:** hay **un solo equipo físico** con **~1 GB de RAM libre**. Cualquier pieza nueva tiene que caber ahí o requiere hardware.

## Análisis de viabilidad

### Prometheus + Grafana → **VIABLE ahora**, con huella pequeña

| Pieza | Dónde | RAM estimada | Para qué |
|---|---|---|---|
| `node_exporter` | host, VM-APP, VM-DB | ~15 MB c/u | CPU, RAM, disco, red, systemd (`--collector.systemd` solo en el host) |
| `mysqld_exporter` | VM-DB | ~20 MB | conexiones, consultas lentas, buffer pool |
| `blackbox_exporter` | host | ~20 MB | sondas: dominio público (túnel), `/app/`, CUPS 631, Ollama, escáner 8631 |
| métricas de `cloudflared` | host (`--metrics 127.0.0.1:2000`) | 0 (ya corre) | estado del túnel, reconexiones, errores |
| `/metrics` de Flask (`prometheus-flask-exporter`) | VM-APP, **solo red interna** | ~10 MB en el proceso | latencia y códigos HTTP por ruta, 429, errores 5xx, duración de MiMo, cuota |
| **Prometheus** | **host** (cerca de todo y fuera de VM-APP, que está al 70 %) | **150–250 MB** con retención de 30 días y scrape cada 30 s | almacenamiento de métricas |
| **Alertmanager** | host | ~30 MB | avisos a Telegram (bot existente) y correo |
| **Grafana** | host | **100–150 MB** | tableros |
| **Total** | | **~400–500 MB** | Entra en lo libre del host, con poco margen |

Condiciones para que sea seguro:

- **Todo escucha solo en `127.0.0.1` o `192.168.122.1`**: nada nuevo a internet.
- **Grafana:**
  - Se ve por la LAN (`http://192.168.1.249:3000`).
  - Desde fuera, solo detrás de **Cloudflare Access** (correo del admin), nunca abierto.
- **El panel de Moscowle no depende de Prometheus:**
  - Si Prometheus está, el backend le consulta (servidor a servidor, solo admin) para las gráficas de 24 h / 7 d / 30 d.
  - Si no está, sigue con `ServerSnapshot` como hoy.
- **Límites de recursos:**
  - Prometheus con `--storage.tsdb.retention.size=2GB`.
  - Grafana y Prometheus con `MemoryMax` en systemd (300 MB y 200 MB), para que nunca le quiten memoria a Ollama ni a las VMs.
- **Docker no es requisito:** binarios oficiales con systemd, igual que el resto del host. Si ya se usa Docker en el host, se puede con `docker compose`, pero con los mismos límites.

### Kubernetes → **NO viable hoy**; viable más adelante, por partes y con requisitos

**Por qué hoy no:**

1. **Un solo nodo físico.** Kubernetes aporta alta disponibilidad, autoescalado y despliegues sin corte *entre varias máquinas*. Con un nodo, si el equipo cae, cae todo igual; solo se suma complejidad.
2. **RAM.**
   - k3s, la distribución más liviana, consume ~500–800 MB solo en el plano de control, más el runtime de contenedores.
   - Hoy hay ~1 GB libre, y Prometheus + Grafana se llevan la mitad.
   - Meterlo dentro de VM-APP (2 GB, ya al 70 %) dejaría sin memoria al backend y a opencode.
3. **Partes que no se pueden mover a pods** (y no deben):
   - **CUPS, el escáner y la impresora:** dependen del hardware y de la LAN del host (WSD/SANE, `lpadmin`).
   - **Ollama:** usa la CPU y RAM del host y su caché de modelos.
   - **MySQL:** un solo nodo con su disco; en Kubernetes de un nodo no gana nada y arriesga datos.
   - **El puente WhatsApp:** un solo dueño de la sesión (`test_whatsapp_bridge_ownership.py`); dos réplicas se pisan.
   - **opencode (PRP 009):** aislado por usuarios de systemd; en pods habría que rehacer el aislamiento.
4. **La app aún no es «sin estado», que es el requisito para tener varias réplicas:**
   - **Socket.IO:** eventlet con 1 worker y sesiones en memoria. Con 2 réplicas, sin `message_queue` (Redis) y sin sesiones fijas, vuelve el bug de los 400 en `/socket.io` que ya vimos.
   - **Limitador y cachés:** viven en memoria (`RATELIMIT_STORAGE_URL = 'memory://'`). Cada réplica tendría su propio límite.
   - **APScheduler:** los jobs (renovables 00:20, cierre de nómina, recordatorios, vigilancia) corren dentro del proceso web. Con 2 réplicas se ejecutan **dos veces**: cuotas y avisos duplicados.
   - **Archivos:** drive, vouchers y escaneos se guardan en el disco de VM-APP. Haría falta almacenamiento compartido.
   - **Sesiones de opencode por usuario:** viven en memoria (`opencode_agent._sessions`).

**Cuándo sí conviene** (compuertas medibles con Prometheus, Fase 1):

- **Hardware:** un segundo equipo o más RAM (≥ 16 GB en el host). Sin esto, no.
- **Carga:** CPU p95 de VM-APP > 70 % sostenido o latencia p95 > 1 s en horas pico durante 2 semanas.
- **Despliegues:** necesidad real de deploy sin corte. Hoy cada deploy reinicia `moscowle`, unos segundos.

**Camino seguro hacia Kubernetes** (sin romper nada, cada paso útil por sí solo):

| Paso | Qué | Beneficio aunque nunca llegue Kubernetes |
|---|---|---|
| K1 | **Redis** (VM-APP o host, ~30 MB): `SocketIO(message_queue=…)`, `RATELIMIT_STORAGE_URL=redis://`, caché | Límites y sockets correctos con más de un worker; permite subir a 2 workers de gunicorn |
| K2 | **Scheduler aparte**: un servicio `moscowle-worker` (mismo código, `RUN_SCHEDULER=1`) y el web con `RUN_SCHEDULER=0` | Los jobs no se duplican; el web reinicia sin cortar jobs |
| K3 | **Archivos fuera del proceso**: `UPLOAD_FOLDER` y drive en un volumen (VM-APP o NFS del host); opcional MinIO | Respaldo simple; habilita réplicas |
| K4 | **Imagen de contenedor única** (ya hay `Dockerfile`) probada en CI con los mismos tests | Despliegues reproducibles; rollback por versión de imagen |
| K5 | **Piloto k3s en una VM nueva (`VM-K8S`)**, solo con el **web sin estado** detrás del túnel, con un peso de tráfico mínimo o en un subdominio de staging | Se aprende sin tocar producción |
| K6 | Si las compuertas lo justifican: migrar el web a k3s, con MySQL, CUPS, escáner, Ollama, WhatsApp y opencode **fuera**, como servicios externos | Escalado del web |

## What (alcance de este PRP)

**Entra:**

- Fase 0: medir.
- Fase 1: Prometheus + exporters + Alertmanager + Grafana.
- Fase 2: el panel de Moscowle lee de Prometheus.
- Fase 3: K1 y K2, preparación sin Kubernetes.

**No entra:** instalar Kubernetes (K5/K6). Se reevalúa con los datos de 4 semanas de Prometheus y la compuerta de hardware.

### Success Criteria

- [ ] El panel «Estado del servidor» no marca caído nada que funcione, y sí marca lo que cae (sondas de PR #69 verificadas en producción).
- [ ] Prometheus guarda 30 días con ≤ 2 GB de disco; Grafana y Prometheus nunca superan su `MemoryMax`.
- [ ] Llegan avisos a Telegram en ≤ 2 min cuando:
  - el túnel cae;
  - `/api/health` falla 3 veces seguidas;
  - VM-APP pasa del 90 % de RAM;
  - el disco pasa del 85 %;
  - la impresora o el escáner no responden 15 min;
  - MiMo entra en pausa por cuota;
  - aparece una racha de 5xx o de 429.
- [ ] Grafana con tableros:
  - Visión general.
  - Host y VMs.
  - Backend: latencia y errores por ruta.
  - Base de datos.
  - Túnel y dominio.
  - IA: Ollama, MiMo, cuota.
  - Impresora y escáner.
- [ ] Ningún puerto nuevo abierto a internet (`ss -ltnp` en host y VMs revisado).
- [ ] Sin cambios funcionales en cobranza, MiMo, Drive, impresión ni escaneo (suite completa verde en CI).
- [ ] Con K1+K2: gunicorn con 2 workers sin errores de Socket.IO ni jobs duplicados (test de doble ejecución).

## All Needed Context

### Topología y puertos actuales (no tocar)

| Servicio | Máquina | Escucha |
|---|---|---|
| cloudflared | host | saliente; métricas a `127.0.0.1:2000` (Fase 1) |
| socat `moscowle-fwd` | host | `127.0.0.1:5000` → VM-APP `:5000` |
| nginx (frontend LAN `/app/`) | host | `:80` |
| CUPS | host | `:631` |
| Ollama | host | `:11434` (ufw: solo `virbr0`) |
| `moscowle-scand` (escáner e impresora) | host | `192.168.122.1:8631` (token) |
| gunicorn `moscowle` | VM-APP | `:5000` |
| opencode chat / dev | VM-APP | `127.0.0.1:4096` / `:4097` |
| MySQL | VM-DB | `192.168.122.20:3306` |

### Puertos nuevos (todos internos)

| Servicio | Escucha | Acceso |
|---|---|---|
| Prometheus | host `192.168.122.1:9095` (el 9090 es de **Cockpit**) | Grafana local; backend vía `192.168.122.1:9095` con ufw solo desde `192.168.122.10` |
| Alertmanager | host `127.0.0.1:9093` | Prometheus |
| Grafana | host `192.168.1.249:3000` (LAN) | admin; desde fuera solo con Cloudflare Access |
| node_exporter | host `127.0.0.1:9100`, VM-APP y VM-DB en su IP de `virbr0` `:9100` | Prometheus |
| mysqld_exporter | VM-DB `192.168.122.20:9104` | Prometheus |
| blackbox_exporter | host `127.0.0.1:9115` | Prometheus |
| `/metrics` de Flask | VM-APP `:5000/metrics` **bloqueado en el túnel** (nginx/socat no lo reenvía; o token) | Prometheus |

> **Ojo con el puerto 9100.** Es también el puerto **RAW de la impresora** (`socket://192.168.1.233:9100`). No hay conflicto: uno está en el host y el otro en la impresora. Aun así, el `node_exporter` del host escucha solo en `127.0.0.1` para no confundir sondas.

### Archivos

- `app/services/server_monitor.py`: sondas por topología (PR #69). La Fase 2 agrega `prometheus_query()`.
- `app/tasks.py`: scheduler. K2: `RUN_SCHEDULER`.
- `app/__init__.py`: `socketio.init_app(..., async_mode='eventlet')`. K1: `message_queue`.
- `config.py:230`: `RATELIMIT_STORAGE_URL`.
- `app/extensions.py:29`: clave del limitador (usuario o IP).
- `deploy/opencode/*`, `deploy/scanner/*`: patrón de instalación a seguir (instalador idempotente + systemd endurecido).

## Implementation Blueprint

### Fase 0 — Medir antes de instalar (1 día, solo lectura)

1. **En el host:**
   - `free -h`, `nproc`, `df -h`, `systemd-cgtop -n 3`.
   - `ss -ltnp`.
   - `systemctl list-units --type=service --state=running`.
2. **En VM-APP y VM-DB:** lo mismo.
3. **Registrar** en este PRP la RAM libre real.
4. **Compuerta:** si en el host quedan **< 700 MB libres** con todo corriendo, Grafana va **dentro de Prometheus** (solo Prometheus + Alertmanager con avisos a Telegram) y los tableros se ven en el panel de Moscowle (Fase 2) hasta tener más RAM.

### Fase 1 — Stack de métricas (`deploy/observability/`)

1. `setup_observability.sh` para el host, idempotente como `setup_scanner.sh`:
   - descarga binarios oficiales con versión fija y suma SHA256;
   - crea usuarios de sistema;
   - instala unidades systemd endurecidas con `MemoryMax`;
   - agrega reglas ufw solo para `virbr0`.
2. `setup_node_exporter.sh` para VM-APP y VM-DB, más `mysqld_exporter` en VM-DB con un usuario MySQL de solo lectura (`PROCESS, REPLICATION CLIENT, SELECT`).
3. `prometheus.yml`:
   - jobs: `node`, `mysqld`, `flask`, `cloudflared`;
   - `blackbox` con módulos `http_2xx` (dominio público, `/app/`, `/api/health`), `tcp_connect` (CUPS 631, escáner 8631, impresora 9100) e `icmp`.
4. `rules.yml`, alertas del criterio de éxito con `for:` razonable para no avisar por un parpadeo. Alertmanager con receptor Telegram por webhook al bot existente y correo de respaldo.
5. Flask: `prometheus-flask-exporter` con `/metrics` **solo** si la IP de origen es la del host (`192.168.122.1`). Métricas propias:
   - `moscowle_mimo_requests_total{status}` y `moscowle_mimo_blocked`;
   - `moscowle_payments_registered_total`;
   - `moscowle_ratelimit_hits_total`;
   - `moscowle_scheduler_job_seconds{job}`.
6. Grafana: tableros versionados en `deploy/observability/dashboards/*.json`, aprovisionados por archivo (nada a mano).

### Fase 2 — El panel de Moscowle lee de Prometheus

- `server_monitor.history()`:
  - si existe `PROMETHEUS_URL`, consulta `query_range` (CPU, RAM, disco, servicios caídos) para 6 h / 24 h / 7 d / **30 d**;
  - si no, `ServerSnapshot` como hoy.
- Nuevas tarjetas: latencia p95 del backend, 5xx y 429 de la última hora, estado del túnel, cuota de MiMo. Botón «Abrir Grafana» (solo LAN o Access), como «Abrir Cockpit».

### Fase 3 — Preparación para escalar (K1 + K2)

- **K1 Redis:**
  - Instalar en VM-APP (`redis-server`, `bind 127.0.0.1`, `maxmemory 64mb`).
  - `SocketIO(message_queue='redis://127.0.0.1:6379/1')`.
  - `RATELIMIT_STORAGE_URL=redis://127.0.0.1:6379/2`.
  - Test con 2 workers.
- **K2 Scheduler aparte:**
  - `RUN_SCHEDULER` en `app/tasks.py`.
  - Unidad `moscowle-worker.service`.
  - Test que asegure que un job no corre dos veces (lock en BD o Redis).
- Solo después: gunicorn `--workers 2` y medir con Prometheus.

### Fase 4 — Reevaluar Kubernetes (fuera de alcance; decisión con datos)

- Con 4 semanas de métricas: ¿se cumplen las compuertas (carga + hardware)?
- Si sí: PRP aparte para K3–K5 con VM-K8S (k3s) solo para el web sin estado.

## Validation Loop

### Level 1

- `ruff check app tests`; `bash -n deploy/observability/*.sh`; `promtool check config prometheus.yml`; `promtool check rules rules.yml`; `amtool check-config`.

### Level 2

- Suite completa en CI.
- Nuevos: `/metrics` rechaza IPs que no sean el host; `history()` usa Prometheus si está y cae a `ServerSnapshot` si no; job no duplicado con `RUN_SCHEDULER`.

### Level 3 (producción)

- `ss -ltnp` en host y VMs: ningún puerto nuevo en `0.0.0.0` salvo Grafana en la IP LAN.
- `systemctl show prometheus grafana-server -p MemoryCurrent,MemoryMax`.
- Apagar a propósito el escáner 15 min → llega el aviso a Telegram.
- Cortar `cloudflared` 2 min (en horario sin uso) → aviso.
- Medir RAM libre del host antes y después: la diferencia debe ser ≤ 500 MB.

## Anti-Patterns to Avoid

- ❌ Instalar Kubernetes en un solo equipo «para escalar»: no escala, y suma consumo y riesgo.
- ❌ Meter MySQL, CUPS, el escáner, Ollama, WhatsApp u opencode en pods.
- ❌ Subir réplicas o workers sin Redis (K1) ni scheduler aparte (K2): vuelven los 400 de Socket.IO y los jobs duplicados.
- ❌ Exponer Grafana, Prometheus o `/metrics` a internet sin Cloudflare Access.
- ❌ Correr Prometheus o Grafana dentro de VM-APP (ya al 70 % de RAM y con opencode).
- ❌ Alertas sin `for:`: un parpadeo del WiFi de la impresora llenaría Telegram de avisos.
- ❌ Reemplazar el panel de Moscowle por Grafana: el panel queda como vista rápida y Grafana como análisis.

## Preguntas abiertas (para aprobar)

1. ¿Hay presupuesto para **más RAM en el host** (subir a 16 GB es la mejora con mejor costo/beneficio) o para un **segundo equipo**? Sin eso, Kubernetes queda descartado y Grafana podría ir sin servidor propio (Fase 0).
2. ¿Grafana solo en la LAN, o también desde fuera con **Cloudflare Access** (requiere configurar Zero Trust en la cuenta de Cloudflare)?
3. ¿Los avisos van al **mismo bot de Telegram** del centro (a los admins) o a uno aparte de sistemas?
4. ¿Se aprueba la **Fase 3 (Redis + scheduler aparte)** en esta misma etapa? Es la que más ayuda a escalar sin Kubernetes.

## Implementación (2026-10-20)

| Pieza | Archivo |
|---|---|
| Métricas de la app sin dependencias nuevas (el deploy no instala paquetes de pip) | `app/services/app_metrics.py` → `/api/server-monitor/metrics` (token `METRICS_TOKEN`) |
| Avisos de Alertmanager → admins | `/api/server-monitor/alerts` (token `ALERT_WEBHOOK_TOKEN`) → `server_monitor.notify_alerts` |
| Historial del panel desde Prometheus (30 días); si no responde, tabla local | `server_monitor.history` / `prometheus_history` |
| Configuración validada con `promtool` y `amtool` oficiales | `deploy/observability/{prometheus,rules,alertmanager,blackbox}.yml` |
| Grafana aprovisionado por archivos | `deploy/observability/grafana/*`, tablero `dashboards/moscowle-overview.json` y «Node Exporter Full» (id 1860) |
| Instaladores idempotentes | `setup_observability.sh` (host), `setup_vm_exporter.sh` (VM-APP y VM-DB) |
