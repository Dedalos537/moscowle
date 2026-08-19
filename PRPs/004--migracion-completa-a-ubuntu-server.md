# PRP: Migración Completa Backend + IA → Servidor Ubuntu

> **Version:** 1.0
> **Created:** 2026-08-19
> **Status:** Ready
> **Servidor:** Ubuntu 26.04 LTS — 192.168.1.41 (diego / Rucula_530)
> **Dominio:** api.centrojuanpabloii.online
> **Tunnel:** Cloudflare (token ya generado)

---

## Goal

Migrar el backend Flask, la base de datos MySQL y crear un motor de IA local (Ollama + faster-whisper + Tesseract) en un servidor Ubuntu dedicado. El frontend Angular se mantiene en cPanel. El dominio `api.centrojuanpabloii.online` apunta al servidor via Cloudflare Tunnel.

## Why

- El hosting cPanel tiene limitaciones de memoria y CPU para IA
- Ollama necesita correr en hardware dedicado (i5-4590T, 7.2GB RAM)
- Separar el motor de IA del backend web permite escalar independientemente
- Sin abrir puertos en el router gracias a Cloudflare Tunnels
- GitHub Actions deploya vía Cloudflare Access SSH

## What

Migración completa del stack backend a servidor Ubuntu local:

| Componente | Puerto | Servicio |
|------------|--------|----------|
| MySQL | 3306 | Base de datos |
| Flask + Gunicorn | 5000 | Backend API principal |
| FastAPI | 5001 | Motor de IA |
| Ollama | 11434 | LLM inference (qwen2.5:1.5b) |
| Nginx | 80/443 | Reverse proxy + SSL |
| cloudflared | - | Tunnel a Cloudflare |

### Success Criteria

- [ ] `https://api.centrojuanpabloii.online/api/health` → 200 OK
- [ ] Login desde frontend Angular funciona (JWT via nuevo backend)
- [ ] `https://api.centrojuanpabloii.online/ai/health` → 200 OK (motor IA)
- [ ] POST a `/ai/api/infer` con texto retorna respuesta del LLM
- [ ] Transcripción de audio via faster-whisper funciona
- [ ] OCR de imágenes via Tesseract funciona
- [ ] GitHub Actions deploya al servidor via Cloudflare Access
- [ ] Frontend cPanel apunta a `api.centrojuanpabloii.online`
- [ ] Backend cPanel apagado después de verificación completa

---

## All Needed Context

### Infraestructura del Servidor

```yaml
HOSTNAME: moscowle
OS: Ubuntu 26.04 LTS (resolute)
CPU: Intel Core i5-4590T @ 2.00GHz (4 cores, sin HT)
RAM: 7.2 GB
DISCO: 98 GB (86 GB libres)
IP_LOCAL: 192.168.1.41
USUARIO: diego
PASSWORD: Rucula_530
SSH_PORT: 22
PYTHON: 3.14.4 (instalado, pero necesita 3.11 para compatibilidad)
GIT: 2.53
FAIL2BAN: Activo (IP 192.168.1.5 confiable)
COCKPIT: Activo en puerto 9090
```

### Cloudflare Tunnel

```yaml
TOKEN: "eyJhIjoiNjhiMDU2YjEyODA3MWUxOTM4ODU0MjBkN2Y1NWJjZjAiLCJ0IjoiMmMyNGE1ZWUtMzRmMC00NjQ1LWJhMmItOTkyMzFlZTQwMDExIiwicyI6IlpURmlabUkwWm1ZdE5qSXpaQzAwTmpSbUxXRmhOREF0WWpJME5URm1aVEppTVRReSJ9"
DOMAIN: api.centrojuanpabloii.online
PROXY_TO: http://localhost:80 (Nginx)
```

### Credenciales cPanel (para extracción de DB)

```yaml
FTP_HOST: ftp.centrojuanpabloii.com
FTP_USER: centroju
FTP_PASS: "Gob$72612"
BACKEND_PATH: /home/centroju/moscowle
```

### Credenciales MySQL cPanel (para mysqldump remoto)

```yaml
# Necesitamos acceso MySQL remoto desde el servidor Ubuntu
# Si cPanel no permite acceso remoto, usar FTP para descargar dump
MYSQL_HOST: localhost (en cPanel)
MYSQL_USER: centroju_diego
MYSQL_DB: centroju_moscowle_prod
```

### Variables de Entorno Requeridas (.env para servidor)

```bash
# Flask
SECRET_KEY=<generar-random-64chars>
APP_SECRET_KEY=<generar-random-64chars>
JWT_SECRET_KEY=<generar-random-64chars>
FLASK_ENV=production

# Database
SQLALCHEMY_DATABASE_URI=mysql+pymysql://moscowle:PASSWORD_DB@localhost:3306/moscowle_prod

# Ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:1.5b
LLM_PROVIDER=ollama

# CORS
CORS_ORIGINS=https://moscowle.centrojuanpabloii.com https://api.centrojuanpabloii.online

# AI Engine
AI_ENGINE_URL=http://127.0.0.1:5001

# Email (mismas credenciales de cPanel)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=<tu-email>
MAIL_PASSWORD=<tu-password>

# Telegram
TELEGRAM_BOT_TOKEN=<token-existente>
TELEGRAM_WEBHOOK_SECRET=<secret-existente>
TELEGRAM_WEBHOOK_URL=https://api.centrojuanpabloii.com/api/telegram/webhook
```

### Presupuesto de Recursos

| Componente | RAM (pico) | RAM (reposo) | CPU |
|------------|-----------|-------------|-----|
| MySQL | 200 MB | 150 MB | Bajo |
| Flask (gunicorn x2) | 300 MB | 200 MB | Bajo |
| FastAPI AI Engine | 100 MB | 80 MB | Bajo |
| Ollama (cargado) | 1.2 GB | 0 MB (keep_alive=0) | Medio |
| faster-whisper (cargado) | 300 MB | 0 MB (se descarga) | Medio |
| Tesseract | 50 MB | 50 MB | Bajo |
| Nginx | 10 MB | 10 MB | Mínimo |
| OS + overhead | 500 MB | 500 MB | - |
| **TOTAL** | **~2.7 GB** | **~990 MB** | - |

Con 7.2 GB RAM y 4 cores, hay margen holgado.

---

## Implementation Blueprint

### FASE 1: Preparar Servidor (infraestructura)

```yaml
Task 1.1: Actualizar sistema
  - RUN: sudo apt update && sudo apt upgrade -y
  - RUN: sudo apt install -y curl wget git ufw software-properties-common apt-transport-https

Task 1.2: Instalar Python 3.11 (NO 3.14 — incompatibilidad con Werkzeug<3.0)
  - RUN: sudo add-apt-repository ppa:deadsnakes/ppa -y
  - RUN: sudo apt update
  - RUN: sudo apt install -y python3.11 python3.11-venv python3.11-dev
  - RUN: sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
  - VERIFY: python3 --version → Python 3.11.x

Task 1.3: Instalar MySQL 8
  - RUN: sudo apt install -y mysql-server
  - RUN: sudo systemctl enable --now mysql
  - RUN: sudo mysql_secure_installation (responder Y a todo)
  - RUN: sudo mysql -e "CREATE USER 'moscowle'@'localhost' IDENTIFIED BY '<generar-password>';"
  - RUN: sudo mysql -e "CREATE DATABASE moscowle_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
  - RUN: sudo mysql -e "GRANT ALL PRIVILEGES ON moscowle_prod.* TO 'moscowle'@'localhost';"
  - RUN: sudo mysql -e "FLUSH PRIVILEGES;"
  - SAVE: Password de MySQL en .env

Task 1.4: Instalar Nginx
  - RUN: sudo apt install -y nginx
  - RUN: sudo systemctl enable --now nginx
  - VERIFY: curl http://localhost → Nginx welcome page

Task 1.5: Instalar Ollama
  - RUN: curl -fsSL https://ollama.com/install.sh | sh
  - RUN: ollama pull qwen2.5:1.5b
  - VERIFY: ollama list → qwen2.5:1.5b
  - NOTE: Modelo descargado ~1GB. Con keep_alive=0 se descarga de RAM al terminar cada inferencia.

Task 1.6: Instalar Tesseract OCR español
  - RUN: sudo apt install -y tesseract-ocr tesseract-ocr-spa
  - VERIFY: tesseract --version

Task 1.7: Instalar cloudflared
  - RUN: curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
  - RUN: echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
  - RUN: sudo apt update && sudo apt install -y cloudflared
  - VERIFY: cloudflared --version

Task 1.8: Configurar UFW
  - RUN: sudo ufw allow 22/tcp
  - RUN: sudo ufw allow 80/tcp
  - RUN: sudo ufw allow 443/tcp
  - RUN: sudo ufw allow 9090/tcp (Cockpit)
  - RUN: sudo ufw --force enable
  - NOTE: Puerto 5000 y 5001 NO se abren al exterior — solo Nginx los alcanza localmente.
```

### FASE 2: Cloudflare Tunnel

```yaml
Task 2.1: Instalar cloudflared como servicio
  - RUN: sudo cloudflared service install eyJhIjoiNjhiMDU2YjEyODA3MWUxOTM4ODU0MjBkN2Y1NWJjZjAiLCJ0IjoiMmMyNGE1ZWUtMzRmMC00NjQ1LWJhMmItOTkyMzFlZTQwMDExIiwicyI6IlpURmlabUkwWm1ZdE5qSXpaQzAwTmpSbUxXRmhOREF0WWpJME5URm1aVEppTVRReSJ9
  - RUN: sudo systemctl enable --now cloudflared
  - VERIFY: sudo systemctl status cloudflared → active (running)

Task 2.2: Configurar DNS en Cloudflare (manual - usuario)
  # PASOS MANUALES:
  # 1. Ir a https://one.dash.cloudflare.com → Zero Trust → Networks → Tunnels
  # 2. Buscar túnel "moscowle-ai-engine" (se crea automáticamente con el token)
  # 3. Pestaña "Public Hostname" → "Add a public hostname"
  # 4. Subdomain: api
  # 5. Domain: centrojuanpabloii.online
  # 6. Service Type: HTTP
  # 7. URL: localhost:80
  # 8. Click "Save hostname"
  # 9. Verificar: https://api.centrojuanpabloii.online → debe llegar a Nginx

Task 2.3: Verificar tunnel funciona
  - RUN: curl -I https://api.centrojuanpabloii.online
  - EXPECT: HTTP/1.1 200 or 301 (Nginx respondiendo)
```

### FASE 3: Migrar Base de Datos

```yaml
Task 3.1: Extraer dump de MySQL en cPanel (vía FTP)
  # Dado que no hay acceso SSH a cPanel, estrategia alternativa:
  # Opción A: Usar la API del backend para exportar datos
  # Opción B: Descargar el .sql desde cPanel File Manager
  # Opción C: Crear endpoint temporal de export en el backend

  # MÉTODO SELECCIONADO: FTP download del dump
  # 1. Login al cPanel → phpMyAdmin → Exportar DB completa
  # 2. Guardar como .sql.gz
  # 3. Descargar via FTP a local
  # 4. Subir al servidor Ubuntu
  - RUN: lftp -u centroju,'Gob$72612' ftp.centrojuanpabloii.com -e "get /home/centroju/moscowle/backups/moscowle_dump.sql; quit" 2>/dev/null || echo "Dump no encontrado, crear endpoint temporal"
  # Si no hay dump en FTP, crear endpoint temporal en el backend:
  # GET /api/admin/export-db → genera mysqldump y lo sirve como archivo
  # (agregar temporalmente, deployar, descargar, eliminar)

Task 3.2: Importar dump en servidor Ubuntu
  - RUN: mysql -u moscowle -p moscowle_prod < /tmp/moscowle_dump.sql
  - VERIFY: mysql -u moscowle -p moscowle_prod -e "SHOW TABLES;" → debe mostrar todas las tablas
  - EXPECT: ~46 tablas

Task 3.3: Verificar integridad
  - RUN: mysql -u moscowle -p moscowle_prod -e "SELECT COUNT(*) FROM users;"
  - RUN: mysql -u moscowle -p moscowle_prod -e "SELECT COUNT(*) FROM sessions;"
  - COMPARE: Conteos con los de cPanel (verificar que coinciden)
```

### FASE 4: Deploy Backend Flask

```yaml
Task 4.1: Clonar repo
  - RUN: cd /home/diego && git clone https://github.com/Dedalos537/moscowle.git moscowle_ia
  - RUN: cd /home/diego/moscowle_ia

Task 4.2: Crear venv con Python 3.11
  - RUN: python3.11 -m venv venv
  - RUN: source venv/bin/activate
  - VERIFY: python --version → Python 3.11.x

Task 4.3: Instalar dependencias
  - RUN: pip install --upgrade pip
  - RUN: pip install -r requirements.txt
  - RUN: pip install gunicorn[eventlet]
  - VERIFY: python -m compileall -q app

Task 4.4: Crear .env del servidor
  - CREATE: /home/diego/moscowle_ia/.env
  # Generar SECRET_KEYs aleatorias:
  # python3 -c "import secrets; print(secrets.token_hex(32))"
  # Content: ver sección "Variables de Entorno Requeridas" arriba

Task 4.5: Verificar que compila
  - RUN: python -m py_compile config.py server_local.py wsgi.py run.py
  - RUN: python -m compileall -q app
  - EXPECT: 0 errores

Task 4.6: Crear systemd service
  - CREATE: /etc/systemd/system/moscowle.service
  ```ini
  [Unit]
  Description=Moscowle Backend (Flask + Gunicorn)
  After=network.target mysql.service
  Requires=mysql.service

  [Service]
  User=diego
  Group=diego
  WorkingDirectory=/home/diego/moscowle_ia
  Environment="PATH=/home/diego/moscowle_ia/venv/bin:/usr/bin"
  ExecStart=/home/diego/moscowle_ia/venv/bin/gunicorn \
      --worker-class eventlet \
      --workers 2 \
      --bind 127.0.0.1:5000 \
      --timeout 300 \
      --graceful-timeout 30 \
      --max-requests 1000 \
      --max-requests-jitter 200 \
      --access-logfile /home/diego/moscowle_ia/logs/gunicorn_acc.log \
      --error-logfile /home/diego/moscowle_ia/logs/gunicorn_err.log \
      server_local:application
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target
  ```

  - RUN: sudo systemctl daemon-reload
  - RUN: sudo systemctl enable --now moscowle
  - VERIFY: sudo systemctl status moscowle → active (running)

Task 4.7: Smoke test
  - RUN: sleep 5 && curl -s http://localhost:5000/api/health
  - EXPECT: {"status":"healthy",...}
  - RUN: curl -s -o /dev/null -w "%{http_code}" https://api.centrojuanpabloii.online/api/health
  - EXPECT: 200
```

### FASE 5: Motor de IA (FastAPI separada)

```yaml
Task 5.1: Crear estructura del proyecto
  - CREATE: /home/diego/ai-engine/
  ```
  ai-engine/
  ├── main.py              # FastAPI app
  ├── config.py            # Configuración
  ├── requirements.txt     # Dependencias
  ├── services/
  │   ├── __init__.py
  │   ├── db_context.py    # Consulta SQLite/MySQL local
  │   ├── sense_audio.py   # faster-whisper
  │   ├── sense_image.py   # Tesseract OCR
  │   └── llm_engine.py    # Ollama inference
  ├── .env                 # Variables de entorno
  └── ai-engine.service    # systemd unit (referencia)
  ```

Task 5.2: Crear main.py (FastAPI)
  - CREATE: /home/diego/ai-engine/main.py
  - FLUJO:
    1. POST /api/infer → recibe { text?, audio_file?, image_file?, session_id? }
    2. Consulta DB local para contexto del usuario
    3. [Si audio] → faster-whisper → texto → gc.collect()
    4. [Si imagen] → Tesseract → texto → gc.collect()
    5. Ensambla prompt: contexto DB + texto extraído + user text
    6. POST a Ollama (qwen2.5:1.5b, num_thread=2, keep_alive=0)
    7. Retorna { response, context_used, processing_time }

Task 5.3: Crear services/sense_audio.py
  - CREATE: /home/diego/ai-engine/services/sense_audio.py
  - faster-whisper con modelo "tiny" o "base" (~1GB RAM)
  - Flujo: cargar modelo → transcribir → DEL audio → gc.collect()
  - IMPORTANTE: modelo se carga y descarga por request (memory-safe)

Task 5.4: Crear services/sense_image.py
  - CREATE: /home/diego/ai-engine/services/sense_image.py
  - Tesseract OCR con español (tesseract-ocr-spa)
  - Flujo: abrir imagen → pytesseract.image_to_string → DEL imagen → gc.collect()

Task 5.5: Crear services/llm_engine.py
  - CREATE: /home/diego/ai-engine/services/llm_engine.py
  - Ollama API: POST http://127.0.0.1:11434/api/chat
  - Options: { "num_thread": 2, "keep_alive": 0, "num_ctx": 2048 }
  - Model: qwen2.5:1.5b
  - IMPORTANTE: keep_alive=0 descarga el modelo de RAM al terminar

Task 5.6: Crear services/db_context.py
  - CREATE: /home/diego/ai-engine/services/db_context.py
  - Conexión a MySQL moscowle_prod
  - Consulta: historial de sesiones del usuario, preferencias, contexto terapéutico
  - Usa SQLAlchemy o pymysql directo

Task 5.7: Crear requirements.txt del AI Engine
  - CREATE: /home/diego/ai-engine/requirements.txt
  ```
  fastapi>=0.100.0
  uvicorn[standard]>=0.23.0
  faster-whisper>=1.0.0
  pytesseract>=0.3.10
  Pillow>=9.0.0
  httpx>=0.24.0
  pymysql>=1.1.0
  python-dotenv>=1.0.0
  gc
  ```

Task 5.8: Crear .env del AI Engine
  - CREATE: /home/diego/ai-engine/.env
  ```
  MYSQL_HOST=localhost
  MYSQL_USER=moscowle
  MYSQL_PASSWORD=<misma-password-que-fase-3>
  MYSQL_DB=moscowle_prod
  OLLAMA_HOST=http://127.0.0.1:11434
  OLLAMA_MODEL=qwen2.5:1.5b
  AI_PORT=5001
  ```

Task 5.9: Instalar dependencias y verificar
  - RUN: cd /home/diego/ai-engine && python3.11 -m venv venv
  - RUN: source venv/bin/activate && pip install -r requirements.txt
  - RUN: python -m uvicorn main:app --host 127.0.0.1 --port 5001 (test manual)
  - VERIFY: curl http://localhost:5001/health → 200

Task 5.10: Crear systemd service
  - CREATE: /etc/systemd/system/ai-engine.service
  ```ini
  [Unit]
  Description=AI Engine (FastAPI + Ollama + Whisper + Tesseract)
  After=network.target mysql.service ollama.service
  Requires=mysql.service

  [Service]
  User=diego
  Group=diego
  WorkingDirectory=/home/diego/ai-engine
  Environment="PATH=/home/diego/ai-engine/venv/bin:/usr/bin"
  ExecStart=/home/diego/ai-engine/venv/bin/uvicorn main:app --host 127.0.0.1 --port 5001 --workers 1
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target
  ```

  - RUN: sudo systemctl daemon-reload
  - RUN: sudo systemctl enable --now ai-engine
  - VERIFY: curl http://localhost:5001/health → 200
```

### FASE 6: Nginx (Reverse Proxy)

```yaml
Task 6.1: Crear configuración Nginx
  - CREATE: /etc/nginx/sites-available/moscowle
  ```nginx
  server {
      listen 80;
      server_name api.centrojuanpabloii.online;

      # Backend Flask
      location / {
          proxy_pass http://127.0.0.1:5000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
          proxy_read_timeout 300s;
          proxy_connect_timeout 60s;
      }

      # AI Engine (FastAPI)
      location /ai/ {
          proxy_pass http://127.0.0.1:5001/;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
          proxy_read_timeout 600s;
          client_max_body_size 50M;
      }

      # Health check directo
      location /nginx-health {
          return 200 'ok';
          add_header Content-Type text/plain;
      }
  }
  ```

Task 6.2: Habilitar sitio
  - RUN: sudo ln -sf /etc/nginx/sites-available/moscowle /etc/nginx/sites-enabled/
  - RUN: sudo rm -f /etc/nginx/sites-enabled/default
  - RUN: sudo nginx -t
  - EXPECT: "syntax is ok" / "test is successful"
  - RUN: sudo systemctl reload nginx

Task 6.3: Verificar Nginx
  - RUN: curl -s http://localhost -H "Host: api.centrojuanpabloii.online" → Flask health
  - RUN: curl -s http://localhost/ai/health -H "Host: api.centrojuanpabloii.online" → FastAPI health
```

### FASE 7: GitHub Actions Deploy (Cloudflare Access SSH)

```yaml
Task 7.1: Configurar Cloudflare Access para SSH (manual - usuario)
  # PASOS MANUALES en Cloudflare Zero Trust:
  # 1. Zero Trust → Access → Applications → "Add an application"
  # 2. Tipo: "Self-hosted"
  # 3. Application name: "moscowle-server-ssh"
  # 4. Session duration: 24 hours
  # 5. Add policy → "Allow"
  # 6. Include: Emails → diego@centrojuanpabloii.com (o el email del usuario)
  # 7. Save
  # 8. Notar el Application ID y Policy ID

Task 7.2: Crear workflow deploy-ai-server.yml
  - CREATE: .github/workflows/deploy-ai-server.yml
  ```yaml
  name: Deploy to AI Server

  on:
    push:
      branches: [main]
      paths:
        - 'app/**'
        - 'config.py'
        - 'requirements.txt'
        - 'server_local.py'
        - 'ai_engine/**'
    workflow_dispatch:

  jobs:
    deploy-backend:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - name: Deploy via SSH (Cloudflare Access)
          uses: appleboy/ssh-action@v1
          with:
            host: ${{ secrets.AI_SERVER_HOST }}
            username: diego
            key: ${{ secrets.AI_SERVER_SSH_KEY }}
            script: |
              cd /home/diego/moscowle_ia
              git pull origin main
              source venv/bin/activate
              pip install -r requirements.txt -q
              python -m compileall -q app
              sudo systemctl restart moscowle
              sleep 3
              curl -sf http://localhost:5000/api/health || exit 1

    deploy-ai-engine:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - name: Deploy AI Engine via SSH
          uses: appleboy/ssh-action@v1
          with:
            host: ${{ secrets.AI_SERVER_HOST }}
            username: diego
            key: ${{ secrets.AI_SERVER_SSH_KEY }}
            script: |
              cd /home/diego/ai-engine
              git pull origin main
              source venv/bin/activate
              pip install -r requirements.txt -q
              sudo systemctl restart ai-engine
              sleep 3
              curl -sf http://localhost:5001/health || exit 1
  ```

Task 7.3: Generar SSH key para GitHub Actions
  - RUN: ssh-keygen -t ed25519 -f /home/diego/.ssh/github_actions -N ""
  - RUN: cat /home/diego/.ssh/github_actions.pub >> /home/diego/.ssh/authorized_keys
  - # Copiar private key a GitHub Secrets: AI_SERVER_SSH_KEY
  - # Copiar host a GitHub Secrets: AI_SERVER_HOST (IP pública o Cloudflare Access URL)

  # NOTA: Cloudflare Access SSH requiere cloudflared como proxy SSH
  # Alternativa más simple: abrir el puerto 22 en el router (forward a 192.168.1.41:22)
  # y usar la IP pública del router como AI_SERVER_HOST
  # El usuario debe configurar el port forwarding en su router:
  # Puerto WAN 2222 → 192.168.1.41:22
  # Luego AI_SERVER_HOST = <IP-publica-del-router>:2222

Task 7.4: Configurar GitHub Secrets
  # Secretos necesarios en GitHub:
  # AI_SERVER_HOST = <IP-publica>:2222 (o URL Cloudflare Access)
  # AI_SERVER_SSH_KEY = (contenido completo de la private key)
```

### FASE 8: Actualizar Frontend Angular

```yaml
Task 8.1: Actualizar environment.prod.ts
  - MODIFY: edysync/src/environments/environment.prod.ts
  - CHANGE: apiBaseUrl de 'https://backend.centrojuanpabloii.com' a 'https://api.centrojuanpabloii.online'
  - KEEP: restartSecret

Task 8.2: Actualizar environment.ts (desarrollo)
  - MODIFY: edysync/src/environments/environment.ts
  - CHANGE: apiBaseUrl para desarrollo local

Task 8.3: Build y deploy del frontend
  - RUN: cd edysync && npm run build
  # El deploy a cPanel se hace via el workflow existente deploy-frontend.yml
```

### FASE 9: Apagar Backend cPanel

```yaml
Task 9.1: Verificar todo funciona antes de apagar
  # CHECKLIST:
  # ✓ https://api.centrojuanpabloii.online/api/health → 200
  # ✓ Login desde frontend funciona
  # ✓ Todas las funciones del backend operativas
  # ✓ Motor IA responde
  # ✓ Transcripción de audio funciona
  # ✓ OCR funciona

Task 9.2: Deshabilitar backend en cPanel
  # Opciones:
  # A) Renombrar app.cgi → app.cgi.bak (más drástico)
  # B) Cambiar WSGI para que retorne 503 (más suave)
  # C) Eliminar el workflow deploy-backend.yml (ya no deploya)
  # RECOMENDADO: Opción C + esperar 1 semana de prueba

Task 9.3: Actualizar DNS
  # Si backend.centrojuanpabloii.com ya no se usa:
  # - Eliminar el registro DNS o redirigir a api.centrojuanpabloii.online
  # - Mantener frontend-centrojuanpabloii.com en cPanel
```

### FASE 10: Tests End-to-End

```yaml
Task 10.1: Test health checks
  - RUN: curl -s https://api.centrojuanpabloii.online/api/health | jq .
  - EXPECT: {"status": "healthy", ...}

Task 10.2: Test login
  # Usar curl o Playwright para verificar que el login completo funciona

Task 10.3: Test AI Engine - texto
  - RUN: curl -X POST https://api.centrojuanpabloii.online/ai/api/infer \
      -H "Content-Type: application/json" \
      -d '{"text": "Hola, ¿cómo estás?"}'
  - EXPECT: JSON con "response" del LLM

Task 10.4: Test AI Engine - health
  - RUN: curl https://api.centrojuanpabloii.online/ai/health
  - EXPECT: {"status": "ok", "ollama": "connected", "whisper": "available", "tesseract": "available"}

Task 10.5: Test Ollama standalone
  - RUN: curl http://localhost:11434/api/tags
  - EXPECT: Lista de modelos incluyendo qwen2.5:1.5b

Task 10.6: Monitoreo de memoria
  - RUN: free -h (antes de request)
  - RUN: curl -X POST .../ai/api/infer -d '{"text":"test"}'
  - RUN: free -h (durante inference)
  - RUN: sleep 10 && free -h (después — verificar que keep_alive=0 liberó RAM)
```

---

## Validation Loop

### Level 1: Syntax (en servidor)
```bash
cd /home/diego/moscowle_ia
source venv/bin/activate
python -m py_compile config.py server_local.py wsgi.py run.py
python -m compileall -q app
# Expected: 0 errors

cd /home/diego/ai-engine
source venv/bin/activate
python -c "from main import app; print('FastAPI OK')"
```

### Level 2: Services Running
```bash
sudo systemctl status moscowle
sudo systemctl status ai-engine
sudo systemctl status mysql
sudo systemctl status nginx
sudo systemctl status cloudflared
sudo systemctl status ollama
# All should be "active (running)"
```

### Level 3: Network
```bash
# Internal
curl -s http://localhost:5000/api/health
curl -s http://localhost:5001/health
curl -s http://localhost:11434/api/tags

# External (via tunnel)
curl -s https://api.centrojuanpabloii.online/api/health
curl -s https://api.centrojuanpabloii.online/ai/health
```

### Level 4: Functional
```bash
# Login test
curl -X POST https://api.centrojuanpabloii.online/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'

# AI inference test
curl -X POST https://api.centrojuanpabloii.online/ai/api/infer \
  -H "Content-Type: application/json" \
  -d '{"text":"¿Cuál es la capital de Perú?"}'
```

### Level 5: Memory Check
```bash
# Antes
free -h

# Durante inference (abrir otra terminal)
watch -n 1 free -h

# Después de 30s (keep_alive=0 debería haber liberado RAM)
sleep 30 && free -h
```

---

## Final Checklist

- [ ] Python 3.11 instalado (no 3.14)
- [ ] MySQL 8 corriendo con DB moscowle_prod importada
- [ ] ~46 tablas verificadas
- [ ] Cloudflare Tunnel activo y resolviendo
- [ ] `https://api.centrojuanpabloii.online` responde Nginx
- [ ] Flask backend corriendo en 127.0.0.1:5000
- [ ] FastAPI AI engine corriendo en 127.0.0.1:5001
- [ ] Ollama corriendo con qwen2.5:1.5b descargado
- [ ] Tesseract instalado con soporte español
- [ ] faster-whisper instalado
- [ ] Nginx configurado con reverse proxy
- [ ] GitHub Actions deploy funcional
- [ Frontend apuntando a api.centrojuanpabloii.online
- [ ] Backend cPanel deshabilitado
- [ ] Todos los tests E2E pasan
- [ ] Memoria estable (< 3GB en pico)

---

## Anti-Patterns to Avoid

- ❌ NO usar Python 3.14 — Werkzeug<3.0 no es compatible
- ❌ NO correr Ollama sin keep_alive=0 — consume 1GB+ de RAM permanentemente
- ❌ NO paralelizar whisper + Ollama — el i5-4590T no soporta
- ❌ NO abrir puertos 5000/5001 al exterior — solo Nginx localmente
- ❌ NO usar `llama3.1:8b` — demasiado grande para 7.2GB RAM; usar `qwen2.5:1.5b`
- ❌ NO hacer migration de DB sin backup primero
- ❌ NO apagar cPanel hasta verificar 48h de estabilidad

---

## Notes

- **Servidor real:** i5-4590T (no i7 como se mencionó inicialmente). 4 cores, 2.0GHz, sin HT.
- **Cloudflare Tunnel:** El token ya fue generado. El usuario debe crear el public hostname en el panel de Cloudflare.
- **Credenciales MySQL cPanel:** No hay acceso SSH a cPanel para mysqldump. Se usará phpMyAdmin o API del backend para exportar.
- **GitHub Actions:** Requiere port forwarding en el router o Cloudflare Access SSH. Opción más simple: cron git pull en el servidor.
- **Backup:** Siempre hacer backup de la DB antes de migrar. En cPanel → phpMyAdmin → Export → Full.
- **Ollama keep_alive=0:** Este parámetro es CRÍTICO. Sin él, Ollama mantiene el modelo (~1GB) en RAM indefinidamente.
- **faster-whisper modelo "tiny":** Solo ~75MB de modelo, ~1GB RAM durante uso. Se descarga después con gc.collect().
