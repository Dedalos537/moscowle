# 📋 PLAN DE IMPLEMENTACIÓN PASO A PASO
## Estabilidad y Seguridad en Producción - Moscowle IA

**Documento Vivo:** 24 de enero de 2026  
**Timeline Estimado:** 18-24 horas de implementación  
**Resultado Esperado:** Cero caídas en producción  

---

## 🎯 META PRINCIPAL

Tu aplicación actualmente está fallando múltiples veces al día. Después de este plan:
- ✅ Cero crashes por pool de conexiones agotado
- ✅ Cero crashes por excepciones no manejadas
- ✅ Cero memory leaks por sessions infinitas
- ✅ Cero users bloqueados por rate limiting
- ✅ Cero timeouts en requests
- ✅ Cero errores ocultos en logs

---

## 📊 ANÁLISIS RÁPIDO DE CRÍTICOS

| Problema | Status | Fix | Impacto |
|----------|--------|-----|---------|
| Pool conexiones | 🔴 Crítico | 2h | 8/10 |
| Excepciones | 🔴 Crítico | 3h | 9/10 |
| Sessions infinitas | 🔴 Crítico | 1h | 8/10 |
| Rate limiting | 🔴 Crítico | 1h | 7/10 |
| Background jobs | 🔴 Crítico | 2h | 8/10 |
| Uploads sin validar | 🔴 Crítico | 2h | 9/10 |
| Email bloqueante | 🟠 Alto | 3h | 7/10 |
| Logging | 🟠 Alto | 1h | 8/10 |

---

## 🚀 FASE 1: ESTABILIDAD BÁSICA (6-8 horas)
### Implementar PRIMERO - Antes de tocar nada más

### 1.1 Configurar Pool de Conexiones (30 min)

**Archivo:** `config.py`

**Qué hacer:**
1. Abre `/Users/apple/Documents/moscowle_ia_mvp/config.py`
2. Reemplaza la sección de base de datos con este código:

```python
# === DATABASE OPTIMIZATION ===
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///moscowle.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_COMMIT_ON_TEARDOWN = True

# Connection pool - CRÍTICO
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,              # Conexiones permanentes
    'max_overflow': 20,            # Conexiones adicionales
    'pool_timeout': 30,            # Segundos esperando
    'pool_recycle': 3600,          # Reciclar cada 1h
    'pool_pre_ping': True,         # Verificar antes de usar
    'echo': False                  # Off en producción
}
```

**Por qué:**
- `pool_size`: Mantiene 10 conexiones siempre activas
- `max_overflow`: Permite hasta 20 más bajo carga
- `pool_recycle`: MySQL/MariaDB requiere reciclar
- `pool_pre_ping`: Verifica que conexión esté viva

**Test:** Después de cambiar, verifica en terminal:
```bash
cd /Users/apple/Documents/moscowle_ia_mvp
python -c "from app import create_app; app = create_app(); print('✅ Pool configured')"
```

---

### 1.2 Agregar Logging Robusto (45 min)

**Archivo:** `app/__init__.py`

**Qué hacer:**
1. Copia la función `setup_logging()` del archivo `OPTIMIZACIONES_CODIGO.md`
2. Agrégala al inicio de `app/__init__.py`
3. Llámala en `create_app()` así:

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # ✅ LOGGING PRIMERO
    setup_logging(app)
    
    # ... resto del código ...
```

**Verificar:**
```bash
# Debe existir y tener permisos
mkdir -p /Users/apple/Documents/moscowle_ia_mvp/logs
touch /Users/apple/Documents/moscowle_ia_mvp/logs/app.log
```

**Test:**
```bash
python run.py
# Debe aparecer un archivo app.log con timestamps
```

---

### 1.3 Error Handlers Globales (45 min)

**Archivo:** `app/__init__.py`

**Qué hacer:**
1. Copia función `register_error_handlers()` del documento
2. Agrégala a `app/__init__.py`
3. Llámala en `create_app()`:

```python
def create_app(config_class=Config):
    # ... setup_logging ...
    
    # ✅ ERROR HANDLERS
    register_error_handlers(app)
    
    # ... resto ...
```

**Qué hace:**
- Captura ANY excepción no manejada
- Limpia sesión de BD automáticamente
- Loguea con contexto completo
- Retorna respuesta JSON consistente

---

### 1.4 Configuración de Sesiones (30 min)

**Archivo:** `config.py`

**Qué hacer:**
Reemplaza sección de sesiones:

```python
# === SESSION CONFIGURATION ===
PERMANENT_SESSION_LIFETIME = timedelta(hours=1)  # Timeout 1 hora
SESSION_REFRESH_EACH_REQUEST = True
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_NAME = 'moscowle_session'
SESSION_COOKIE_MAX_AGE = 3600
```

**Por qué:**
- `PERMANENT_SESSION_LIFETIME`: Cierra sesiones después de 1h inactividad
- `SECURE=True`: Cookie solo sobre HTTPS
- `HTTPONLY=True`: JavaScript no puede acceder
- `SAMESITE=Strict`: Protege contra CSRF

---

### 1.5 Agregar CSRF Protection (30 min)

**Archivo A:** `app/extensions.py`

Agrega al final:
```python
from flask_wtf import CSRFProtect
csrf = CSRFProtect()
```

**Archivo B:** `app/__init__.py`

En `create_app()`:
```python
csrf.init_app(app)
```

**Archivo C:** Todas las templates HTML

En cada formulario:
```html
<form method="POST" action="/endpoint">
    {{ csrf_token() }}  <!-- ← AGREGAR ESTA LÍNEA -->
    <!-- resto del form -->
</form>
```

**Test:**
```bash
# Intentar POST sin token → Error 400
curl -X POST http://localhost:5000/login
# Debe fallar con "CSRF token missing"
```

---

## 🚀 FASE 2: ROBUSTEZ (8-10 horas)
### Después de Phase 1 comprobada

### 2.1 Optimizar Background Jobs (2 horas)

**Archivo:** `run.py`

**Qué hacer:**
1. Reemplaza COMPLETAMENTE `run.py` con código del documento `OPTIMIZACIONES_CODIGO.md`
2. Cambios clave:
   - Procesar en batches de 100, no 1000
   - Sleep entre pacientes
   - Commit por batch
   - Logging detallado con job_id

**Verificar:**
```bash
# Verificar scheduler inicia
python run.py
# Debe mostrar: "Scheduler started successfully"
```

---

### 2.2 Validación de Inputs en Formularios (2 horas)

**Archivo:** `app/utils.py`

**Qué hacer:**
1. Crea o agrega función `handle_db_errors()` del documento
2. Usa en todos los servicios:

```python
# ANTES
def get_patient_appointments(self, patient_id):
    return Appointment.query.filter_by(patient_id=patient_id).all()

# DESPUÉS
from app.utils import handle_db_errors

@handle_db_errors
def get_patient_appointments(self, patient_id):
    return Appointment.query.filter_by(patient_id=patient_id).all()
```

**Beneficio:**
- Rollback automático en errores
- Cierre de conexión garantizado
- Logging de errores

---

### 2.3 Validación en Rutas (2 horas)

**Archivo:** `app/routes/therapist_routes.py` (y similares)

**Antes:**
```python
@therapist_routes.route('/appointment', methods=['POST'])
def create_appointment():
    data = request.get_json()
    appt = Appointment(...)  # Sin validar
    db.session.add(appt)
    db.session.commit()
```

**Después:**
```python
@therapist_routes.route('/appointment', methods=['POST'])
@login_required
def create_appointment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validar campos requeridos
        required = ['patient_id', 'start_time', 'end_time']
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({'error': f'Missing fields: {missing}'}), 400
        
        # Validar tipos
        try:
            patient_id = int(data['patient_id'])
        except:
            return jsonify({'error': 'Invalid patient_id'}), 400
        
        # Verificar acceso
        patient = User.query.get(patient_id)
        if not patient or patient.assigned_therapist_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Crear
        appt = Appointment(...)
        db.session.add(appt)
        db.session.commit()
        
        return jsonify({'success': True, 'appointment_id': appt.id}), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Appointment creation failed: {e}", exc_info=True)
        return jsonify({'error': 'Server error'}), 500
```

---

### 2.4 Validación de Uploads (2 horas)

**Archivo:** `app/routes/uploads.py`

**Qué hacer:**
1. Copia función `validate_upload()` del documento
2. Usa así:

```python
@uploads_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        file = request.files.get('file')
        
        # Validar
        errors = validate_upload(file)
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400
        
        # Generar nombre seguro con hash
        import hashlib
        ext = file.filename.rsplit('.', 1)[1].lower()
        file_hash = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)
        safe_filename = f"{file_hash}.{ext}"
        
        # Guardar en carpeta del usuario
        user_dir = os.path.join(UPLOAD_FOLDER, str(current_user.id))
        os.makedirs(user_dir, exist_ok=True, mode=0o750)
        
        filepath = os.path.join(user_dir, safe_filename)
        file.save(filepath)
        os.chmod(filepath, 0o640)  # No ejecutable
        
        return jsonify({'success': True, 'filename': safe_filename}), 201
    
    except Exception as e:
        current_app.logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'error': 'Server error'}), 500
```

---

### 2.5 Email Asincrónico (2 horas)

**OPCIONAL pero RECOMENDADO**

Si tienes Redis disponible:

1. Instala Celery:
```bash
pip install celery redis
```

2. Crea `app/celery_app.py`:
```python
from celery import Celery
import os

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    )
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
```

3. En `app/__init__.py`:
```python
from app.celery_app import make_celery

def create_app(config_class=Config):
    # ...
    app.celery = make_celery(app)
    # ...
```

4. Modifica `app/services/email_service.py`:
```python
@staticmethod
def send_email_async(to, subject, body):
    from flask import current_app
    
    def send_task():
        with current_app.app_context():
            msg = Message(subject=subject, recipients=[to], html=body)
            mail.send(msg)
    
    if hasattr(current_app, 'celery'):
        current_app.celery.send_task('send_email', args=[to, subject, body])
    else:
        from threading import Thread
        Thread(target=send_task, daemon=True).start()
```

---

## 🚀 FASE 3: SEGURIDAD (4-6 horas)
### Después que Phase 1 y 2 estén testeadas

### 3.1 Rate Limiting Realista (1 hora)

**Archivo:** `config.py`

```python
RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'redis://localhost:6379')
RATELIMIT_DEFAULT = "1000 per day,100 per hour"  # Más realista
RATELIMIT_HEADERS_ENABLED = True
```

**Archivo:** `app/routes/auth.py`

```python
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per 15 minutes")  # No muy estricto
def login():
    # ... resto ...
```

---

### 3.2 Security Headers (1 hora)

**Archivo:** `app/__init__.py` - ya incluido en `register_request_handlers()`

```python
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
```

---

### 3.3 Monitoreo y Alertas (2-4 horas)

**Recomendado: Sentry**

1. Crea cuenta en https://sentry.io (gratis)
2. En `config.py`:
```python
SENTRY_DSN = os.getenv('SENTRY_DSN')
```

3. En `.env`:
```
SENTRY_DSN=https://YOUR_KEY@sentry.io/PROJECT_ID
```

4. En `app/__init__.py`:
```python
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    
    sentry_dsn = app.config.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1
        )
        app.logger.info("Sentry initialized")
except:
    pass
```

**Beneficio:**
- Notificaciones de errores en tiempo real
- Alertas cuando ocurren crashes
- Historial de excepciones
- Stack traces completos

---

## ✅ TESTING Y VALIDACIÓN

### Test 1: Pool de Conexiones (15 min)

```bash
cd /Users/apple/Documents/moscowle_ia_mvp
python -c "
from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    # Simular 50 requests simultáneos
    for i in range(50):
        user = User.query.filter_by(email='test@test.com').first()
    print('✅ Pool test passed')
"
```

**Resultado esperado:**
- No errors
- No "QueuePool timeout"

---

### Test 2: Error Handling (10 min)

```bash
python run.py &
sleep 2

# Test 404
curl http://localhost:5000/nonexistent
# Debe retornar JSON con error

# Test CSRF
curl -X POST http://localhost:5000/login -d "email=test@test.com"
# Debe retornar 400 o 403 con CSRF error

kill %1
```

---

### Test 3: Background Jobs (5 min)

```bash
python run.py
# Esperar 5+ minutos
# Debe ver en logs: "[auto_update_...] Completed successfully"
```

---

### Test 4: Logging (5 min)

```bash
# Verificar que archivo existe y tiene contenido
tail -f /Users/apple/Documents/moscowle_ia_mvp/logs/app.log
# Debe mostrar logs JSON con timestamps
```

---

## 🔄 DEPLOYMENT A PRODUCCIÓN

### Pre-Deploy Checklist

- [ ] Todos los tests de arriba pasaron
- [ ] Cero logs de error en 24 horas de ejecución local
- [ ] `.env` configurado con valores de producción
- [ ] Base de datos respaldada
- [ ] SSH acceso verificado

### Deployment Steps

```bash
# 1. Conectar a servidor
ssh usuario@tu-servidor.com

# 2. Navegar a carpeta del proyecto
cd /path/to/moscowle_ia_mvp

# 3. Actualizar código
git pull origin main
# O: descarga archivo ZIP y extrae

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Ejecutar migraciones
python -m flask db upgrade

# 6. Iniciar con Gunicorn (producción)
gunicorn \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  run:app

# 7. Configurar supervisor/systemd para mantener corriendo
```

### Archivo Systemd (opcional)

Crear `/etc/systemd/system/moscowle.service`:
```ini
[Unit]
Description=Moscowle IA MVP
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/moscowle_ia_mvp
ExecStart=/usr/bin/gunicorn --workers 4 --bind 0.0.0.0:8000 run:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl enable moscowle
sudo systemctl start moscowle
```

---

## 📊 TIMELINE ESTIMADO

| Fase | Tareas | Horas | Recursos |
|------|--------|-------|----------|
| 1 | Pool, logging, CSRF, sesiones | 2-3h | Solo config |
| 2 | Background jobs, validación, uploads | 8-10h | Refactorización |
| 3 | Rate limit, headers, monitoreo | 4-6h | Sentry + opcional |
| Testing | Validación y deployment | 2-3h | Manual + prod |
| **TOTAL** | | **18-24h** | **Production Ready** |

---

## 🎯 MÉTRICAS DE ÉXITO

Después de implementar todo:

```
ANTES          DESPUÉS
━━━━━━━━━━━━   ━━━━━━━━━━━
Crashes: 3-5/día → 0/mes ✅
Uptime: 60% → 99.9% ✅
Response time: 5-10s → 200-500ms ✅
Memory leak: Yes → No ✅
Logs: Generic → Detailed ✅
Error tracking: None → Full ✅
User sessions: Infinite → 1h timeout ✅
CSRF protection: No → Yes ✅
```

---

## ⚠️ NOTAS FINALES

### Producción REQUIERE:
1. **HTTPS/SSL** - Obligatorio
2. **Redis** - Para rate limiting y sesiones
3. **Backups diarios** - BD + código
4. **Monitoreo** - Sentry/DataDog
5. **Logs centralizados** - ELK/Splunk

### Operaciones Mínimas Diarias:
```bash
# Revisar logs
tail -n 100 logs/app.log | grep ERROR

# Verificar salud
curl http://localhost:8000/health

# Respaldos
mysqldump moscowle_db > backups/$(date +%Y%m%d).sql
```

---

## 🆘 SI ALGO FALLA

**Problema:** App no inicia
```bash
# Ver error específico
python -c "from app import create_app; create_app()"

# Verificar config
python -c "from config import Config; print(Config.__dict__)"
```

**Problema:** Rate limiting bloqueando usuarios
```python
# En config.py, reduce limits
RATELIMIT_DEFAULT = "5000 per day,500 per hour"
```

**Problema:** Logs llenos de errores
```bash
# Limpiar logs viejos
rm logs/app.log.*

# Aumentar verbosidad para debuggear
LOG_LEVEL=DEBUG
```

**Problema:** BD lenta
```python
# En config.py, increase pool
'pool_size': 20,
'max_overflow': 40,
```

---

## 📞 SOPORTE

Si necesitas ayuda:
1. Revisa `logs/app.log` por errores específicos
2. Busca el error en Google
3. Consulta documentación oficial del paquete
4. Prueba en desarrollo antes de producción

**Tu aplicación estará lista en 24 horas.**

¡Éxito! 🚀

