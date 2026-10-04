# PRP 005 — Entornos separados: producción en cPanel, develop en Ubuntu, host dividido con QEMU

**Estado:** planificación. No ejecutar hasta cerrar el **Gate 0** (VT-x) y la **Fase 1** (hostname de la API de producción).
**Fecha:** 2026-10-02
**Decisiones ya tomadas por el usuario:**
1. `https://moscowle.centrojuanpabloii.com` (cPanel) → **producción**.
2. `https://api-centrojuanpabloii.online` (túnel Cloudflare → 192.168.1.41) → **develop**.
3. El backend de producción vive en **Ubuntu dentro de una VM QEMU**; cPanel recibe **solo el frontend estático**.
4. Alcance QEMU: **2 VMs** (`prod` y `develop`) en el mismo host.

---

## Fase 0 — Descubrimiento (hechos verificados, no supuestos)

### 0.1 Estado real de cPanel

| Verificación | Comando / fuente | Resultado |
|---|---|---|
| FTP alcanzable | `ftplib.FTP('ftp.centrojunpabloii.com')` → `login()` | **OK** — Pure-FTPd+TLS, 62 archivos en `/public_html/moscowle.centrojuanpabloii.com` |
| Frontend desactualizado | `LIST` del FTP | última subida **Sep 21 23:34** |
| Backend presente en disco | `cwd('/moscowle')` | 73 entradas (`.env`, `Dockerfile`, `passenger_wsgi.py`…) |
| **Frontend de cPanel ROTO** | `curl -w '%{http_code} %{size_download} %{content_type}'` | `/app/main-EAL3PU6F.js` → **17051 `text/html`** (cae al index); `/main-EAL3PU6F.js` → **222755 `application/javascript`** (el real está en la raíz) |
| Causa | `edysync/dist/.../index.html` y el servido por cPanel | ambos con `<base href="/app/">` |
| Backend cPanel caído | `docs/DEPLOY_CPANEL.md:477-484` | **500 en todas las peticiones desde el 28/jul** (Passenger no arranca) |

### 0.2 Estado real del host `192.168.1.41`

| Verificación | Resultado |
|---|---|
| `systemd-detect-virt` | `none` → **bare metal** |
| `lscpu` | Intel Core **i5-4590T** @ 2.00GHz, 4 cores / 4 threads, Haswell |
| `egrep -c '(vmx\|svm)' /proc/cpuinfo` | **0** → **VT-x/VT-d apagado en BIOS** |
| `ls /dev/kvm` | **no existe** → **KVM no disponible** |
| `free -h` | 7.2 GB total, ~6.0 GB disponibles |
| `df -h /` | 98 GB, 70 GB libres |
| GPU | Intel HD (Xeon E3-1200 v3 integrada) — **sin GPU compute** |
| Servicios corriendo | `moscowle`, `nginx`, `mysql`, `ollama`, `cloudflared` |
| QEMU / libvirt / Docker instalados | **ninguno** |

### 0.3 Topología de despliegue actual

| Pieza | Ubicación exacta | Hecho |
|---|---|---|
| Build producción Angular | `edysync/angular.json:41-72` | `baseHref: "/app/"` (`:42`), `fileReplacements` → `environment.prod.ts` (`:50-55`), `outputHashing: "all"` (`:68`), default config (`:107`) |
| API que llama el front | `edysync/src/environments/environment.prod.ts:4` | `apiBaseUrl: 'https://api-centrojuanpabloii.online'` |
| API del build dev | `edysync/src/environments/environment.ts:4` | `apiBaseUrl: ''` (same-origin) |
| Ruta `/app/` la sirve Flask | `app/routes/public_routes.py:52-72` | `_SPA_DIR = edysync/dist/edysync/browser` |
| Auto-deploy actual | `.github/workflows/deploy-ubuntu.yml:36-48` | `npm run build` → `tar -czf /tmp/frontend_dist.tar.gz -C dist/edysync/browser .` → `POST $DEPLOY_WEBHOOK_URL` con `-F backend=true` / `-F frontend=@...` |
| Receptor | `app/routes/deploy_routes.py:35-56` | valida `X-Deploy-Token`, lanza `scripts/server_deploy.sh` |
| Ejecutor | `scripts/server_deploy.sh:4,10-12,50-51,63-80` | `--backend` → `git reset --hard origin/main` + `sudo -n systemd-run … systemctl restart moscowle`; `--frontend <tar>` → `rsync -a --delete` a `SPA_FRONTEND_ROOT` **y** `NGINX_FRONTEND_ROOT=/var/www/moscowle/app` + `reload nginx` |
| Deploy cPanel | `scripts/deploy_cpanel.py:4-7,34-44` | `--backend` / `--frontend` / `--dry-run`; FTP a `/moscowle` y `/public_html/moscowle.centrojuanpabloii.com` |
| Deploy cPanel (solo front) | `scripts/deploy_frontend.py:14-18` | mismo destino, sin `--dry-run` |
| Workflows a cPanel | — | **ninguno activo**; `deploy-backend.yml` y `deploy-frontend.yml` borrados en `3171aecf` |
| nginx real | **NO está en el repo** | solo `docker/nginx.conf` y un snippet en `PRPs/004--…:450-497` |
| cloudflared real | **NO está en el repo** | solo token en `PRPs/004:74,212`; hostname creado a mano en el dashboard |
| QEMU/VMs en el repo | — | **cero menciones** |
| Docker (fallback) | `docker-compose.yml` | `db`(mariadb:10.11), `redis`, `backend`, `celery-worker`, `nginx` |

### 0.4 «APIs permitidas» (lo que sí existe, con fuente)

```
# Deploy cPanel — scripts/deploy_cpanel.py:4-7, :317-341
python scripts/deploy_cpanel.py --dry-run
python scripts/deploy_cpanel.py --backend
python scripts/deploy_cpanel.py --frontend

# Deploy cPanel solo front — scripts/deploy_frontend.py
python scripts/deploy_frontend.py

# Build Angular (packaged) — edysync/package.json:8
npm run build                 # ng build && cp src/htaccess dist/edysync/browser/.htaccess

# Build Angular con config/base-href explícitos — docs/DEPLOY.md:137-139
npx ng build --configuration production

# Webhook de deploy — .github/workflows/deploy-ubuntu.yml:16-19, :45-48
curl -sS -X POST "$DEPLOY_WEBHOOK_URL" -H "X-Deploy-Token: $DEPLOY_TOKEN" -F "backend=true"
curl -sS -X POST "$DEPLOY_WEBHOOK_URL" -H "X-Deploy-Token: $DEPLOY_TOKEN" -F "frontend=@/tmp/frontend_dist.tar.gz"

# Script del servidor — scripts/server_deploy.sh:4
./server_deploy.sh [--backend] [--frontend /tmp/frontend.tar.gz]

# Puente WhatsApp (systemd) — scripts/install_whatsapp_service.sh:16-20
sudo cp app/whatsapp_bridge/moscowle-whatsapp.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl enable moscowle-whatsapp && sudo systemctl restart moscowle-whatsapp
```

**QEMU/libvirt/cloud-image: `man qemu-system-x86_64` + docs oficiales de Ubuntu Cloud Images. NO inventar flags** — toda bandera de QEMU/cloud-init se confirma en la Fase 2 contra el man page antes de ejecutar.

### 0.5 Anti-patrones detectados (no repetir)

1. **Asumir que Passenger funciona** en cPanel: está documentado en 500 (`docs/DEPLOY_CPANEL.md:477-484`).
2. **Romper el smoke test**: `.github/workflows/deploy-ubuntu.yml:69` hace `grep -q '<base href="/app/">'`. Si cambiamos `baseHref` para cPanel, ese test hay que ajustarlo (o mantener dos builds distintas).
3. **`git reset --hard origin/main` en producción**: es el mecanismo de *develop* (`scripts/server_deploy.sh:42`). La VM de producción no debe usar `--backend`.
4. **Levantar dos puentes WhatsApp**: el repo ya asume un único poseedor (`test_whatsapp_bridge_ownership.py`, `app/services/whatsapp_service.py:303-323`). Con 2 VMs hay que decidir **una** casa para el puente.
5. **Re-imprimir credenciales en el plan**: FTP, token de tunnel y API keys están en texto plano en el repo (`scripts/deploy_cpanel.py:34-36`, `PRPs/004:74`, `.env.production`). Referenciar por ruta, nunca copiar.
6. **Inventar la config de nginx/cloudflared**: no está en el repo; hay que leerla del host (`/etc/nginx/sites-enabled/`, `/etc/cloudflared/`) en la Fase 2.

---

## Gate 0 — Virtualización (bloqueante)

> ### ✅ CERRADO — 2026-10-02, opción 0-A (VT-x activado en BIOS)
> Verificado tras `sudo reboot` en el host:
> | Comprobación | Resultado |
> |---|---|
> | `egrep -c '(vmx\|svm)' /proc/cpuinfo` | **8** (antes `0`) |
> | `ls -l /dev/kvm` | **existe** (`10, 232 root:kvm`) |
> | `lsmod \| grep kvm` | `kvm_intel 552960` + `kvm 1527808` |
> | `/sys/module/kvm_intel/parameters/nested` | **Y** |
> | `systemctl is-active` (`cloudflared moscowle nginx mysql ollama`) | **todos `active`** |
> | Datos | `moscowle_prod` con **69 tablas**; `user=59`, `appointment=411`, `payment=62`; `.env` intacto |
> | API pública | `https://api-centrojuanpabloii.online/health` → **200**; `/app/` → 200; cPanel → 200 |
>
> ⚠️ **El host cambió de IP por DHCP tras el reinicio: `192.168.1.41` → `192.168.1.249`.**
> Todas las referencias a `.41` en docs/scripts deben actualizarse, y hay que pedir una
> **reserva DHCP en el router** para que la IP no vuelva a cambiar (ver «Riesgos»).

**Sin cerrar este gate no se ejecuta ninguna fase posterior.**

| Opción | Qué implica | Consecuencia |
|---|---|---|
| **0-A (recomendada)** Activar VT-x en BIOS | Reinicio físico → BIOS → `Intel VT-x` / `VMX` → `sudo apt install cpu-checker && kvm-ok` | KVM disponible → QEMU con rendimiento ~nativo |
| **0-B** QEMU en TCG | QEMU por software, sin `/dev/kvm` | **10-50× más lento**; inviable meter Ollama/Gunicorn/MySQL dentro de las VMs |
| **0-C** Cambiar de tecnología | LXC/Docker en host | No necesita VT-x; mismo objetivo de aislamiento con mucho menos overhead |

**Verificación del gate:**
```bash
egrep -c '(vmx|svm)' /proc/cpuinfo   # debe ser >= 1
ls -l /dev/kvm                        # debe existir
sudo kvm-ok                           # "KVM acceleration can be used"
```
Si el resultado es `0` → el plan sigue en pausa o se cambia a 0-B/0-C **antes** de instalar paquetes.

---

## Fase 1 — Hostname de la API de producción (bloqueante de diseño)

### Restricción declarada por el usuario
El dominio **`.com` está ligado a cPanel** y debe alojar el host de producción:
- **`moscowle.centrojuanpabloii.com`** → frontend de **producción** (cPanel).

**Verificado (2026-10-02):**

| Dato | Resultado |
|---|---|
| `dig +short NS centrojuanpabloii.com` | `dns1/dns2.planetahosting.pe` → **NO está en Cloudflare**, DNS en el proveedor de hosting |
| `dig +short moscowle.centrojuanpabloii.com` | `201.148.104.76` (servidor cPanel, en Perú) |
| `dig +short api-centrojuanpabloii.online` | `172.67.138.180 / 104.21.54.128` → **Cloudflare proxied** |
| Túnel | `cloudflared --no-autoupdate tunnel run --token-file /etc/cloudflared/token` → **gestionado en remoto**, sin `config.yml` local |
| nginx del host | `/etc/nginx/sites-available/moscowle`: `listen 80; server_name _; root /var/www/moscowle;` **sin `proxy_pass`** → solo LAN; el túnel va **directo a Flask :5000** |

### Consecuencia
El **link público** de producción es `.com` (cPanel, solo estático), pero el frontend necesita **llamar a una API** en el servidor Ubuntu, que sólo es alcanzable **a través del túnel de Cloudflare** (el host está en LAN, sin IP pública expuesta).

**No hay que mover el dominio.** El frontend es estático: basta con `apiBaseUrl` apuntando a la API de producción.

| Opción | Cómo | Coste |
|---|---|---|
| **1-A (recomendada)** | Segundo public hostname en el **mismo** túnel: `api-prod.centrojuanpabloii.online → localhost:5000` (o nginx:80 cuando exista routing por Host). El link de usuarios sigue siendo `.com`. | ~2 min en el dashboard de Cloudflare |
| **1-B** | `api-prod.centrojuanpabloii.com` vía **CNAME → `<UUID>.cfargotunnel.com`** creado en Planeta Hosting + public hostname en el dashboard | Todo en `.com`, pero el DNS queda fuera de Cloudflare y expone el UUID del túnel |
| **1-C** | Un solo hostname `api-centrojunpabloii.online` para ambos entornos | Sin DNS nuevo, pero **no hay separación real** de datos (descartado) |
| **1-D** | Reverse proxy desde cPanel (`.htaccess` → túnel) | Depende de `mod_proxy`, normalmente deshabilitado en cPanel; no recomendado |

**Salida de esta fase:** dos variables escritas y aprobadas:
- `PROD_API_BASE` = `https://api-prod.centrojuanpabloii.online` (opción 1-A)
- `DEV_API_BASE` = `https://api-centrojuanpabloii.online`
- Link público de producción = `https://moscowle.centrojuanpabloii.com` (cPanel, build `cpanel` con `base-href /`)

**Verificación:** `curl -s $PROD_API_BASE/health` y `curl -s $DEV_API_BASE/health` devuelven `{"app":"app","status":"ok",…}`.

---

## Fase 2 — Base del host para QEMU

**Qué implementar** (sobre el host, una sola vez):
1. Confirmar gate 0 (comandos arriba).
2. Instalar paquetes y comprobarlos contra el man page:
   ```bash
   sudo apt-get install -y qemu-system-x86 qemu-utils libvirt-daemon-system \
        libvirt-clients bridge-utils cpu-checker
   sudo systemctl enable --now libvirtd
   ```
3. **Leer antes de tocar** la config real, que no está en el repo:
   - `cat /etc/nginx/sites-enabled/*` (ver `PRPs/004:450-497` solo como referencia histórica)
   - `ls -l /etc/cloudflared/ && cat /etc/cloudflared/*`
   - `systemctl cat moscowle nginx mysql ollama cloudflared`
4. Descargar la imagen base Ubuntu 26.04 Cloud Image y comprobar su SHA256 publicada (docs oficiales Ubuntu Cloud Images).
5. Definir el plano de recursos (ver tabla abajo) **y** de dónde sale la RAM.

**Plan de recursos propuesto** (host: 4 cores / 7.2 GB):

| Entorno | vCPU | RAM | Disco qcow2 | Servicios dentro |
|---|---|---|---|---|
| Host (queda) | — | ~2.0 GB | — | `ollama`, `cloudflared`, `nginx` (puerta de entrada), `qemu` |
| **VM-PROD** | 2 | 2.5 GB | 20 GB | `moscowle` (gunicorn/eventlet) + `nginx` |
| **VM-DEV** | 2 | 2.0 GB | 20 GB | `moscowle` (gunicorn/eventlet) + `nginx` |
| MySQL | — | — | — | **decisión 2.1 abajo** |

**Decisión 2.1 (bloqueante): dónde vive MySQL**
- **2.1-A (recomendada): MySQL en el host**, un instance con dos schemas (`moscowle_prod`, `moscowle_dev`). Ahorra ~800 MB y permite backups en un solo sitio. Aislamiento a nivel de schema, no de proceso.
- **2.1-B: MySQL dentro de cada VM.** Aislamiento real, pero +800 MB y ~400 MB más de host → inviable sin quitar Ollama.

**Verificación:**
```bash
egrep -c '(vmx|svm)' /proc/cpuinfo ; ls /dev/kvm
virsh version && virsh list --all
qemu-system-x86_64 --version
```
**Anti-patrones:** no usar imágenes de terceros no verificadas; no asignar más RAM total que la disponible (`free -h`); no montar `/dev/kvm` si el gate falló.

---

## Fase 3 — VM-PROD

**Qué implementar** (copiar patrones de la Fase 2, no improvisar):
1. `qemu-img create -f qcow2 … 20G` + cloud-init `user-data` (hostname `moscowle-prod`, usuario, ssh key, paquetes base).
2. Arranque con `--enable-kvm` (si gate 0-A) y red en bridge/NAT definido en Fase 2.
3. Dentro de la VM: Python 3.11 + venv + `requirements.txt`, `systemd` unit equivalente a la descrita en `PRPs/004--…:295-321` (`gunicorn --worker-class eventlet --workers 2 --bind 127.0.0.1:5000 --timeout 300 server_local:application`), `nginx` con `location / → proxy_pass http://127.0.0.1:5000` (patrón: `docker/nginx.conf:26-40` y `PRPs/004:458-466`).
4. `.env` de producción: partir de `.env.production` (subido por `deploy_cpanel.py:247-255`), **ajustando `DATABASE_URL` al schema de la decisión 2.1** y `PROD_API_BASE`.
5. **Sin** `scripts/server_deploy.sh --backend` (anti-patrón 3).

**Referencias:** `PRPs/004--…:292-325` (unit), `docker/nginx.conf` (proxy), `docs/DEPLOY.md` (URLs).
**Verificación:**
```bash
curl -s http://127.0.0.1:5000/health          # {"app":"app","status":"ok"}
curl -s $PROD_API_BASE/health                  # 200 público
curl -s $PROD_API_BASE/app/ | grep -o '<base href="[^"]*">'
```
**Anti-patrones:** no copiar `.env` de develop; no publicar el puerto de MySQL; no instalar Ollama dentro de la VM.

---

## Fase 4 — VM-DEV

**Qué implementar:** mismo patrón que la Fase 3 pero apuntando a `DEV_API_BASE`, schema `moscowle_dev`, y **sí** recibir el flujo auto de deploy.

1. Dentro de la VM: clone del repo + `scripts/server_deploy.sh` tal cual (es el flujo de develop).
2. Apuntar el webhook de develop (`.github/workflows/deploy-ubuntu.yml:16-19`, `DEPLOY_WEBHOOK_URL`) a la VM-DEV.
3. Smoke tests del workflow (`deploy-ubuntu.yml:61-69`) deben apuntar a `DEV_API_BASE` **y** seguir esperando `<base href="/app/">`.

**Verificación:** `curl -s $DEV_API_BASE/health` → 200; un `git push` a `main` debe reiniciar **solo** la VM-DEV.
**Anti-patrones:** no confundir `DEV_API_BASE` con `PROD_API_BASE` en `.env`; no desplegar develop sobre el schema de producción.

---

## Fase 5 — Build de producción para cPanel (`base-href /`)

**Qué implementar:**
1. Nuevo environment `edysync/src/environments/environment.cpanel.ts` con `apiBaseUrl: '<PROD_API_BASE>'`.
2. Nueva configuración en `edysync/angular.json` (copiar el bloque `production` de `:41-72`):
   - `baseHref: "/"`  ← corrige el bug verificado en 0.1
   - `fileReplacements` → `environment.cpanel.ts`
   - `outputHashing: "all"`
3. Script de build: `"build:cpanel": "ng build --configuration cpanel && cp src/htaccess dist/edysync/browser/.htaccess"` (`edysync/package.json:8` es el patrón a copiar).
4. Desplegar: `python scripts/deploy_cpanel.py --frontend` (o `scripts/deploy_frontend.py`).

**Verificación (obligatoria, es la que hoy falla):**
```bash
B=$(curl -s https://moscowle.centrojuanpabloii.com/ | grep -o '<base href="[^"]*">')
echo "$B"                                     # debe ser <base href="/">
J=$(curl -s https://moscowle.centrojuanpabloii.com/ | grep -o 'src="[^"]*main[^"]*\.js"' | sed 's/src="//;s/"//')
curl -sI "https://moscowle.centrojuanpabloii.com/$J" | grep -i content-type   # must be application/javascript
curl -sI "https://moscowle.centrojuanpabloii.com/$J" | head -1               # HTTP/2 200 (no caer a index.html)
curl -s https://moscowle.centrojuanpabloii.com/ | grep -c 'src="main-[^"]*\.js"'   # assets relativos a la raíz
```
**Anti-patrones:**
- No subir el mismo `dist/` con `<base href="/app/">` a la raíz de cPanel (es exactamente el bug actual).
- No apuntar `apiBaseUrl` de producción a `api-centrojuanpabloii.online` si esa URL es develop (Fase 1).
- **Actualizar** el smoke test de `deploy-ubuntu.yml:69` si el build de develop deja de usar `/app/`.

---

## Fase 6 — Reparto final de tráfico

| URL | Sirve | Habla con |
|---|---|---|
| `moscowle.centrojuanpabloii.com` | cPanel, frontend estático build `cpanel` | `PROD_API_BASE` (VM-PROD) |
| `api-prod.centrojuanpabloii.online` (Fase 1) | VM-PROD | — |
| `api-centrojuanpabloii.online/app/` | VM-DEV, build con `baseHref "/app/"` | same-origin (`DEV_API_BASE`) |

**Qué implica:**
- `environment.prod.ts:4` **cambia** a `DEV_API_BASE` (o se renombra a `environment.dev.ts`) para que el build del túnel sea el de develop.
- El flujo auto de deploy (`deploy-ubuntu.yml` → webhook → `server_deploy.sh`) queda **solo** para develop.
- Producción se despliega con `deploy_cpanel.py --frontend` (manual, o con un workflow nuevo con `paths: ['edysync/**']`).

**Verificación:**
```bash
# Producción
curl -s https://moscowle.centrojuanpabloii.com/health -o /dev/null -w '%{http_code}\n'   # 200 (SPA fallback)
curl -s $PROD_API_BASE/api/health | head -c 120                                          # {"status":"ok"...}
# Develop
curl -s $DEV_API_BASE/api/health | head -c 120
```

---

## Fase 7 — Servicios que NO se duplican

| Servicio | Dónde vive | Motivo |
|---|---|---|
| `ollama` | **host** | consume toda la RAM/CPU disponible; no cabe en 2.5 GB |
| `cloudflared` | **host** | un solo tunnel con los 2 hostnames (Fase 1) |
| `nginx` | **host** (puerta) + dentro de cada VM | el host enruta por hostname a la VM correspondiente |
| `mysql` | **decisión 2.1** | recomendado: host, 2 schemas |
| puente WhatsApp (`moscowle-whatsapp`) | **UNA sola casa** (decidir: VM-PROD) | el repo asume poseedor único (`app/services/whatsapp_service.py:303-323`) |
| cron / APScheduler (`app/tasks.py:475-530`) | dentro de cada VM | corre con su propio `.env` |

**Verificación:** `systemctl list-units --type=service --state=running` en host y en cada VM; comprobar que **no** hay dos procesos escuchando el mismo `whatsapp_sessions/`.

---

## Fase 8 — Verificación final (checklist de aceptación)

- [ ] `sudo kvm-ok` → `KVM acceleration can be used` (o plan replanteado en Gate 0-B/0-C).
- [ ] `virsh list --all` muestra `moscowle-prod` y `moscowle-dev` en `running`.
- [ ] `curl -s $PROD_API_BASE/health` → `{"app":"app","status":"ok",…}`.
- [ ] `curl -s $DEV_API_BASE/health` → `{"app":"app","status":"ok",…}`.
- [ ] Producción: `<base href="/">` y `main-*.js` con `Content-Type: application/javascript`.
- [ ] Develop: `<base href="/app/">` (smoke test `deploy-ubuntu.yml:69` en verde).
- [ ] Producción y develop **usan schemas distintos** (verificar `DATABASE_URL` en cada VM).
- [ ] Un commit a `main` reinicia **solo** develop; producción no cambia.
- [ ] `systemctl status moscowle-whatsapp` → **una** instancia activa.
- [ ] Backups antes/después: `scripts/create_backup.sh` ejecutado y verificado.
- [ ] Ninguna credencial nueva copiada al repo (revisar `git diff` antes de commitear).

---

## Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| VT-x no se puede activar (acceso físico) | Alto: QEMU en TCG no sirve | Gate 0 con opciones 0-B / 0-C explícitas |
| RAM insuficiente (7.2 GB con Ollama) | Alto | Decisión 2.1-A (MySQL en host) y topología de 2 VMs ya dimensionada |
| Romper la web actual al cambiar `baseHref` | Alto | Fase 5 con verificación de content-type antes de dar por buena |
| Doble puente WhatsApp | Medio | Fase 7: una sola casa + lock ya existente |
| nginx/cloudflared reales desconocidos (no están en el repo) | Medio | Fase 2.3: leerlos del host **antes** de tocar nada |
| Credenciales en texto plano en el repo | Medio (pre-existente) | `docs/ROTATE_CREDENTIALS.md`; no propagar a las VMs |

---

## Orden de ejecución

```
Gate 0 (VT-x) ─┐
Fase 1 (hostnames) ─┴─▶ Fase 2 (base QEMU) ─▶ Fase 3 (VM-PROD) ─▶ Fase 4 (VM-DEV)
                                                          │
                            Fase 5 (build cPanel) ────────┤
                                                          ▼
                                            Fase 6 (reparto) ─▶ Fase 7 (servicios) ─▶ Fase 8 (aceptación)
```

Fases 1 y 5 son paralelizables con 2/3/4. **Nada se ejecuta hasta cerrar Gate 0 y Fase 1.**
