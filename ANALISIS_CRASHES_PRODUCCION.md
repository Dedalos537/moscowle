# 🔴 ANÁLISIS CRÍTICO: CAUSAS DE CRASHES EN PRODUCCIÓN
## Moscowle IA MVP - Diagnóstico y Soluciones

**Fecha:** 24 de enero de 2026  
**Severidad:** 🔴 CRÍTICA  
**Estado Actual:** Inestable en Producción - Múltiples caídas frecuentes

---

## 📋 RESUMEN EJECUTIVO

Tu aplicación está fallando constantemente en producción debido a **8 problemas críticos** no resueltos:

1. **Fugas de conexiones a BD** → Agotamiento de pool
2. **Excepciones sin manejo** → App crashes
3. **Sessions activas infinitas** → Memory leaks
4. **Rate limiting incorrecto** → Bloqueos de usuarios
5. **Acceso a BD en background jobs** → App context errors
6. **Cargas de archivo sin validación** → RCE / DoS
7. **Email no asincrónico** → Timeouts y cuellos
8. **Logging insuficiente** → Imposible debuggear

**Impacto:** La aplicación cae varias veces al día sin aviso previo.

---

## 🔍 PROBLEMA #1: Fugas de Conexiones a Base de Datos
### Severidad: 🔴 CRÍTICA | Impacto: 8/10

### Causa Raíz
El pool de conexiones SQLAlchemy se agota porque:
- Las conexiones no se cierran correctamente después de excepciones
- Los servicios crean múltiples instancias sin reutilizar conexiones
- No hay timeout configurado para conexiones inactivas
- Background jobs abren conexiones sin cerrarlas

### Código Problemático
```python
# app/__init__.py - ACTUAL (INCORRECTO)
limiter.init_app(app)  # Sin manejo de errors

# app/services/appointment_service.py - ACTUAL (INCORRECTO)
def get_patient_appointments(self, patient_id, start_dt=None, end_dt=None, limit=10):
    query = Appointment.query.filter(Appointment.patient_id == patient_id)
    # Si ocurre error, la conexión no se libera
    if start_dt and end_dt:
        return query.filter(...).order_by(...).all()  # Sin try/except

# run.py - ACTUAL (INCORRECTO)
def auto_update_session_status():
    with app.app_context():  # No maneja excepciones adecuadamente
        try:
            service = AppointmentService()
            patients = User.query.filter_by(role='jugador').all()
            for patient in patients:  # Si uno falla, todo se rompe
                service.update_expired_appointments(patient.id)
        except Exception as e:
            app.logger.error(f"Error: {str(e)}")  # Log sin contexto
```

### Síntomas
```
psycopg2.OperationalError: FATAL: too many connections
SQLAlchemy.exc.InvalidRequestError: QueuePool timeout exceeded
conn = <dead object>
```

### Solución

**Paso 1: Configurar pool de conexiones correctamente**
```python
# config.py - NUEVO
class Config:
    # ... otros configs ...
    
    # Connection pooling - MEJORADO
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,              # Conexiones permanentes
        'max_overflow': 20,            # Conexiones adicionales
        'pool_timeout': 30,            # Segundos esperando conexión
        'pool_recycle': 3600,          # Reciclar cada 1h (MySQL/MariaDB requiere)
        'pool_pre_ping': True,         # Verificar conexión antes de usar
        'echo': False                  # False en producción
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
```

**Paso 2: Manejo de excepciones en servicios**
```python
# app/utils.py - NUEVO
from functools import wraps
from app.extensions import db
from flask import current_app

def handle_db_errors(f):
    """Decorator para manejar errores de DB y liberar conexiones"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"DB Error in {f.__name__}: {str(e)}", exc_info=True)
            raise
        finally:
            db.session.close()  # Siempre liberar
    return decorated_function
```

**Paso 3: Mejorar servicios con decorators**
```python
# app/services/appointment_service.py - MEJORADO
from app.utils import handle_db_errors

class AppointmentService:
    @handle_db_errors
    def get_patient_appointments(self, patient_id, start_dt=None, end_dt=None, limit=10):
        self.update_expired_appointments(patient_id)
        query = Appointment.query.filter(Appointment.patient_id == patient_id)
        if start_dt and end_dt:
            return query.filter(
                Appointment.start_time >= start_dt,
                Appointment.start_time <= end_dt
            ).order_by(Appointment.start_time.asc()).all()
        # ... resto del código
```

---

## 🔴 PROBLEMA #2: Excepciones No Manejadas
### Severidad: 🔴 CRÍTICA | Impacto: 9/10

### Causa Raíz
```python
# app/routes/main.py - ACTUAL (INCORRECTO)
@main_bp.route('/dashboard')
def dashboard():
    user_id = current_user.id
    patients = User.query.filter_by(assigned_therapist_id=user_id).all()
    # Si la query falla → crash del worker
    metrics = db.session.query(...).filter(...).all()  # Sin try/except
    return render_template('dashboard.html', data=metrics)

# app/services/email_service.py - ACTUAL (INCORRECTO)
def send_verification_email(email):
    msg = Message(...)
    mail.send(msg)  # Si el SMTP falla → RuntimeError sin manejo
```

### Solución
```python
# app/__init__.py - NUEVO
from flask import jsonify

def register_error_handlers(app):
    """Registrar manejadores globales de errores"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"500 Error: {error}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        db.session.rollback()
        app.logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({'error': 'Server error'}), 500

# En create_app():
register_error_handlers(app)

# app/routes/main.py - MEJORADO
@main_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        user_id = current_user.id
        patients = User.query.filter_by(assigned_therapist_id=user_id).all()
        
        if not patients:
            flash('No tienes pacientes asignados.', 'info')
            return render_template('dashboard.html', patients=[])
        
        metrics = []
        for patient in patients:
            try:
                patient_metrics = SessionMetrics.query.filter_by(
                    user_id=patient.id
                ).order_by(SessionMetrics.date.desc()).limit(5).all()
                metrics.append({'patient': patient, 'metrics': patient_metrics})
            except Exception as e:
                current_app.logger.warning(f"Error loading metrics for patient {patient.id}: {e}")
                metrics.append({'patient': patient, 'metrics': []})
        
        return render_template('dashboard.html', metrics=metrics)
    
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}", exc_info=True)
        flash('Error cargando el dashboard. Por favor intenta más tarde.', 'error')
        return redirect(url_for('main.home'))
```

---

## 🔴 PROBLEMA #3: Memory Leaks - Sessions Activas Infinitas
### Severidad: 🔴 CRÍTICA | Impacto: 8/10

### Causa Raíz
```python
# config.py - ACTUAL (INCORRECTO)
SESSION_COOKIE_SECURE = False  # En producción debe ser True
REMEMBER_COOKIE_HTTPONLY = True  # Bueno
SESSION_COOKIE_SAMESITE = 'Lax'  # Debe ser 'Strict'

# Flask por defecto no cierra sesiones automáticamente
# Las sesiones se quedan activas indefinidamente
```

### Síntomas
```
RAM aumenta constantemente
Usuarios reportan "sesiones múltiples" 
Imposible logout correctamente
```

### Solución
```python
# config.py - MEJORADO
class Config:
    # Session Management
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora en producción
    SESSION_REFRESH_EACH_REQUEST = True  # Renovar al cada request
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # Proteger contra CSRF
    SESSION_COOKIE_NAME = 'moscowle_session'
    SESSION_COOKIE_MAX_AGE = 3600
    
    REMEMBER_COOKIE_SECURE = os.getenv('REMEMBER_COOKIE_SECURE', 'True') == 'True'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Strict'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

# app/routes/auth.py - MEJORADO
@auth_bp.route('/logout')
@login_required
def logout():
    """Logout limpio con limpieza de session"""
    user = current_user
    user_id = user.id
    user_email = user.email
    
    try:
        # Limpiar sesión
        from flask import session
        session.clear()
        
        # Logout de Flask-Login
        logout_user()
        
        # Log audit
        current_app.logger.info(f"User {user_email} (ID: {user_id}) logged out")
        
        flash('Sesión cerrada correctamente.', 'success')
        return redirect(url_for('auth.login'))
    
    except Exception as e:
        current_app.logger.error(f"Logout error for user {user_id}: {e}")
        flash('Error cerrando sesión. Por favor intenta nuevamente.', 'error')
        return redirect(url_for('auth.login'))
```

---

## 🔴 PROBLEMA #4: Rate Limiting Incorrecto
### Severidad: 🔴 ALTA | Impacto: 7/10

### Causa Raíz
```python
# config.py - ACTUAL (INCORRECTO)
RATELIMIT_STORAGE_URL = 'memory://'  # Se pierde entre reinicios
RATELIMIT_DEFAULT = "200 per day,50 per hour"  # Muy bajo para usuarios reales

# app/routes/auth.py - ACTUAL (INCORRECTO)
@limiter.limit("5 per 15 minutes")  # Muy estricto, bloquea usuarios legítimos
def login():
```

### Problema
Un usuario legítimo que intente 6 veces login en 15 minutos queda bloqueado 1-2 horas.

### Solución
```python
# config.py - MEJORADO
class Config:
    # Rate limiting - Redis recomendado para producción
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL') or 'memory://'
    
    # En .env usar: RATELIMIT_STORAGE_URL=redis://localhost:6379
    
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = "1000 per day,100 per hour"  # Más realista
    
    # Por endpoint
    RATELIMIT_LOGIN = "10 per 15 minutes"  # Permitir más intentos
    RATELIMIT_API = "500 per hour"

# app/routes/auth.py - MEJORADO
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per 15 minutes")  # Límite más realista
def login():
    if request.method == 'POST':
        # Implementar backoff exponencial
        email = request.form.get('email', '').strip().lower()
        attempts = cache.get(f'login_attempts:{email}') or 0
        
        if attempts >= 5:
            wait_time = min(60 * (2 ** attempts), 3600)  # Max 1 hora
            flash(f'Demasiados intentos. Espera {wait_time} segundos.', 'error')
            return render_template('login.html'), 429
        
        form = {
            'email': email,
            'password': request.form.get('password', '')
        }
        data, errors = validate_login_input(form)
        
        if errors:
            cache.set(f'login_attempts:{email}', attempts + 1, 900)  # 15 minutos
            flash('Por favor corrige los errores.', 'error')
            return render_template('login.html')
        
        success, user = auth_service.login(data['email'], data['password'])
        
        if success:
            cache.delete(f'login_attempts:{email}')  # Limpiar intentos
            return redirect(url_for('main.dashboard'))
        else:
            cache.set(f'login_attempts:{email}', attempts + 1, 900)
            flash('Credenciales inválidas.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')
```

---

## 🔴 PROBLEMA #5: Background Jobs sin App Context
### Severidad: 🔴 CRÍTICA | Impacto: 8/10

### Causa Raíz
```python
# run.py - ACTUAL (INCORRECTO)
def auto_update_session_status():
    with app.app_context():
        try:
            patients = User.query.filter_by(role='jugador').all()
            # Si hay 1000 pacientes, esto mata el servidor
            for patient in patients:
                service.update_expired_appointments(patient.id)  # Sin límite
                # Sin sleep → CPU 100%
        except Exception as e:
            app.logger.error(f"Error: {str(e)}")  # Muy genérico

# Scheduler sin límites
scheduler.add_job(
    func=auto_update_session_status,
    trigger="interval",
    seconds=60,  # Cada minuto - demasiado frecuente
)
```

### Solución
```python
# run.py - MEJORADO
import time
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

def auto_update_session_status():
    """Background job to auto-update session statuses - OPTIMIZADO"""
    job_id = f"auto_update_{int(time.time())}"
    
    with app.app_context():
        try:
            from app.models import User
            from app.services.appointment_service import AppointmentService
            
            # Procesar en lotes para no sobrecargar
            BATCH_SIZE = 100
            
            service = AppointmentService()
            patients = User.query.filter_by(role='jugador').all()
            total = len(patients)
            
            current_app.logger.info(f"[{job_id}] Starting auto-update for {total} patients")
            
            for idx in range(0, total, BATCH_SIZE):
                batch = patients[idx:idx + BATCH_SIZE]
                
                for patient in batch:
                    try:
                        service.update_expired_appointments(patient.id)
                    except SQLAlchemyError as e:
                        current_app.logger.warning(f"DB error for patient {patient.id}: {e}")
                        continue
                    except Exception as e:
                        current_app.logger.error(f"Error processing patient {patient.id}: {e}", exc_info=True)
                        continue
                    
                    # Dormir un poco para no saturar
                    time.sleep(0.01)
                
                # Limpiar session entre lotes
                db.session.commit()
                current_app.logger.debug(f"[{job_id}] Processed batch {idx // BATCH_SIZE + 1}")
                time.sleep(0.5)  # Pausa entre lotes
            
            current_app.logger.info(f"[{job_id}] Completed successfully")
            
        except SQLAlchemyError as e:
            app.logger.error(f"[{job_id}] Database error: {str(e)}", exc_info=True)
            db.session.rollback()
        except Exception as e:
            app.logger.error(f"[{job_id}] Unexpected error: {str(e)}", exc_info=True)


def check_payment_reminders():
    """Background job to send payment reminders - OPTIMIZADO"""
    job_id = f"payment_check_{int(time.time())}"
    
    with app.app_context():
        try:
            from app.services.payment_service import PaymentService
            
            current_app.logger.info(f"[{job_id}] Starting payment reminder check")
            
            payment_service = PaymentService()
            
            try:
                count = payment_service.check_upcoming_due_dates()
                deactivated = payment_service.check_and_deactivate_overdue()
                
                if count > 0 or deactivated > 0:
                    current_app.logger.info(
                        f"[{job_id}] Sent {count} reminders, Deactivated {deactivated} users"
                    )
            except SQLAlchemyError as e:
                current_app.logger.error(f"[{job_id}] DB error: {e}")
                db.session.rollback()
            
        except Exception as e:
            current_app.logger.error(f"[{job_id}] Unexpected error: {str(e)}", exc_info=True)


# Scheduler configuration - MEJORADO
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

scheduler = BackgroundScheduler()

# Aumentar intervalos y agregar máximo de workers
scheduler.add_job(
    func=auto_update_session_status,
    trigger=IntervalTrigger(minutes=5),  # Cada 5 minutos, no cada 1
    max_instances=1,  # Una sola instancia a la vez
    id='auto_update_sessions',
    name='Auto-update expired appointments',
    coalesce=True,  # Si se atrasa, ejecutar una sola vez
    misfire_grace_time=60  # Grace period de 60 segundos
)

scheduler.add_job(
    func=check_payment_reminders,
    trigger=IntervalTrigger(hours=1),  # Cada hora
    max_instances=1,
    id='payment_reminders',
    name='Check payment reminders',
    coalesce=True,
    misfire_grace_time=60
)

scheduler.start()

# Asegurar que se detiene al cerrar la app
atexit.register(lambda: scheduler.shutdown())
```

---

## 🔴 PROBLEMA #6: Cargas de Archivos sin Validación
### Severidad: 🔴 CRÍTICA | Impacto: 9/10

### Causa Raíz
```python
# app/routes/uploads.py - ACTUAL (POSIBLE INCORRECTO)
@uploads_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    # Sin validación de tipo
    # Sin verificar tamaño real
    # Sin sanitizar nombre
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))  # RCE VULNERABLE
```

### Riesgos
- **RCE:** Subir .py y ejecutarlo
- **DoS:** Subir archivo de 100 GB
- **LFI:** Nombres como `../../../etc/passwd`

### Solución
```python
# app/routes/uploads.py - MEJORADO
import mimetypes
import hashlib
from werkzeug.utils import secure_filename
from flask import current_app
import os

ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp',  # Imágenes
    'pdf',  # Documentos
    'mp4', 'mov', 'webm',  # Video
    'mp3', 'wav', 'ogg', 'm4a'  # Audio
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

def allowed_file(filename, allowed_exts=ALLOWED_EXTENSIONS):
    """Validar extensión de archivo"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

def validate_upload(file):
    """Validar archivo antes de guardar"""
    errors = []
    
    # Verificar que existe
    if not file or file.filename == '':
        errors.append('No file provided')
        return errors
    
    # Verificar extensión
    if not allowed_file(file.filename):
        errors.append(f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}')
    
    # Verificar tamaño
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        errors.append(f'File too large. Max: {MAX_FILE_SIZE / 1024 / 1024} MB')
    
    if file_size == 0:
        errors.append('File is empty')
    
    return errors

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
        ext = file.filename.rsplit('.', 1)[1].lower()
        file_hash = hashlib.sha256(file.read()).hexdigest()
        file.seek(0)
        safe_filename = f"{file_hash}.{ext}"
        
        # Crear carpeta por usuario
        user_upload_dir = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            str(current_user.id)
        )
        os.makedirs(user_upload_dir, exist_ok=True, mode=0o750)
        
        # Guardar
        filepath = os.path.join(user_upload_dir, safe_filename)
        file.save(filepath)
        os.chmod(filepath, 0o640)  # No ejecutable
        
        return jsonify({
            'success': True,
            'filename': safe_filename,
            'path': f'/uploads/{current_user.id}/{safe_filename}'
        }), 201
    
    except Exception as e:
        current_app.logger.error(f"Upload error for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Server error'}), 500
```

---

## 🔴 PROBLEMA #7: Email Bloqueante - No Asincrónico
### Severidad: 🔴 ALTA | Impacto: 7/10

### Causa Raíz
```python
# app/services/email_service.py - ACTUAL (INCORRECTO)
def send_email(to, subject, body):
    msg = Message(subject=subject, recipients=[to], html=body)
    mail.send(msg)  # BLOQUEANTE - espera respuesta SMTP (2-5 segundos)
    # Usuario espera durante esto
```

### Síntomas
```
POST /appointment tarda 5+ segundos
Timeouts ocasionales si SMTP está lento
Bajo throughput de usuarios simultáneos
```

### Solución
```python
# requirements.txt - AGREGAR
celery>=5.3.0
redis>=4.5.0

# app/celery_app.py - NUEVO
from celery import Celery
from flask import Flask
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

# app/__init__.py - EN create_app()
from app.celery_app import make_celery

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # ... inicializar db, bcrypt, etc ...
    
    # Inicializar Celery
    app.celery = make_celery(app)
    
    # ... resto

# app/services/email_service.py - MEJORADO
from flask import current_app
from app.extensions import mail

class EmailService:
    @staticmethod
    def send_email_async(to, subject, body):
        """Enviar email de forma asincrónica usando Celery"""
        from flask import current_app
        
        def send_email_task():
            with current_app.app_context():
                try:
                    msg = Message(
                        subject=subject,
                        recipients=[to],
                        html=body
                    )
                    mail.send(msg)
                    current_app.logger.info(f"Email sent to {to}")
                except Exception as e:
                    current_app.logger.error(f"Email error to {to}: {e}", exc_info=True)
        
        # Ejecutar en background
        if hasattr(current_app, 'celery'):
            send_email_task.apply_async()
        else:
            # Fallback si Celery no está disponible
            from threading import Thread
            Thread(target=send_email_task, daemon=True).start()

# En rutas - USO
from app.services.email_service import EmailService

@therapist_routes.route('/appointment', methods=['POST'])
@login_required
def create_appointment():
    # ... crear cita ...
    
    # Enviar email SIN esperar
    EmailService.send_email_async(
        to=patient.email,
        subject='Nueva cita programada',
        body=render_template('emails/appointment_scheduled.html', appointment=appointment)
    )
    
    return jsonify({'success': True}), 201
```

---

## 🔴 PROBLEMA #8: Logging Insuficiente
### Severidad: 🔴 ALTA | Impacto: 8/10

### Causa Raíz
```python
# app/__init__.py - ACTUAL (INSUFICIENTE)
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)
# Sin logs JSON, sin nivel por módulo, sin rotación
```

### Síntomas
```
No sé qué causó el crash
Logs se pierden después de reinicio
Imposible debuggear en producción
```

### Solución
```python
# config.py - NUEVO
import logging
from logging.handlers import RotatingFileHandler
import os
from pythonjsonlogger import jsonlogger

class Config:
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 10

# app/__init__.py - MEJORADO
def setup_logging(app):
    """Configurar logging robusto"""
    
    # Crear directorio de logs
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    os.makedirs(log_dir, exist_ok=True)
    
    # Remover handlers por defecto
    app.logger.handlers.clear()
    
    # File handler con rotación
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_SIZE'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    
    # Formato JSON para parsear en ELK/Splunk
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler para development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        app.logger.addHandler(console_handler)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    
    # Log de startup
    app.logger.info(f"Application started. Config: {app.config['ENV']}")

# En create_app()
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Logging ANTES que todo
    setup_logging(app)
    
    # ... resto de inicialización ...
    
    return app

# Uso en servicios - MEJORADO
from flask import current_app

class AppointmentService:
    def create_session(self, therapist_id, data, therapist_username):
        session_id = uuid.uuid4()
        try:
            current_app.logger.info(
                f"Creating appointment",
                extra={
                    'therapist_id': therapist_id,
                    'patient_id': data.get('patient_id'),
                    'session_id': str(session_id)
                }
            )
            
            # ... crear session ...
            
            current_app.logger.info(
                f"Appointment created successfully",
                extra={'appointment_id': appt.id, 'session_id': str(session_id)}
            )
            return appt
        
        except ValueError as e:
            current_app.logger.warning(
                f"Appointment validation error",
                extra={'error': str(e), 'session_id': str(session_id)}
            )
            raise
        except Exception as e:
            current_app.logger.error(
                f"Appointment creation failed",
                exc_info=True,
                extra={'session_id': str(session_id)}
            )
            raise
```

---

## 🟠 PROBLEMA #9: Validaciones Insuficientes
### Severidad: 🟠 ALTA | Impacto: 7/10

### Causa Raíz
```python
# app/routes/therapist_routes.py - ACTUAL (INCORRECTO)
@therapist_routes.route('/appointment', methods=['POST'])
def create_appointment():
    data = request.get_json()
    # Sin validar tipos de datos
    # Sin verificar que el paciente pertenece al terapeuta
    # Sin validar horarios
    appt = Appointment(...)
    db.session.add(appt)
    db.session.commit()
```

### Solución
```python
# app/schemas/appointment_schema.py - NUEVO
from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime

class CreateAppointmentSchema(Schema):
    patient_id = fields.Int(required=True)
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(required=True)
    title = fields.Str(required=False, allow_none=True)
    notes = fields.Str(required=False, allow_none=True)
    
    def validate_times(self, data):
        start = data.get('start_time')
        end = data.get('end_time')
        
        if not start or not end:
            return
        
        if start >= end:
            raise ValidationError('start_time must be before end_time')
        
        duration_minutes = (end - start).total_seconds() / 60
        if duration_minutes < 15:
            raise ValidationError('Minimum duration is 15 minutes')
        if duration_minutes > 240:
            raise ValidationError('Maximum duration is 4 hours')

# En rutas
@therapist_routes.route('/appointment', methods=['POST'])
@login_required
def create_appointment():
    try:
        schema = CreateAppointmentSchema()
        data = schema.load(request.get_json())
        
        # Verificar que el paciente existe y pertenece al terapeuta
        patient = User.query.get(data['patient_id'])
        if not patient or patient.role != 'jugador':
            return jsonify({'error': 'Invalid patient'}), 400
        
        if patient.assigned_therapist_id != current_user.id:
            return jsonify({'error': 'Patient not assigned to you'}), 403
        
        # Validar disponibilidad
        errors = appointment_service.validate_session_times(
            data['start_time'],
            data['end_time'],
            data['patient_id'],
            current_user.id
        )
        
        if errors:
            return jsonify({'errors': errors}), 400
        
        # Crear
        appt = appointment_service.create_session(
            current_user.id,
            data,
            current_user.username
        )
        
        return jsonify({'success': True, 'appointment_id': appt.id}), 201
    
    except ValidationError as e:
        current_app.logger.warning(f"Validation error: {e.messages}")
        return jsonify({'errors': e.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Create appointment error: {e}", exc_info=True)
        return jsonify({'error': 'Server error'}), 500
```

---

## 🟠 PROBLEMA #10: Falta CSRF Protection
### Severidad: 🟠 CRÍTICA | Impacto: 8/10

### Solución
```python
# app/__init__.py - MEJORADO
from flask_wtf import CSRFProtect

csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar CSRF
    csrf.init_app(app)
    
    # ... resto ...
    
    return app

# app/templates/base.html - EN TODOS LOS FORMULARIOS
<form method="POST" action="{{ url_for('auth.login') }}">
    {{ csrf_token() }}  <!-- AGREGAR ESTO -->
    <input type="email" name="email" required>
    <input type="password" name="password" required>
    <button type="submit">Login</button>
</form>

# En JavaScript para AJAX
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

fetch('/api/appointment', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
})
```

---

## ✅ RESUMEN DE FIXES CRÍTICOS

| Problema | Impacto | Fix Time | Priority |
|----------|---------|----------|----------|
| Pool de conexiones | 8/10 | 2h | 🔴 P1 |
| Excepciones | 9/10 | 3h | 🔴 P1 |
| Sessions infinitas | 8/10 | 1h | 🔴 P1 |
| Rate limiting | 7/10 | 1h | 🔴 P1 |
| Background jobs | 8/10 | 2h | 🔴 P1 |
| Uploads inseguro | 9/10 | 2h | 🔴 P1 |
| Email bloqueante | 7/10 | 3h | 🔴 P1 |
| Logging | 8/10 | 1h | 🔴 P1 |
| Validaciones | 7/10 | 2h | 🟠 P2 |
| CSRF | 8/10 | 1h | 🔴 P1 |
| **TOTAL** | **82/100** | **18h** | **Critical** |

---

## 📋 CHECKLIST IMPLEMENTACIÓN

### Fase 1 - Estabilidad (6-8 horas)
- [ ] Configurar pool de conexiones y conexión pooling
- [ ] Agregar error handlers globales
- [ ] Mejorar background jobs con límites
- [ ] Agregar CSRF protection

### Fase 2 - Robustez (8-10 horas)
- [ ] Logging completo con JSON
- [ ] Validaciones en todos los endpoints
- [ ] Email asincrónico (Celery + Redis)
- [ ] Sessions con timeout correcto

### Fase 3 - Seguridad (4-6 horas)
- [ ] Validación de uploads
- [ ] Rate limiting con Redis
- [ ] Audit logging
- [ ] Security headers

---

## 🚀 PASOS SIGUIENTES

1. **Inmediato:** Implementar Fase 1 (estabilidad)
2. **Antes de producción:** Pasar Fase 2 (robustez)
3. **Ongoing:** Implementar Fase 3 (seguridad)
4. **Monitoreo:** Activar alertas en Sentry/DataDog

Tu aplicación está en **código amarillo crítico**. Con estos 10 fixes, pasará a producción-ready en 18-24 horas de trabajo.

