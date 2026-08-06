# 🚀 Deploy de Moscowle IA en cPanel

> **Guía paso a paso** para desplegar la aplicación Flask + Angular en un hosting con cPanel.

---

## 📋 Requisitos Previos

- Hosting cPanel con **Python App** (Setup Python App) — común en Hostinger, SiteGround, etc.
- Acceso a **cPanel** (usuario y contraseña)
- **Dominio** o subdominio asignado (ej: `app.moscowle.ai`)
- **Python 3.11+** disponible en el servidor
- **MySQL** (recomendado) o SQLite (solo pruebas)

---

## 🧱 Componentes del Deploy

| Componente | Tecnología | Cómo se sirve |
|---|---|---|
| Backend API | Flask + Gunicorn | Passenger WSGI (cPanel Python App) |
| Frontend | Angular SPA | Archivos estáticos vía Apache/Nginx |
| Base de datos | MySQL 8+ | cPanel MySQL Wizard |
| Archivos subidos | Uploads | Carpeta `instance/uploads` |
| Tareas asíncronas | Celery (opcional) | Worker separado o Redis |

---

## 🔹 PASO 1: Preparar el código

### 1.1 Subir archivos al hosting

Conéctate por **FTP/SFTP** o usa el **File Manager** de cPanel:

```
/home/tuusuario/
├── moscowle_ia/          ← TODO el proyecto (excluir node_modules, __pycache__, .env)
│   ├── app/
│   ├── config.py
│   ├── requirements.txt
│   ├── runtime.txt
│   ├── wsgi_cpanel.py    ← Archivo que crearás en el paso 3
│   └── ...
├── public_html/          ← O un subdominio: moscowle_ia  (depende del hosting)
│   └── (Angular compilado — opcional si usas carpeta separada)
```

**Excluye al subir:**
- `venv/`, `__pycache__/`, `.env`
- `node_modules/` (edysync)
- `*.db`, `*.log`

### 1.2 Crear archivo `.env` (NO subir a git)

```bash
# En el servidor, crear /home/tuusuario/moscowle_ia/.env
SECRET_KEY=genera_una_clave_segura_aqui
FLASK_ENV=production
DEBUG=False

# Base de datos MySQL (creada en cPanel)
SQLALCHEMY_DATABASE_URI=mysql+pymysql://usuario:contraseña@localhost/nombre_bd

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=contraseña_app_gmail
MAIL_DEFAULT_SENDER=tu_email@gmail.com

# CORS (tu dominio)
CORS_ORIGINS=https://app.moscowle.ai https://moscowle.ai
SOCKET_CORS_ORIGINS=https://app.moscowle.ai

# Timezone Perú
TIMEZONE=America/Lima

# App Secret
APP_SECRET_KEY=otra_clave_segura
```

---

## 🔹 PASO 2: Crear Base de Datos MySQL

1. En cPanel → **MySQL® Databases**
2. Crear una base de datos: `moscowle_prod`
3. Crear un usuario: `moscowle_user` con contraseña segura
4. Asignar usuario a la BD con **Todos los privilegios**
5. Copiar credenciales al `.env`:
   ```
   SQLALCHEMY_DATABASE_URI=mysql+pymysql://moscowle_user:pass@localhost/moscowle_prod
   ```

### ⚠️ Compatibilidad MySQL con SQLite

Si tu base local es SQLite y migras a MySQL, el proyecto usa Flask-Migrate + SQLAlchemy. Las migraciones están en `migrations/`. Para aplicar:

```bash
cd /home/tuusuario/moscowle_ia
source venv/bin/activate
flask db upgrade
```

Esto creará todas las tablas automáticamente.

---

## 🔹 PASO 3: Configurar WSGI para cPanel

cPanel usa **Passenger** (mod_wsgi) para servir Python. Necesitas un archivo WSGI especial. Crea `/home/tuusuario/moscowle_ia/wsgi_cpanel.py`:

```python
"""
WSGI para cPanel Passenger.
cPanel espera el objeto 'application' en la raíz.
"""
import sys
import os
import logging

# ── 1. Ruta del proyecto ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ── 2. Activar virtualenv ──
VENV_SITE = os.path.join(BASE_DIR, 'venv', 'lib', 'python3.11', 'site-packages')
if os.path.isdir(VENV_SITE) and VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# ── 3. Cargar .env ──
from dotenv import load_dotenv
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

# ── 4. Logging ──
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# ── 5. Crear aplicación ──
from app import create_app
application = create_app()

# ── 6. [Opcional] Punto de entrada directo ──
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=8080)
```

### Archivo `passenger_wsgi.py`

Algunos hostings (Hostinger, SiteGround) exigen **exactamente** el nombre `passenger_wsgi.py` en la raíz del documento. Crea un enlace o copia:

```bash
cd /home/tuusuario/moscowle_ia
ln -s wsgi_cpanel.py passenger_wsgi.py
```

O simplemente crea `passenger_wsgi.py` con el mismo contenido.

---

## 🔹 PASO 4: Configurar Python App en cPanel

### 4.1 Abrir Setup Python App

En cPanel → **Setup Python App** (o **Python App**).

### 4.2 Parámetros

| Campo | Valor |
|---|---|
| **Python version** | 3.11 (o la disponible más reciente) |
| **Application root** | `/home/tuusuario/moscowle_ia` |
| **Application URL** | `moscowle.ai` o el subdominio que uses |
| **Application startup file** | `passenger_wsgi.py` |
| **Application Entry point** | `application` |

### 4.3 Crear VirtualEnv

cPanel crea automáticamente el virtualenv en:
```
/home/tuusuario/virtualenvs/moscowle_ia/...
```

Si no lo crea automático, usa el botón **"Create"** o hazlo manual:

```bash
cd /home/tuusuario/moscowle_ia
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

### 4.4 Configurar Variables de Entorno

En la misma interfaz de **Setup Python App** hay una sección **"Environment variables"**. Agrega las **mismas** que pusiste en `.env` — pero **NO pongas SECRET_KEY dos veces** (usa una o la otra):

| Variable | Valor |
|---|---|
| `FLASK_ENV` | `production` |
| `DEBUG` | `False` |
| `SQLALCHEMY_DATABASE_URI` | `mysql+pymysql://...` |
| (y las demás del .env) |

### 4.5 Aplicar y Reiniciar

Haz clic en **"Save"** y luego **"Restart"**. La app se despliega en la URL configurada.

---

## 🔹 PASO 5: Compilar y servir el Frontend Angular

### 5.1 Compilar Angular

Si usas el frontend Angular (`edysync/`), compílalo localmente o en el servidor:

```bash
# En el servidor (o local y luego subes dist/)
cd /home/tuusuario/moscowle_ia/edysync
npm install
npx ng build --configuration=production
```

Esto genera la carpeta `edysync/dist/moscowle_ia/`.

### 5.2 Opción A — Servir con la misma app Flask (recomendado)

Configura Flask para servir los estáticos de Angular. Edita tu `config.py`:

```python
# En config.py de producción
ANGULAR_DIST = os.path.join(basedir, 'edysync', 'dist', 'moscowle_ia')
```

Y agrega una ruta catch-all en `app/__init__.py`:

```python
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_angular(path):
    from flask import send_from_directory
    dist = current_app.config.get('ANGULAR_DIST', '/path/to/dist')
    if path and os.path.exists(os.path.join(dist, path)):
        return send_from_directory(dist, path)
    return send_from_directory(dist, 'index.html')
```

### 5.3 Opción B — Servir con Apache (públic_html)

Sube el contenido de `edysync/dist/moscowle_ia/` a `public_html/` (o la carpeta del subdominio). Agrega un `.htaccess`:

```apache
# public_html/.htaccess
RewriteEngine On
RewriteBase /

# No reescribir archivos reales
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^ index.html [L]

# API reverse proxy (si el backend está en otro puerto/url)
RewriteRule ^api/(.*) http://127.0.0.1:5001/api/$1 [P,L]
```

---

## 🔹 PASO 6: Archivos Subidos (Uploads)

Asegúrate de que la carpeta de uploads exista y tenga permisos:

```bash
cd /home/tuusuario/moscowle_ia
mkdir -p instance/uploads/receipts
chmod -R 755 instance/uploads
```

En `.env`:
```
UPLOAD_FOLDER=/home/tuusuario/moscowle_ia/instance/uploads
```

---

## 🔹 PASO 7: Configurar SSL/HTTPS

1. En cPanel → **SSL/TLS** → **Install and Manage SSL**
2. Usa **AutoSSL** (gratuito) o compra un certificado
3. Asegúrate que tu dominio tenga HTTPS forzado
4. En el `.env`, activa HTTPS:
   ```
   FORCE_HTTPS=True
   SESSION_COOKIE_SECURE=True
   JWT_COOKIE_SECURE=True
   SESSION_COOKIE_SAMESITE=None
   ```

---

## 🔹 PASO 8: Verificar el Deploy

### Checklist de verificación

```bash
# 1. Probar que la app responde
curl -I https://app.moscowle.ai

# 2. Ver logs de errores
cat /home/tuusuario/moscowle_ia/logs/app.log

# 3. Ver logs de Apache/cPanel
tail -f /etc/httpd/logs/error_log

# 4. Ver estado del virtualenv
source /home/tuusuario/moscowle_ia/venv/bin/activate
python --version
pip list | grep Flask

# 5. Probar login
curl -X POST https://app.moscowle.ai/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"test"}'

# 6. Probar BD
flask db check

# 7. Crear tablas si es primera vez
flask db upgrade
```

---

## 🔹 PASO 9: Tareas Programadas (APScheduler)

cPanel **no ejecuta workers persistentes** como celery. Alternativas:

### Opción A: Usar APScheduler en el mismo proceso Flask

Ya está configurado en `app/tasks.py`. Se inicia con la app. **Ventaja:** simple. **Desventaja:** puede ralentizar requests.

### Opción B: Cron Jobs de cPanel

1. En cPanel → **Cron Jobs**
2. Agregar tareas:

```bash
# Verificar pagos vencidos (diario 8am)
0 8 * * * cd /home/tuusuario/moscowle_ia && venv/bin/python -c "from app.tasks import check_payment_reminders; check_payment_reminders()" >> logs/cron.log 2>&1

# Actualizar sesiones expiradas (cada hora)
0 * * * * cd /home/tuusuario/moscowle_ia && venv/bin/python -c "from app.tasks import auto_update_session_status; auto_update_session_status()" >> logs/cron.log 2>&1
```

### Opción C: Celery con Redis externo (avanzado)

Si el hosting permite procesos persistentes:

```bash
# Usar nohup o Supervisor
nohup celery -A app.celery_app worker --loglevel=info &
```

Pero en cPanel compartido, generalmente **no está permitido**. Usa la opción A o B.

---

## 🔹 PASO 10: Solución de Problemas Comunes

### ❌ "Internal Server Error" 500
```bash
# Ver el error real
cat /home/tuusuario/moscowle_ia/logs/app.log
tail -f /usr/local/apache/logs/error_log
grep passenger /usr/local/apache/logs/error_log
```

### ❌ "No module named flask"
```bash
# El virtualenv no se está usando
# Verifica passenger_wsgi.py → sys.path tiene la ruta correcta
# Ejecuta manualmente:
pip install -r requirements.txt
```

### ❌ "MySQL server has gone away"
```bash
# Conexiones idle agotadas. En config.py:
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_recycle': 1800,
    'pool_pre_ping': True,
}
```

### ❌ "403 Forbidden" en Angular SPA
```bash
# Faltan rutas para SPA. Agrega .htaccess con RewriteRule.
```

### ❌ Passenger no detecta la app
- Verifica que `passenger_wsgi.py` está en el **Application root**
- Que el **Entry point** sea `application`
- Reinicia la app desde cPanel **Setup Python App** → **Restart**

---

## 🔁 Resumen de Archivos Clave

| Archivo | Ubicación | Propósito |
|---|---|---|
| `passenger_wsgi.py` | `/home/tuusuario/moscowle_ia/` | Punto de entrada WSGI para cPanel |
| `.env` | `/home/tuusuario/moscowle_ia/` | Variables de entorno (NO público) |
| `venv/` | `/home/tuusuario/moscowle_ia/` | Entorno virtual Python |
| `logs/app.log` | `/home/tuusuario/moscowle_ia/` | Logs de la aplicación |
| `instance/uploads/` | `/home/tuusuario/moscowle_ia/` | Archivos subidos por usuarios |
| `edysync/dist/` | `/home/tuusuario/moscowle_ia/` | Frontend Angular compilado |

---

## ⏱️ Tiempo Estimado

| Paso | Tiempo |
|---|---|
| Subir archivos | 10-15 min |
| Crear BD | 5 min |
| Configurar Python App | 10 min |
| Compilar Angular | 5-10 min |
| Configurar SSL | 5 min |
| Pruebas | 10-15 min |
| **Total** | **~45 min - 1 hora** |

---

> **¿Dudas?** Contacta al soporte de tu hosting cPanel o revisa los logs en:
> - `/home/tuusuario/moscowle_ia/logs/app.log`
> - `/usr/local/apache/logs/error_log` (o equivalente en tu hosting)

---

## 🔎 ANEXO: Diagnóstico real en centrojuanpabloii.com (jul 2026)

> Situación encontrada y resuelta al migrar de Railway a cPanel. Sirve como referencia para hosts con **CloudLinux Python Selector**.

### 1. Síntoma
`https://backend.centrojuanpabloii.com/api/health` → **500** con `content-type: text/html`, `server: Apache`, **sin** cabecera `X-Powered-By: Phusion Passenger`.

### 2. Causa raíz (doble)
1. **Passenger nunca se conectó al subdominio.** La app Python existe y está "started" en la config de CloudLinux (`~/.cl.selector/python-selector.json`):
   ```json
   { "moscowle": { "app_status": "started", "domain": "backend.centrojuanpabloii.com",
       "startup_file": "passenger_wsgi.py", "entry_point": "application", "python_version": "3.11" } }
   ```
   Pero el **vhost de Apache nunca se regeneró**: el docroot del subdominio sigue siendo `public_html/backend.centrojuanpabloii.com/` (carpeta vacía), no `/<approot>/public`.
2. **La app no arrancaba por un bug real:** `app/services/tools_registry.py` llamaba a `register_tool(...)` (inexistente) a nivel de módulo → `NameError` → `create_app()` fallaba. **Fix:** esas 2 llamadas deben ser el decorador `@tool(...)`.

### 3. Lo que NO funciona en este host (verificado)
- **`.htaccess` con directivas Passenger** (`PassengerEnabled`, `PassengerAppRoot`, `PassengerPython`): rechazadas por Apache → 500 "Invalid command". Solo el UI de cPanel/CloudLinux puede activarlo.
- **MySQL externo**: usuarios cPanel son `localhost`-only → `Access denied (1045)` desde fuera. La app usa `@localhost` y corre dentro del servidor.
- **UAPI cPanel** (`Passenger`, `PythonApp`, `Extensions`): módulos no existen (CloudLinux gestiona Python aparte; su API vive en el puerto 2030, inaccesible por firewall).

### 4. Fix desde el UI de cPanel (obligatorio)
1. cPanel → **Software → Setup Python App** → app `moscowle`.
2. **Restart** (si no aplica: **Stop → Start**, o editar Application URL → Save → revertir → Save, o **Delete y recrear**).
3. Root `/home/tuusuario/moscowle` · URL `backend.centrojuanpabloii.com` · startup `passenger_wsgi.py` · entry `application`.

### 5. Checklist post-fix
```bash
curl -s https://backend.centrojuanpabloii.com/api/health   # → JSON 200
curl -sI https://backend.centrojuanpabloii.com/api/health  # → X-Powered-By: Phusion Passenger
```

### 6. Evidencia adicional (jul 2026): Passenger NO se ejecuta

- **Prueba aislada**: se subió un `passenger_wsgi.py` trivial que escribe `~/moscowle/PASSENGER_RAN.txt` y responde 200. El request devolvió **500 instantáneo y el marcador nunca se escribió** → Passenger no ejecuta nada en este vhost; el 500 ocurre en Apache, antes de correr Python.
- **Domlogs** (`~/logs/backend.centrojuanpabloii.com-Jul-2026.gz`): el subdominio devuelve **500 para TODAS las peticiones desde el 28/jul** (body genérico 723 bytes, `server: Apache`, sin `X-Powered-By: Phusion Passenger`). Es el estado original del host, no un cambio de hoy.
- **DocumentRoot real** (UAPI `DomainInfo/domains_data`): `/home/centroju/public_html/backend.centrojuanpabloii.com` (solo `.well-known/` + `cgi-bin/`). No hay `.htaccess` ahí.
- **Conclusión**: CloudLinux inyecta directivas Passenger en el vhost del subdominio, pero el Apache de este hosting **no puede procesarlas** (mod_passenger no funcional para vhosts de usuario) → 500 en todas las peticiones. Ningún cambio de archivos por FTP/Fileman puede arreglar esto.
- **Todo el lado servidor quedó listo de todos modos**: `passenger_wsgi.py` correcto (rutas de venv reales + bootstrap de pip que extrae `wheelhouse.tar.gz` y hace `pip install --no-index`), `requirements.txt` con el pin de `flasgger>=0.9.5` (antes `0.9.7.1`, inexistente), `wheelhouse.tar.gz` (143 MB / 147 wheels offline), y el fix de `tools_registry.py` (61 `@tool`, 0 `register_tool`). El virtualenv del server estaba **vacío** — el bootstrap lo llena al primer boot real de Passenger.
- **Único paso restante (usuario, obligatorio)**: cPanel UI → **Setup Python App** → app `moscowle` → **Stop → Start** (o Delete y recrear), para regenerar el vhost con Passenger funcional. Si el hosting no soporta mod_passenger, hay que contactar al proveedor. Tras el primer Restart, la app instala dependencias (1-3 min); un segundo Restart arranca rápido. Luego verificar `/api/health`.
