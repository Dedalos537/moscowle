# PRP: Migración Backend + DB de Railway a cPanel

> **Version:** 1.0
> **Created:** 2026-07-22
> **Status:** Ready
> **Fases:** 1 (DB) → 2 (Backend) → 3 (Frontend) → 4 (DNS/SSL) → 5 (Verificación)

---

## Goal

Migrar el backend Flask y la base de datos MySQL de Railway a cPanel, consolidando todo el stack (frontend + backend + DB) en un solo hosting cPanel en `centrojuanpabloii.com`.

## Why

- Railway tiene la suscripción vencida y amenaza con suspender el servicio
- El frontend Angular ya está desplegado en cPanel
- Unificar todo en un solo hosting reduce costos y simplifica el deploy
- La DB de Railway tiene datos desde enero 2026 que necesitan preservarse

## What

Migración completa del backend Flask + MySQL de Railway a cPanel, manteniendo:
- Todas las 46 tablas y datos existentes
- WebSocket (SocketIO) funcional
- Autenticación JWT + OAuth
- Cron jobs
- CORS configurado para el dominio

### Success Criteria
- [ ] Base de datos importada exitosamente en cPanel con todas las 46 tablas
- [ ] Backend Flask ejecutándose en cPanel via Passenger/WSGI
- [ ] Endpoints API respondiendo correctamente (`/api/health`, `/api/admin/list-users`)
- [ ] WebSocket (SocketIO) funcionando
- [ ] Frontend Angular apuntando al nuevo backend y funcionando
- [ ] CORS configurado para `moscowle.centrojuanpabloii.com`
- [ ] SSL/HTTPS activo en el dominio

---

## All Needed Context

### Credenciales Railway (para exportar DB)
```yaml
MYSQL_HOST: mysql-production-fe1e.up.railway.app
MYSQL_USER: root
MYSQL_PASSWORD: "aAYXkPOxFQHYKREjdVrupSyroltfyiYg"
MYSQL_DATABASE: railway
MYSQL_PUBLIC_URL: "mysql://root:aAYXkPOxFQHYKREjdVrupSyroltfyiYg@shinkansen.proxy.rlwy.net:41619/railway"
```

### Credenciales cPanel (FTP)
```yaml
FTP_HOST: ftp.centrojuanpabloii.com
FTP_USER: centroju
FTP_PASS: "+LC6OXpm0dq6@4"
REMOTE_DIR: /public_html/moscowle.centrojuanpabloii.com
```

### DB Dump ya generado
```yaml
FILE: /Users/apple/Documents/moscowle_ia/moscowle_production.sql
SIZE: "1634 KB (1.6 MB)"
TABLES: 46
LINES: 15483
```

### Current Codebase Structure
```bash
moscowle_ia/
├── app/                          # Flask application
│   ├── __init__.py               # App factory (create_app)
│   ├── extensions.py             # SQLAlchemy, SocketIO, etc.
│   ├── models.py                 # All SQLAlchemy models
│   ├── routes/                   # Blueprints (admin, api, auth, etc.)
│   ├── services/                 # Business logic (railway_service, etc.)
│   ├── middleware/                # Metrics, CSRF, etc.
│   └── templates/                # Jinja2 templates
├── config.py                     # Config classes (Config, ProductionConfig)
├── server.py                     # Gunicorn entry point (eventlet)
├── start_server.py               # SocketIO server entry
├── wsgi.py                       # WSGI entry for PythonAnywhere
├── requirements.txt              # 50 Python dependencies
├── migrations/                   # Alembic migrations
├── edysync/                      # Angular frontend (already deployed)
│   └── dist/edysync/browser/     # Build output → cPanel
├── docker-compose.yml            # Local dev (MariaDB + Redis)
├── railway.json                  # Railway deploy config
├── Dockerfile                    # Multi-stage (Angular + Python + nginx)
├── moscowle_production.sql       # ← DB DUMP GENERADO
└── PRPs/
```

### Configuración actual (config.py)
```python
# Producción usa MySQL
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
# Formato: mysql+pymysql://user:password@host/dbname

# Pool settings para MySQL
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_recycle': 1800,
    'pool_pre_ping': True,
}
```

### Entry points del backend
```python
# server.py (principal - Gunicorn + eventlet)
from app import create_app
application = create_app()

# start_server.py (SocketIO)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
socketio.run(app, host='0.0.0.0', port=8080)
```

### Variables de entorno necesarias para cPanel
```env
FLASK_ENV=production
SECRET_KEY=<generar-nuevo>
JWT_SECRET_KEY=<generar-nuevo>
APP_SECRET_KEY=<generar-nuevo>

# DB de cPanel (ajustar según credenciales reales)
SQLALCHEMY_DATABASE_URI=mysql+pymysql://<usuario_cpanel>:<password_cpanel>@localhost/<nombre_db_cpanel>

# OAuth
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...

# APIs
GROQ_API_KEY=...
GEMINI_API_KEY=...
WHISPER_PROVIDER=groq

# Email
MAIL_SERVER=mail.centrojuanpabloii.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=...
MAIL_PASSWORD=...

# Sentry
SENTRY_DSN=https://cc4162720a3afe4d94e936af1507f7d0@o4511413962211328.ingest.us.sentry.io/4511413966405632

# Alertas
ALERT_EMAIL_TO=info@centrojuanpabloii.com
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Flask app detecta Railway por env vars (RAILWAY_ENVIRONMENT, etc.)
# En cPanel NO existen estas vars, así que tomará ProductionConfig automáticamente
# Ver app/__init__.py líneas 353-364

# CRITICAL: SocketIO requiere async_mode='eventlet' en produccion
# cPanel con Passenger soporta eventlet, pero hay que verificar

# CRITICAL: PyMySQL necesita allow_public_key_retrieval=True para caching_sha2_password
# Algunos hosts cPanel usan mysql_native_password

# CRITICAL: CORS_ORIGINS en config.py tiene default con Railway URL
# hay que cambiarlo a https://moscowle.centrojuanpabloii.com

# CRITICAL: CSP connect-src tiene wss:// de Railway
# hay que cambiarlo a wss://moscowle.centrojuanpabloii.com
```

---

## Implementation Blueprint

### Tasks (in execution order)

#### Fase 1: Preparar Base de Datos en cPanel
```yaml
Task 1.1: Crear base de datos en cPanel
  - ACCION: Ir a cPanel → MySQL Databases → Crear nueva DB
  - NOMBRE: <usuario_cpanel>_moscowle (cPanel agrega prefijo)
  - NOTA: Anotar credenciales exactas (usuario, password, nombre completo)

Task 1.2: Importar dump SQL en cPanel
  - ACCION: Ir a cPanel → phpMyAdmin → seleccionar DB → Import
  - ARCHIVO: moscowle_production.sql (1.6 MB)
  - ALTERNATIVA SSH: mysql -u <user> -p <db> < moscowle_production.sql
  - VERIFICAR: Que las 46 tablas se importaron correctamente
```

#### Fase 2: Preparar Backend para cPanel
```yaml
Task 2.1: Crear passenger_wsgi.py
  - CREAR: ~/moscowle/passenger_wsgi.py
  - CONTENIDO:
    ```python
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    os.environ.setdefault('FLASK_ENV', 'production')
    from app import create_app
    application = create_app()
    ```

Task 2.2: Crear archivo .env para cPanel
  - CREAR: ~/moscowle/.env
  - COPIAR de .env.example y ajustar:
    - SQLALCHEMY_DATABASE_URI con credenciales reales de cPanel
    - SECRET_KEY, JWT_SECRET_KEY, APP_SECRET_KEY (generar nuevos)
    - GOOGLE_OAUTH vars si aplica
    - GROQ_API_KEY, GEMINI_API_KEY

Task 2.3: Actualizar CORS en config.py
  - MODIFICAR: config.py línea CORS_ORIGINS
  - CAMBIAR: De Railway URL a https://moscowle.centrojuanpabloii.com
  - MODIFICAR: CSP connect-src de wss:// de Railway a wss://moscowle.centrojuanpabloii.com

Task 2.4: Instalar dependencias en cPanel
  - ACCION: SSH a cPanel
  - COMANDOS:
    ```bash
    cd ~/moscowle
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
```

#### Fase 3: Subir Código a cPanel
```yaml
Task 3.1: Subir backend por SFTP/FTP
  - MÉTODO: Usar deploy_frontend.py como base, adaptar para backend
  - EXCLUIR: edysync/dist/, .git/, __pycache__/, *.pyc
  - INCLUIR: app/, config.py, server.py, wsgi.py, passenger_wsgi.py, requirements.txt, .env, migrations/

Task 3.2: Configurar Python App en cPanel
  - ACCION: cPanel → Setup Python App (o Python Selector)
  - PYTHON: 3.11
  - APP ROOT: /moscowle
  - APP URL: https://moscowle.centrojuanpabloii.com
  - STARTUP FILE: passenger_wsgi.py
```

#### Fase 4: Configurar Dominio y SSL
```yaml
Task 4.1: Configurar subdominio en cPanel
  - ACCION: cPanel → Subdomains → Crear "moscowle" apuntando a /moscowle

Task 4.2: Configurar SSL
  - ACCION: cPanel → SSL/TLS → Let's Encrypt → agregar moscowle.centrojuanpabloii.com

Task 4.3: Configurar DNS
  - ACCION: Si el dominio está en otro registrar, agregar registro A:
    moscowle.centrojuanpabloii.com → IP del servidor cPanel
```

#### Fase 5: Actualizar Frontend
```yaml
Task 5.1: Actualizar environment.prod.ts
  - CAMPIAR apiUrl de Railway URL a https://moscowle.centrojuanpabloii.com/api
  - REBUILD: npx ng build --configuration=production
  - REDEPLOY: python scripts/deploy_frontend.py
```

#### Fase 6: Verificación
```yaml
Task 6.1: Test health endpoint
  - COMANDO: curl https://moscowle.centrojuanpabloii.com/api/health
  - ESPERADO: {"status": "healthy", ...}

Task 6.2: Test API endpoint
  - COMANDO: curl https://moscowle.centrojuanpabloii.com/api/admin/list-users
  - ESPERADO: JSON con lista de usuarios

Task 6.3: Test login
  - ACCION: Abrir https://moscowle.centrojuanpabloii.com en navegador
  - ESPERADO: Login funcional, dashboard cargando

Task 6.4: Test WebSocket
  - ACCION: Verificar que chat/notifications funcionan en tiempo real

Task 6.5: Verificar CORS
  - COMANDO: curl -H "Origin: https://moscowle.centrojuanpabloii.com" -I https://moscowle.centrojuanpabloii.com/api/health
  - ESPERADO: Header Access-Control-Allow-Origin presente
```

---

## Validation Loop

### Level 1: DB Import Check
```bash
# En cPanel por SSH o phpMyAdmin
mysql -u <user> -p <db> -e "SHOW TABLES;" | wc -l
# Esperado: 47+ líneas (46 tablas + header)
```

### Level 2: Backend Startup Check
```bash
# En cPanel → Setup Python App → logs
# Verificar que no hay errores de importación
# Verificar que Flask app inicia correctamente
```

### Level 3: API Endpoint Tests
```bash
# Health check
curl -s https://moscowle.centrojuanpabloii.com/api/health | python3 -m json.tool

# Protected endpoint (con token)
curl -s -H "Authorization: Bearer <token>" \
  https://moscowle.centrojuanpabloii.com/api/admin/list-users | python3 -m json.tool
```

### Level 4: Frontend Integration
```bash
# Abrir en navegador
# Login → Dashboard → Centro de Operaciones → WebSocket chat
# Verificar que todo carga sin errores en consola
```

---

## Final Checklist

- [ ] DB importada con 46 tablas
- [ ] Backend corriendo en cPanel (sin errores en logs)
- [ ] passenger_wsgi.py configurado
- [ ] .env con credenciales correctas de cPanel
- [ ] CORS configurado para dominio correcto
- [ ] SSL activo en moscowle.centrojuanpabloii.com
- [ ] Frontend apuntando al nuevo backend
- [ ] Login funcional
- [ ] WebSocket funcionando
- [ ] Health endpoint respondiendo
- [ ] Railway desactivado (para evitar costos)

---

## Anti-Patterns to Avoid

- ❌ No olvidar cambiar CORS_ORIGINS en config.py
- ❌ No olvidar cambiar CSP connect-src de wss:// de Railway
- ❌ No importar el dump sin verificar que la DB fue creada primero
- ❌ No saltar la generación de nuevos SECRET_KEY/JWT_SECRET_KEY
- ❌ No olvidar que cPanel agrega prefijo al nombre de la DB
- ❌ No dejar Railway corriendo después de migrar (costos)

---

## Notas

- **Dump ya generado**: `moscowle_production.sql` (1.6 MB, 46 tablas)
- **Contraseña Railway**: `aAYXkPOxFQHYKREjdVrupSyroltfyiYg` (con O mayúscula, no cero)
- **Frontend ya desplegado** en cPanel, solo necesita update de environment.prod.ts
- **Railway subscription vencida**: migrar urgentemente para evitar suspensión
