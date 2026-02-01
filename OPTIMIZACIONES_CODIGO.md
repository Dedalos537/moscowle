# 🔧 OPTIMIZACIONES IMPLEMENTABLES - SEGURIDAD Y ESTABILIDAD
## Moscowle IA MVP - Código listo para copiar/pegar

---

## 📄 ARCHIVO 1: config_mejorado.py
### Reemplazar/Extender config.py con estas configuraciones

```python
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # ========== FLASK CONFIGURATION ==========
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'
    
    # ========== DATABASE OPTIMIZATION ==========
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///moscowle.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    
    # CRITICAL: Connection pool optimization to prevent leaks
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,              # Minimum persistent connections
        'max_overflow': 20,            # Additional connections under load
        'pool_timeout': 30,            # Seconds to wait for connection
        'pool_recycle': 3600,          # Recycle connections every 1 hour
        'pool_pre_ping': True,         # Test connection before using
        'echo': False                  # Disable SQL logging in production
    }
    
    # ========== GEMINI API ==========
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # ========== FILE UPLOADS ==========
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max
    ALLOWED_UPLOAD_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'webp',
        'pdf', 'mp4', 'mov', 'webm',
        'mp3', 'wav', 'ogg', 'm4a'
    }
    
    # ========== EMAIL CONFIGURATION ==========
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    # Timeout para SMTP (prevent hanging)
    MAIL_TIMEOUT = 10  # segundos
    
    # ========== SESSION CONFIGURATION - CRITICAL ==========
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # Prevent CSRF
    SESSION_COOKIE_NAME = 'moscowle_session'
    SESSION_COOKIE_MAX_AGE = 3600
    
    # Remember cookie settings
    REMEMBER_COOKIE_SECURE = os.getenv('REMEMBER_COOKIE_SECURE', 'True') == 'True'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Strict'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    
    # ========== CSRF CONFIGURATION ==========
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit on CSRF tokens
    WTF_CSRF_SSL_STRICT = os.getenv('FLASK_ENV', 'development') == 'production'
    
    # ========== SECURITY HEADERS ==========
    PREFERRED_URL_SCHEME = 'https' if ENV == 'production' else 'http'
    HSTS_SECONDS = int(os.getenv('HSTS_SECONDS', 31536000))
    HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
    
    # ========== RATE LIMITING - OPTIMIZED ==========
    # Use Redis in production: redis://localhost:6379
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = "1000 per day,100 per hour"  # Realistic limits
    
    # ========== LOGGING CONFIGURATION ==========
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB per file
    LOG_BACKUP_COUNT = 10
    
    # ========== CELERY CONFIGURATION (for async tasks) ==========
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

class DevelopmentConfig(Config):
    ENV = 'development'
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    ENV = 'production'
    DEBUG = False
    TESTING = False
    # Force HTTPS in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

class TestingConfig(Config):
    ENV = 'testing'
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Select config based on environment
_env = os.getenv('FLASK_ENV', 'development')
if _env == 'production':
    config_class = ProductionConfig
elif _env == 'testing':
    config_class = TestingConfig
else:
    config_class = DevelopmentConfig
```

---

## 📄 ARCHIVO 2: extensions_mejorado.py
### Reemplazar app/extensions.py con este código

```python
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_caching import Cache

# Database
db = SQLAlchemy()

# Password hashing
bcrypt = Bcrypt()

# Email
mail = Mail()

# OAuth2
oauth = OAuth()

# Login management
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# CSRF Protection
csrf = CSRFProtect()

# Caching (optional, for future use)
cache = Cache(config={'CACHE_TYPE': 'simple'})
```

---

## 📄 ARCHIVO 3: app_init_mejorado.py
### Reemplazar/Extender app/__init__.py con estas funciones

```python
from flask import Flask, request, jsonify, g, has_request_context
from config import Config
from app.extensions import db, bcrypt, mail, oauth, login_manager, limiter, csrf, cache
from flask_talisman import Talisman
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
import os
from uuid import uuid4
from datetime import datetime

def setup_logging(app):
    """Configure robust logging with JSON format and rotation"""
    
    # Create logs directory
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    os.makedirs(log_dir, exist_ok=True)
    
    # Remove default handlers
    app.logger.handlers.clear()
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_SIZE'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    
    # JSON formatter for production logging (ELK/Splunk compatible)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(exc_info)s'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s]: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        app.logger.addHandler(console_handler)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    
    # Log startup
    app.logger.info(
        'Application initialized',
        extra={
            'env': app.config['ENV'],
            'debug': app.debug,
            'timestamp': datetime.utcnow().isoformat()
        }
    )

def register_error_handlers(app):
    """Register global error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f"400 Bad Request: {error}")
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400
    
    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f"403 Forbidden: {error}")
        return jsonify({'error': 'Access denied'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f"429 Rate Limited: {e}")
        return jsonify({'error': 'Rate limit exceeded', 'description': str(e.description)}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        request_id = g.get('request_id', 'unknown')
        app.logger.error(
            f"500 Internal Server Error",
            exc_info=True,
            extra={'request_id': request_id}
        )
        return jsonify({
            'error': 'Internal server error',
            'request_id': request_id
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        db.session.rollback()
        request_id = g.get('request_id', 'unknown')
        app.logger.error(
            f"Unhandled exception: {type(error).__name__}",
            exc_info=True,
            extra={
                'request_id': request_id,
                'error_type': type(error).__name__
            }
        )
        return jsonify({
            'error': 'Server error',
            'request_id': request_id
        }), 500

def register_request_handlers(app):
    """Register before_request and after_request handlers"""
    
    @app.before_request
    def before_request():
        # Generate request ID for tracking
        g.request_id = str(uuid4())[:8]
        g.request_start_time = datetime.utcnow()
        
        # Log incoming request
        app.logger.debug(
            f"Request started",
            extra={
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_id': current_user.id if current_user.is_authenticated else None
            }
        )
    
    @app.after_request
    def after_request(response):
        # Calculate request duration
        duration = (datetime.utcnow() - g.request_start_time).total_seconds()
        
        # Log response
        if response.status_code >= 400:
            app.logger.warning(
                f"Request completed with error",
                extra={
                    'request_id': g.request_id,
                    'status_code': response.status_code,
                    'duration_ms': duration * 1000,
                    'method': request.method,
                    'path': request.path
                }
            )
        else:
            app.logger.debug(
                f"Request completed",
                extra={
                    'request_id': g.request_id,
                    'status_code': response.status_code,
                    'duration_ms': duration * 1000
                }
            )
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # ========== LOGGING - SETUP FIRST ==========
    setup_logging(app)
    
    # ========== SECURITY MIDDLEWARE ==========
    # ProxyFix for reverse proxies (cPanel, Nginx)
    if app.config.get('USE_PROXYFIX'):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1, x_proto=1, x_host=1, x_port=1
        )
        app.logger.info("ProxyFix middleware enabled")
    
    # Talisman for security headers and HSTS
    try:
        csp = {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com"],
            'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            'font-src': ["'self'", "https://fonts.gstatic.com"],
            'img-src': ["'self'", 'data:', 'https://ui-avatars.com'],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'self'"]
        }
        
        Talisman(app,
            content_security_policy=csp,
            content_security_policy_report_only=app.config.get('CSP_REPORT_ONLY', False),
            force_https=app.config['ENV'] == 'production',
            strict_transport_security=app.config['ENV'] == 'production',
            strict_transport_security_max_age=app.config['HSTS_SECONDS'],
            strict_transport_security_include_subdomains=app.config['HSTS_INCLUDE_SUBDOMAINS']
        )
        app.logger.info("Talisman security headers enabled")
    except Exception as e:
        app.logger.warning(f"Talisman configuration failed: {e}")
    
    # ========== INITIALIZE EXTENSIONS ==========
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    
    # ========== RATE LIMITING ==========
    try:
        limiter.init_app(app)
        app.logger.info(f"Rate limiter initialized with storage: {app.config.get('RATELIMIT_STORAGE_URL')}")
    except Exception as e:
        app.logger.warning(f"Rate limiter initialization failed: {e}")
    
    # ========== ERROR HANDLERS ==========
    register_error_handlers(app)
    register_request_handlers(app)
    
    # ========== DATABASE ==========
    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': __import__('app.models', fromlist=['User']).User
        }
    
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created/verified")
    
    # ========== BLUEPRINTS ==========
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Register additional blueprints as needed
    try:
        from app.routes.therapist_routes import therapist_bp
        app.register_blueprint(therapist_bp)
    except:
        pass
    
    try:
        from app.routes.patient_routes import patient_bp
        app.register_blueprint(patient_bp)
    except:
        pass
    
    try:
        from app.routes.api_routes import api_bp
        app.register_blueprint(api_bp)
    except:
        pass
    
    try:
        from app.routes.uploads import uploads_bp
        app.register_blueprint(uploads_bp)
    except:
        pass
    
    app.logger.info("Application initialization complete")
    return app
```

---

## 📄 ARCHIVO 4: utils_mejorado.py
### Agregar a app/utils.py o crear nuevo

```python
from functools import wraps
from app.extensions import db
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

def handle_db_errors(f):
    """
    Decorator para manejar errores de base de datos y liberar conexiones
    Debe usarse en métodos de servicios que acceden a DB
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
            return result
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(
                f"Database error in {f.__name__}",
                exc_info=True,
                extra={'function': f.__name__}
            )
            raise
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error in {f.__name__}",
                exc_info=True,
                extra={'function': f.__name__}
            )
            raise
        finally:
            # Always close the session to prevent leaks
            if db.session:
                db.session.close()
    
    return decorated_function

def validate_user_input(data, required_fields, max_lengths=None):
    """
    Generic input validation helper
    
    Args:
        data: dict with form data
        required_fields: list of required field names
        max_lengths: dict like {'email': 255, 'name': 100}
    
    Returns:
        (validated_data, errors) tuple
    """
    errors = {}
    validated = {}
    
    # Check required fields
    for field in required_fields:
        value = data.get(field, '').strip()
        if not value:
            errors[field] = f'{field} is required'
        else:
            validated[field] = value
    
    # Check max lengths
    if max_lengths:
        for field, max_len in max_lengths.items():
            if field in validated and len(validated[field]) > max_len:
                errors[field] = f'{field} must be less than {max_len} characters'
    
    return validated, errors

def safe_int(value, default=None):
    """Safely convert value to integer"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def safe_float(value, default=None):
    """Safely convert value to float"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
```

---

## 📄 ARCHIVO 5: run_mejorado.py
### Reemplazar run.py con este código OPTIMIZADO

```python
from app import create_app
from app.extensions import db
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import logging
import os
import time
from sqlalchemy.exc import SQLAlchemyError

app = create_app()

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.INFO)

def auto_update_session_status():
    """
    Background job to auto-update session statuses
    OPTIMIZED: Process in batches, handle errors gracefully
    """
    job_id = f"auto_update_{int(time.time())}"
    
    with app.app_context():
        try:
            from app.models import User
            from app.services.appointment_service import AppointmentService
            
            BATCH_SIZE = 100
            service = AppointmentService()
            
            # Get all patients
            patients = User.query.filter_by(role='jugador').all()
            total = len(patients)
            
            app.logger.info(f"[{job_id}] Starting auto-update for {total} patients")
            
            # Process in batches
            for idx in range(0, total, BATCH_SIZE):
                batch = patients[idx:idx + BATCH_SIZE]
                
                for patient in batch:
                    try:
                        service.update_expired_appointments(patient.id)
                    except SQLAlchemyError as e:
                        app.logger.warning(f"DB error for patient {patient.id}: {e}")
                        db.session.rollback()
                        continue
                    except Exception as e:
                        app.logger.error(f"Error processing patient {patient.id}: {e}", exc_info=True)
                        continue
                    
                    # Small delay to prevent CPU overload
                    time.sleep(0.01)
                
                # Commit batch and cleanup
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
                finally:
                    db.session.close()
                
                batch_num = (idx // BATCH_SIZE) + 1
                app.logger.info(f"[{job_id}] Processed batch {batch_num}/{(total // BATCH_SIZE) + 1}")
                
                # Pause between batches
                time.sleep(0.5)
            
            app.logger.info(f"[{job_id}] Completed successfully")
            
        except SQLAlchemyError as e:
            app.logger.error(f"[{job_id}] Database error: {str(e)}", exc_info=True)
            db.session.rollback()
        except Exception as e:
            app.logger.error(f"[{job_id}] Unexpected error: {str(e)}", exc_info=True)


def check_payment_reminders():
    """
    Background job to send payment reminders
    OPTIMIZED: Error handling and logging
    """
    job_id = f"payment_check_{int(time.time())}"
    
    with app.app_context():
        try:
            from app.services.payment_service import PaymentService
            
            app.logger.info(f"[{job_id}] Starting payment reminder check")
            
            payment_service = PaymentService()
            
            try:
                count = payment_service.check_upcoming_due_dates()
                deactivated = payment_service.check_and_deactivate_overdue()
                
                if count > 0 or deactivated > 0:
                    app.logger.info(
                        f"[{job_id}] Sent {count} reminders, Deactivated {deactivated} users"
                    )
            except SQLAlchemyError as e:
                app.logger.error(f"[{job_id}] DB error: {e}")
                db.session.rollback()
            finally:
                db.session.close()
                
        except Exception as e:
            app.logger.error(f"[{job_id}] Unexpected error: {str(e)}", exc_info=True)


# ========== SCHEDULER CONFIGURATION ==========
scheduler = BackgroundScheduler(daemon=True)

# Add jobs with proper configuration
scheduler.add_job(
    func=auto_update_session_status,
    trigger=IntervalTrigger(minutes=5),  # Every 5 minutes (not every 1)
    max_instances=1,  # Only one instance at a time
    id='auto_update_sessions',
    name='Auto-update expired appointments',
    coalesce=True,  # Skip missed runs if delayed
    misfire_grace_time=60  # 60 second grace period
)

scheduler.add_job(
    func=check_payment_reminders,
    trigger=IntervalTrigger(hours=1),  # Every hour
    max_instances=1,
    id='payment_reminders',
    name='Check payment reminders',
    coalesce=True,
    misfire_grace_time=60
)

# Start scheduler
try:
    scheduler.start()
    app.logger.info("Scheduler started successfully")
except Exception as e:
    app.logger.error(f"Failed to start scheduler: {e}")

# Ensure scheduler shuts down gracefully
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV', 'development') == 'development'
    )

# For production, use:
# gunicorn --workers 4 --bind 0.0.0.0:8000 --timeout 120 --access-logfile - --error-logfile - run:app
```

---

## 📄 ARCHIVO 6: CSRF Protection en Templates

### Agregar a TODAS las templates HTML con formularios

```html
<!-- En app/templates/base.html HEAD -->
<meta name="csrf-token" content="{{ csrf_token() }}">

<!-- En CADA FORMULARIO -->
<form method="POST" action="/endpoint">
    {{ csrf_token() }}
    <!-- resto del formulario -->
</form>

<!-- En JavaScript para AJAX -->
<script>
// Get CSRF token from meta tag
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

// Use in fetch requests
function apiCall(url, data) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
}

// Example usage
apiCall('/api/appointment', {
    patient_id: 1,
    start_time: '2026-01-25T10:00:00',
    end_time: '2026-01-25T11:00:00'
})
.then(r => r.json())
.then(d => console.log(d))
.catch(e => console.error(e));
</script>
```

---

## 📊 CHECKLIST IMPLEMENTACIÓN

- [ ] Actualizar `config.py` con pool de conexiones
- [ ] Reemplazar `app/extensions.py` con versión mejorada
- [ ] Extender `app/__init__.py` con error handlers y logging
- [ ] Agregar `app/utils.py` con decorators
- [ ] Reemplazar `run.py` con versión optimizada
- [ ] Agregar CSRF tokens a todas las templates
- [ ] Testear en desarrollo: `python run.py`
- [ ] Verificar logs en `logs/app.log`
- [ ] Desplegar a producción con `gunicorn --workers 4`

---

## ⚠️ NOTAS IMPORTANTES

1. **Redis recomendado**: Para rate limiting y Celery en producción
2. **Email asincrónico**: Considera implementar Celery + Redis
3. **Monitoreo**: Implementar Sentry para alertas de errores
4. **Backups**: Configurar backups diarios de BD
5. **SSL/TLS**: Obligatorio en producción (Let's Encrypt)

