from flask import Flask, request, jsonify, g, has_request_context, render_template
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

def register_auth_loader(app):
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        if user_id is None:
            return None
        return User.query.get(int(user_id))

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
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f"429 Rate Limited: {e}")
        # Return JSON for API calls, HTML for browser
        if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
             return jsonify({'error': 'Rate limit exceeded', 'description': str(e.description)}), 429
        return render_template('errors/429.html', error=e), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        request_id = g.get('request_id', 'unknown')
        app.logger.error(
            f"500 Internal Server Error",
            exc_info=True,
            extra={'request_id': request_id}
        )
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({
                'error': 'Internal server error',
                'request_id': request_id
            }), 500
        return render_template('errors/500.html', error=error), 500
    
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
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({
                'error': 'Server error',
                'request_id': request_id
            }), 500
        return render_template('errors/500.html', error=error), 500

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
    if app.config.get('USE_PROXYFIX', True):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1, x_proto=1, x_host=1, x_port=1
        )
        app.logger.info("ProxyFix middleware enabled")
    
    # Talisman for security headers and HSTS
    try:
        csp = {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com", "https://cdnjs.cloudflare.com", "https://cdn.jsdelivr.net", "https://npmcdn.com"],
            'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
            'font-src': ["'self'", "data:", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com"],
            'img-src': ["'self'", 'data:', 'https://ui-avatars.com'],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'self'"]
        }
        
        Talisman(app,
            content_security_policy=csp,
            content_security_policy_report_only=False, # Enforce policy instead of report-only without URI
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
    register_auth_loader(app)
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
        try:
            db.create_all()
            app.logger.info("Database tables created/verified")
        except Exception as e:
             app.logger.error(f"Database creation failed: {e}")
    
    # ========== BLUEPRINTS ==========
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Register additional blueprints
    from app.routes.therapist_routes import therapist_bp
    app.register_blueprint(therapist_bp)
    
    from app.routes.patient_routes import patient_bp
    app.register_blueprint(patient_bp)
    
    from app.routes.api_routes import api_bp
    app.register_blueprint(api_bp)
    
    from app.routes.uploads import uploads_bp
    app.register_blueprint(uploads_bp)
        
    from app.routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    # Register Async DAO API Blueprint (V2)
    from app.routes.async_api_routes import async_api_bp
    app.register_blueprint(async_api_bp)

    # Add other routes here...
    
    # ========== BACKGROUND TASKS ==========
    try:
        from app.tasks import init_scheduler
        init_scheduler(app)
        app.logger.info("Scheduler initialized")
    except Exception as e:
        app.logger.error(f"Scheduler initialization failed: {e}")
    
    app.logger.info("Application initialization complete")
    return app
