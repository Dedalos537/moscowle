# PRP 006 — División de servicios del host Ubuntu con QEMU/KVM

**Estado:** listo para aplicar. **Gate 0 cerrado** (VT-x activado 2026-10-02).
**Fecha:** 2026-10-02 · **Anterior:** [[005--entornos-qemu-produccion-develop]] (parcialmente anulado)

## Alcance

**Sí:**
- Dividir los servicios del host `192.168.1.249` (antes `.41`) en **2 VMs QEMU/KVM**: `VM-APP` (backend Flask) y `VM-DB` (MySQL).
- El host queda con: `cloudflared`, `nginx` (frontend estático), `Ollama`, el reenvío de puertos y el sistema base.

**No (fuera de alcance, decisión del usuario):**
- ~~Entorno de **producción** en cPanel / `moscowle.centrojuanpabloii.com`~~
- ~~Split prod/develop, hostname `api-prod.*`, build con `base-href /`~~
- `scripts/deploy_cpanel.py` / `deploy_frontend.py` → **no se tocan**, quedan como estaban.
- `ai-engine` (puerto 5001) → **`inactive`** en el host, no entra en el plan.

**No cambia:** dominio, token del túnel, flujo de deploy por webhook, frontend estático en `/var/www/moscowle/app`, `.env` de producción salvo dos claves.

---

## Estado: EJECUTADO (2026-10-04) ✅

| Fase | Resultado |
|---|---|
| 1 Base QEMU | ✅ QEMU 10.2.1, libvirt 12.0.0, `socat`, `virt-install`, `cloud-localds`; `virbr0 = 192.168.122.1/24` (DHCP .2–.254); imagen base `ubuntu-resolute-base.img` (825 MB, SHA256 OK); ufw `11434/tcp on virbr0` |
| 2 VM-DB | ✅ `192.168.122.20`, 1 vCPU / 1536 MB / 30 GB, dump `118 MB · 69 CREATE TABLE`, restore → **69 / 59 / 411 / 62**, `bind-address 0.0.0.0` |
| 3 VM-APP | ✅ `192.168.122.10`, 2 vCPU / **2048 MB** / 30 GB, Python **3.11** + Node **20.20.2**, repo + venv + `.env`, `/health` → 200 |
| 4 Corte | ✅ host `moscowle` parado → dump final → restore → `moscowle-fwd.service` (`socat TCP-LISTEN:5000,bind=127.0.0.1 → 192.168.122.10:5000`) → API pública **200** |
| 5 Deploy | ✅ commit **`575707c0`**; Actions `Deploy to Ubuntu (auto)` → success; `--frontend` y `--backend` probados end-to-end |
| 6 Aceptación | ✅ ver checklist final abajo |

### Desviaciones respecto a la versión prevista del plan

1. **`gunicorn` bindea `0.0.0.0:5000`** dentro de VM-APP (no `127.0.0.1`): el `socat` del host entra por la IP de la VM. `misc.py` (`UPSTREAM_HOST='127.0.0.1'`) sigue funcionando porque `0.0.0.0` incluye loopback.
2. **Python 3.11 vía deadsnakes**: se copiaron `/etc/apt/sources.list.d/deadsnakes-ppa.list` (suite `noble`) y `/etc/apt/keyrings/deadsnakes.gpg` desde el host; `add-apt-repository` no sirve porque el PPA no publica para `resolute`.
3. **Node oficial**: tarball `node-v20.20.2-linux-x64.tar.xz` en `/usr/local` (misma versión que el nvm del host).
4. **`venv` (1 GB) y `.git` (309 MB) se copiaron por rsync** en vez de reinstalar: el repo es legible sin credenciales (`git ls-remote` OK), así que `git fetch/reset` funciona dentro de la VM.
5. **Clave VM→host** `~/.ssh/id_ed25519_to_host` en VM-APP, añadida a `authorized_keys` del host: sirve para copiar el dist a `/var/www/moscowle/app` y hacer `sudo systemctl reload nginx` (NOPASSWD ya lo cubría).
6. **`.env` de VM-APP**: solo dos claves distintas → `SQLALCHEMY_DATABASE_URI=@192.168.122.20` y `OLLAMA_HOST=http://192.168.122.1:11434`.
7. **Ollama**: drop-in `/etc/systemd/system/ollama.service.d/listen.conf` con `Environment=OLLAMA_HOST=0.0.0.0:11434` (ufw sólo lo publica en `virbr0`).
8. **El MySQL del host sigue activo** de forma intencionada (vía de rollback) hasta 24 h de estabilidad → Fase 5.4 pendiente.


---

## Fase 0 — Descubrimiento (verificado en el host tras el reboot)

### 0.1 Hardware y virtualización

| Comando | Resultado |
|---|---|
| `systemd-detect-virt` | `none` → bare metal (i5-4590T, 4 cores, 7.2 GB, 98 GB) |
| `egrep -c '(vmx\|svm)' /proc/cpuinfo` | **8** ✅ |
| `ls -l /dev/kvm` | **existe** ✅ |
| `lsmod \| grep kvm` | `kvm_intel 552960` + `kvm 1527808`; `nested=Y` ✅ |
| `qemu-system-x86_64`, `virsh`, `socat` | **NO instalados** |
| `ufw status` | requiere root → **estado desconocido** (Fase 1.4) |
| IP | **`192.168.1.249`** (DHCP cambió tras el reinicio; `.41` quedó obsoleto) |

### 0.2 Puertos y memoria reales (medidos)

```
LISTEN: 22  |  80 (nginx)  |  11434 (ollama, 127.0.0.1)  |  3306/33060 (mysql, 127.0.0.1)
            |  5000 (gunicorn, 127.0.0.1)  |  9090 (cloudflared metrics)  |  20241 (cloudflared, pid 5596)
RSS: mysqld 541 MB (1) · gunicorn 285 MB (2) · node 86 MB (1) · nginx 21 MB (5)
     cloudflared 40 MB · ollama 38 MB (inactivo; sube al cargar un modelo)
RAM: 7.2 GB total · 1.4 GB usados · 5.7 GB disponibles
```

**Procesos confirmados:**
```
gunicorn … --workers 1 --bind 127.0.0.1:5000 … server_ubuntu:application   (x2, pid 25557/25589)
node /home/diego/.nvm/versions/node/v20.20.2/bin/node index.js              (pid 25625, hijo de gunicorn)
cloudflared --no-autoupdate tunnel run --token-file /etc/cloudflared/token   (túnel gestionado en remoto)
```

**Firewall (`ufw`) activo** — `deny incoming` con 4 reglas: `22/tcp`, `80/tcp`, `443/tcp`, `9090/tcp` (+IPv6).
`11434` y `3306` **no** están publicados (además de bindear a `127.0.0.1`).

**`virbr0` aún no existe** (`Device "virbr0" does not exist`) → se crea en Fase 1.2.

**Origen del túnel:** el `cloudflared` no tiene `config.yml` local: el destino HTTP (`127.0.0.1:5000`) está en el
**dashboard de Cloudflare**. Por eso se reutiliza ese mismo puerto en el host con `socat` → **cero edición del túnel**.

### 0.3 Dependencias locales de Flask que condicionan el diseño

| Dependencia | Ubicación actual | Consecuencia para el plan |
|---|---|---|
| **Puente WhatsApp** | `subprocess.Popen(... stdin=PIPE, stdout=PIPE)` en `app/services/whatsapp_service.py:271-275`; el puente habla «una linea JSON entra, una linea JSON sale» (`app/whatsapp_bridge/index.js:4,221`) | **No es un servicio de red: se muda con Flask a VM-APP** (Node + `whatsapp_sessions/` incluidos) |
| **Ollama** | `config.py:32` → `OLLAMA_HOST` default `http://127.0.0.1:11434`; escucha solo en `127.0.0.1:11434` | VM-APP **no lo alcanza**: hay que escuchar en `0.0.0.0` y apuntar a `http://192.168.122.1:11434` |
| **MySQL** | `SQLALCHEMY_DATABASE_URI=…@localhost:3306/moscowle_prod` (`.env`) | Migrar a `192.168.122.20:3306` |
| **Auto-check / auto-restart** | `app/routes/api/misc.py:36-40` (`UPSTREAM_HOST='127.0.0.1'`, `UPSTREAM_PORT=5000`) y gunicorn en `127.0.0.1:{local_port}` (`misc.py:165-180`) | Sigue siendo local **dentro** de VM-APP → sin cambios |
| **IP del cliente** | `ProxyFix(x_for=1)` (`app/bootstrap.py:179`, `app/__init__.py:442`) + `X-Forwarded-For` en `app/routes/auth.py:47,388` | El reenvío debe **pasar los headers intactos** → `socat` en crudo sirve; un proxy que reescriba XFF rompería el rate-limit de login |
| **Webhook de deploy** | `app/routes/deploy_routes.py:24` → `scripts/server_deploy.sh` (git reset + `systemctl restart moscowle`) | El backend se muda pero **el webhook se queda en el host** → hay que hacer el paso hacia la VM (Fase 5) |
| **Reinicio desde Telegram** | `app/services/telegram_bot_service.py:963` → `sudo systemctl restart moscowle.service` | Dejará de apuntar al servicio correcto → **Fase 5.3** |
| **`ai-engine` :5001** | `inactive` | Fuera de alcance |
| **Redis (`CELERY_BROKER_URL`)** | `config.py:232` `redis://localhost:6379/0` | Redis **no está instalado**; no se toca |

### 0.4 Comandos «permitidos» (existentes, no inventados)

```bash
# paquetes (requiere contraseña sudo: NOPASSWD solo cubre systemctl restart moscowle,
#           systemctl reload nginx y systemd-run — ver CLAUDE.md de sesión)
sudo apt-get install -y qemu-system-x86 qemu-utils libvirt-daemon-system libvirt-clients bridge-utils socat

# estado
systemctl is-active cloudflared moscowle nginx mysql ollama
ss -lntp | grep LISTEN
virsh list --all ; virsh net-list --all

# deploy actual (sin cambios de URL)
curl -sS -X POST "$DEPLOY_WEBHOOK_URL" -H "X-Deploy-Token: $DEPLOY_TOKEN" -F "backend=true"
./scripts/server_deploy.sh [--backend] [--frontend /tmp/frontend.tar.gz]
```

Toda bandera de `qemu-img`/`cloud-init`/`virt-install` se confirma contra su `--help`/man page **antes** de ejecutarla.

### 0.5 Anti-patrones

1. **Meter Ollama o el puente WhatsApp en una VM distinta a la de Flask** → `OLLAMA_HOST` y el `Popen` stdin/stdout se rompen.
2. **Dejar `SQLALCHEMY_DATABASE_URI` apuntando a `localhost`** en VM-APP → se quedaría sin BD.
3. **Publicar el MySQL en `0.0.0.0`** o exponerlo a la LAN: solo debe escuchar en `virbr0`.
4. **Borrar el MySQL del host antes de validar la migración** → perder la vía de rollback.
5. **Romper `X-Forwarded-For`** con un proxy que lo reescriba (afecta a `auth.py:47`).
6. **Asumir `sudo -n` para `apt`** → falla; hay que pasar la contraseña.
7. Seguir citando `192.168.1.41` (IP obsoleta) en comandos o docs.

---

## Fase 1 — Base del host para QEMU

**Implementar:**
1. Instalar paquetes (Fase 0.4) y verificarlos.
2. Activar y comprobar la red NAT por defecto de libvirt (`virbr0`, típicamente `192.168.122.0/24`):
   ```bash
   virsh net-list --all; virsh net-info default
   ip -br addr show virbr0
   ```
   *Confirmar la red y el rango reales con `virsh net-dumpxml default` antes de asignar IPs.*
3. Descargar la **Ubuntu Cloud Image** oficial (misma serie que el host: 26.04) y verificar su SHA256 publicada.
4. El firewall ya está medido (Fase 0.2): `ufw` activo, `deny incoming`, solo `22/80/443/9090`.
   Regla a **añadir** una vez exista `virbr0` (nunca con `ufw disable`):
   ```bash
   sudo ufw allow in on virbr0 to any port 11434 proto tcp comment 'ollama desde VM-APP'
   ```
   `3306` **no** se publica: `VM-DB` sólo debe ser alcanzable desde la red NAT de libvirt.
5. Pedir/crear la **reserva DHCP** del host en el router para que `.249` no vuelva a cambiar.

**Verificación:**
```bash
qemu-system-x86_64 --version && virsh version
test -e /dev/kvm && echo KVM_OK
virsh net-list --all          # default  active
```

**Anti-patrones:** no usar imágenes de terceros; no desactivar `ufw` «para que funcione»; no cambiar la IP del host a mano sin reserva DHCP.

---

## Fase 2 — `VM-DB` (MySQL)

**Implementar:**
1. Crear disco `qcow2` (20 GB, *sparse*) y máquina con **1 vCPU / 1.5 GB RAM** (medido: `mysqld` = 541 MB RSS).
2. Dentro de la VM: `mysql-server`, `bind-address = 0.0.0.0` **restringido por firewall a `192.168.122.0/24`**, usuario `moscowle`, schema `moscowle_prod`.
3. Copia de seguridad del host **antes** de nada:
   ```bash
   mysqldump --single-transaction --routines --triggers moscowle_prod > /home/diego/backups/moscowle_prod_pre_qemu.sql
   ```
   *(claves leídas del `.env`; no imprimir la contraseña en claro)*
4. Restaurar en la VM y validar conteos contra el original:

   | Tabla | Valor de referencia (2026-10-02) |
   |---|---|
   | tablas totales | **69** |
   | `user` | **59** |
   | `appointment` | **411** |
   | `payment` | **62** |
   | `message_log` | **0** |

**Verificación:**
```bash
mysql -h 192.168.122.20 -u moscowle -p -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='moscowle_prod';"   # 69
```
**Anti-patrones:** no exponer `3306` a la LAN; no borrar el dump del host; no usar `CREATE DATABASE` con otro nombre (`moscowle_prod`).

---

## Fase 3 — `VM-APP` (backend Flask + puente WhatsApp)

**Implementar:**
1. Máquina con **2 vCPU / 1.5 GB RAM** y disco 20 GB (medido: `gunicorn` 285 MB + `node` 86 MB).
2. Runtime dentro de la VM (copiar versiones del host, no inventar):
   - Python 3.11 + `venv` + `requirements.txt`
   - **Node v20.20.2 vía nvm** (misma ruta que usa la unit del puente: `/home/diego/.nvm/versions/node/v20.20.2/bin/node`)
   - `git` + el repo (`git clone` de `origin/main`, o `rsync` desde el host)
3. Copiar `.env` y **cambiar solo dos claves**:
   - `SQLALCHEMY_DATABASE_URI=…@192.168.122.20:3306/moscowle_prod`
   - `OLLAMA_HOST=http://192.168.122.1:11434`
   (el resto — `SECRET_KEY`, `JWT_SECRET_KEY`, `APP_SECRET_KEY`, `CORS_ORIGINS`, `PREFERRED_URL_SCHEME` — **se copia igual**; `config.py:195-198` y `app/__init__.py:478-479` dependen del dominio, que no cambia)
4. `systemd` para gunicorn dentro de la VM, copiando la unit descrita en `PRPs/004--migracion-completa-a-ubuntu-server.md:295-321` (ajustando rutas a la VM). **Línea exacta a reproducir** (medida en Fase 0.2):
   ```bash
   /home/diego/moscowle_ia/venv/bin/gunicorn --worker-class eventlet --workers 1 \
     --bind 127.0.0.1:5000 --timeout 300 --graceful-timeout 30 \
     --access-logfile /home/diego/moscowle_ia/logs/gunicorn_acc.log \
     --error-logfile /home/diego/moscowle_ia/logs/gunicorn_err.log \
     server_ubuntu:application
   ```
5. **Ollama en el host debe escuchar fuera de `127.0.0.1`**:
   ```bash
   sudo systemctl edit ollama        # [Service] Environment=OLLAMA_HOST=0.0.0.0:11434
   sudo systemctl restart ollama
   ```
   restringiendo el acceso a `192.168.122.0/24` (Fase 1.4).

**Verificación (dentro de VM-APP):**
```bash
curl -s http://127.0.0.1:5000/health                       # {"app":"app","status":"ok"}
curl -s http://192.168.122.1:11434/api/tags                # Ollama accesible desde la VM
ls ~/moscowle_ia/whatsapp_sessions                          # existe (vacío hasta re-vincular)
```
**Anti-patrones:** no instalar Ollama dentro de la VM; no copiar el `.env` del host sin cambiar esas dos claves; no ejecutar dos puentes WhatsApp a la vez.

---

## Fase 4 — Corte (ventana de mantenimiento, ~10 min)

**Orden exacto:**
1. Aviso de mantenimiento / pausa de recordatorios (`app/tasks.py:475-530` corre en el host).
2. `sudo systemctl stop moscowle` (host).
3. `mysqldump` final → restaurar en `VM-DB` (si hubo cambios desde Fase 2).
4. Actualizar `.env` de **VM-APP** con el dump final y arrancar gunicorn **dentro** de la VM.
5. Levantar el reenvío en el host (opción recomendada):
   ```ini
   # /etc/systemd/system/moscowle-fwd.service
   [Service]
   ExecStart=/usr/bin/socat TCP-LISTEN:5000,bind=127.0.0.1,fork,reuseaddr TCP:192.168.122.10:5000
   Restart=always
   ```
   *(confirmar rango/IPS con `virsh net-dumpxml default`; alternativa: bloque `stream` de nginx si el módulo está cargado)*
6. `sudo systemctl start moscowle-fwd` y comprobar que `cloudflared` sigue apuntando a `127.0.0.1:5000` (**no se toca el dashboard**).

**Verificación:**
```bash
curl -s https://api-centrojuanpabloii.online/health          # 200
curl -s https://api-centrojuanpabloii.online/app/ -o /dev/null -w '%{http_code}\n'   # 200
curl -s https://api-centrojuanpabloii.online/api/health
ss -lntp | grep 5000                                        # ahora es el socat, no gunicorn
```

**Anti-patrones:** no parar `mysql` del host hasta validar; no tocar el token del túnel en esta fase; no cambiar `X-Forwarded-*`.

---

## Fase 5 — Poner al día el flujo de deploy y retirar servicios del host

**5.1 Deploy del backend hacia la VM** — hoy `server_deploy.sh --backend` hace `git reset` + `systemctl restart moscowle` **en el host** (`scripts/server_deploy.sh:42,50-51`), que tras la mudanza ya no tiene ese servicio. Añadir el paso hacia la VM (patrón a copiar: el propio script ya usa `sudo -n systemd-run`):
```bash
rsync -a --delete "$DEPLOY_ROOT/" vm-app:/home/diego/moscowle_ia/
ssh vm-app "sudo -n systemctl restart moscowle"
```
*Alternativa 5.1-B: mover el webhook a la VM (requiere mover también `cloudflared`). No recomendada: rompería el frontend estático que sigue en el host.*

**5.2 `--frontend`** → **sin cambios** (sigue sincronizando `SPA_FRONTEND_ROOT` y `NGINX_FRONTEND_ROOT` en el host).

**5.3** Actualizar `app/services/telegram_bot_service.py:963` (hoy `sudo systemctl restart moscowle.service` en el host) para que reinicie dentro de la VM, o eliminarlo si el propio webhook ya lo hace.

**5.4 Retirada del host** (solo tras 24 h de estabilidad):
```bash
sudo systemctl disable --now moscowle      # quitar el backend viejo del host
sudo systemctl disable --now mysql         # el MySQL viejo deja de arrancar (NO desinstalar aún)
```

**Verificación:** un `git push` a `main` debe reiniciar **la VM** y la API pública debe responder 200 en < 60 s.

---

## Fase 6 — Verificación final (aceptación)

- [x] `virsh list --all` → `moscowle-app` y `moscowle-db` en `running`.
- [x] `curl -s https://api-centrojuanpabloii.online/health` → `{"app":"app","status":"ok",…}`.
- [x] `curl -s https://api-centrojuanpabloii.online/app/` → 200 (y LAN `http://127.0.0.1/app/` → 200).
- [x] Conteos idénticos a la Fase 0: **69 tablas / `user` 59 / `appointment` 411 / `payment` 62**.
- [x] Flujo de deploy (`git push` → Actions → webhook) reinicia el backend **en la VM** (`575707c0`, run `Deploy to Ubuntu (auto)` → success).
- [x] `ps -C node` dentro de VM-APP → **1 proceso**; en el host → **0**. `gunicorn` host = 0, VM = 2.
- [x] `curl http://192.168.122.1:11434/api/tags` desde VM-APP → 200.
- [ ] `mysql` y `gunicorn` **no** aparecen en `ss -lntp` del host → `gunicorn` ✅ fuera; **`mysql` sigue activo** (Fase 5.4, a las 24 h).
- [ ] `free -h` del host con ≥ 3 GB libres → hoy **2.5 Gi disponibles**; mejora al retirar el MySQL del host.
- [x] `git diff` sin credenciales nuevas.
- [x] Frontend estático de `/var/www/moscowle/app` intacto (sincronizado por el deploy).

**Pendiente fuera de este PRP:** QR de WhatsApp (vincular en `Bot → Vincular`), `SMS_GATEWAY_TOKEN`, reserva DHCP del router para `192.168.1.249`, y el fallo preexistente de lint en `CI Backend` (`pip install ruff` sin fijar versión).

---

## Plan de rollback

Si algo falla en Fase 4 o 5:
1. `sudo systemctl stop moscowle-fwd`
2. Restaurar en el host la línea original de `.env` (`…@localhost:3306/moscowle_prod`) — **guardar una copia** antes de tocar nada: `cp .env .env.pre-qemu`
3. `sudo systemctl start mysql moscowle`
4. Verificar `curl -s https://api-centrojunpabloii.online/health` → 200

El MySQL del host **no se desinstala** hasta 24 h después de la validación (Fase 5.4).

---

## Presupuesto de recursos

| Elemento | vCPU | RAM | Disco | Estado real (2026-10-04) |
|---|---|---|---|---|
| Host (resto) | — | ~3.0 GB | 98 GB (65 libres) | `cloudflared`, `nginx`, `Ollama`, `socat`; RAM medida 4.6 GB usados (incluye el MySQL de rollback) |
| `VM-APP` | 2 | **2048 MB** | 30 GB | gunicorn (2 proc) + node (1) |
| `VM-DB` | 1 | 1536 MB | 30 GB | mysqld medido 541 MB |
| **Total** | 4 | **~6.0 / 7.2 GB** | | libera ~540 MB al retirar el MySQL del host |

---

## Orden de ejecución

```
Fase 1 (base QEMU) ─▶ Fase 2 (VM-DB + dump) ─▶ Fase 3 (VM-APP + Ollama en host)
                                                        │
                                                        ▼
                                          Fase 4 (corte + socat) ─▶ Fase 5 (deploy + retirada)
                                                        │
                                                        ▼
                                              Fase 6 (aceptación) ──┐
                                              24 h estabilidad ──────┴─▶ desinstalar MySQL del host
```

**Precondiciones antes de empezar:** contraseña de `sudo` disponible (el NOPASSWD solo cubre 3 comandos), reserva DHCP del host, y una copia de `.env` + `mysqldump` de referencia.
