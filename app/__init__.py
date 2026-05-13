from flask import Flask, request, jsonify, g, has_request_context, render_template
from config import Config
from app.extensions import db, bcrypt, mail, oauth, login_manager, limiter, csrf, cache, cors
from flask_talisman import Talisman
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
import os
from uuid import uuid4
from datetime import datetime
import hashlib

def register_auth_loader(app):
    try:
        from app.models import User

        @login_manager.user_loader
        def load_user(user_id):
            if user_id is None:
                return None
            try:
                return User.query.get(int(user_id))
            except Exception:
                # If DB is unavailable, avoid raising and return None so login_manager continues safely
                app.logger.debug('User lookup failed in user_loader; DB may be unavailable')
                return None
    except Exception as e:
        # Ensure a user_loader is always registered to avoid flask-login raising "Missing user_loader"
        def _dummy_loader(user_id):
            return None

        login_manager.user_loader(_dummy_loader)
        try:
            app.logger.warning(f"register_auth_loader failed to import models: {e}")
        except Exception:
            pass
            
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/') or request.path.startswith('/admin/api/') or getattr(g, 'is_api', False) or request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'message': 'Unauthorized - Please log in'}), 401
        from flask import redirect, url_for
        return redirect(url_for('auth.login', next=request.url))

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
    # CSRF errors should return JSON for API calls
    try:
        from flask_wtf.csrf import CSRFError
        from app.utils.api_helpers import api_response

        @app.errorhandler(CSRFError)
        def handle_csrf_error(e):
            app.logger.warning(f"CSRFError: {e}")
            if getattr(g, 'is_api', False) or request.accept_mimetypes.accept_json:
                return api_response(False, error={'message': str(e)}, status=400)
            return render_template('errors/csrf.html', reason=str(e)), 400
    except Exception:
        # flask-wtf may not be installed in some environments
        pass
    
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
        # Mark whether this request is an API call
        try:
            from app.utils.api_helpers import mark_request_api
            mark_request_api()
        except Exception:
            g.is_api = False
            
        # Validate App Key for API requests to ensure only edysync frontend can access
        if request.path.startswith('/api/') or request.path.startswith('/admin/api/'):
            # Skip X-App-Key validation for:
            # 1. Webhook endpoints
            # 2. /api/auth/* (called from Jinja login.html, not Angular)
            # 3. Requests with a valid Flask session (user is already authenticated
            #    via cookie — these come from Jinja templates, not Angular)
            skip_appkey = (
                'webhook' in request.path
                or request.path.startswith('/api/auth/')
                or current_user.is_authenticated
            )
            if not skip_appkey:
                app_key = request.headers.get('X-App-Key')
                if not app_key:
                    return jsonify({'success': False, 'message': 'Missing App-Key header'}), 403
                
                try:
                    parts = app_key.split('.')
                    if len(parts) != 2:
                        raise ValueError("Invalid key format")
                        
                    client_timestamp = int(parts[0])
                    client_hash = parts[1]
                    
                    # Verify timestamp is within valid window (+/- 1 window = 300s)
                    import time
                    current_timestamp = int(time.time() / 300)
                    if abs(current_timestamp - client_timestamp) > 1:
                        return jsonify({'success': False, 'message': 'Expired App-Key'}), 403
                    
                    # Compute expected hash
                    secret = 'EdySync_Mvp_Secret_2026'
                    message = f"{secret}:{client_timestamp}"
                    expected_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()
                    
                    if client_hash != expected_hash:
                        return jsonify({'success': False, 'message': 'Invalid App-Key'}), 403
                        
                except Exception as e:
                    app.logger.warning(f"App-Key validation failed: {str(e)}")
                    return jsonify({'success': False, 'message': 'Invalid App-Key format'}), 403
    
    @app.after_request
    def after_request(response):
        # Calculate request duration
        start_time = getattr(g, 'request_start_time', None)
        duration = (datetime.utcnow() - start_time).total_seconds() if start_time else 0
        
        # Log response
        request_id = getattr(g, 'request_id', 'unknown')
        
        if response.status_code >= 400:
            app.logger.warning(
                f"Request completed with error",
                extra={
                    'request_id': request_id,
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
                    'request_id': request_id,
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
    # NOTE: Database must be the configured MySQL URI from environment.
    # Do NOT fall back to SQLite here. If the DB connection fails, we will log and raise the error.
    
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
        # Content Security Policy: allow common CDNs used by the frontend (Chart.js, Tailwind CDN,
        # Font providers and FontAwesome). Keep defaults restrictive otherwise.
        csp = {
            'default-src': ["'self'"],
            'script-src': [
                "'self'",
                "'unsafe-inline'",
                "https://cdn.tailwindcss.com",
                "https://cdnjs.cloudflare.com",
                "https://cdn.jsdelivr.net",
                "https://npmcdn.com",
                "https://ka-f.fontawesome.com"
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",
                "https://fonts.googleapis.com",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
                "https://ka-f.fontawesome.com"
            ],
            'font-src': [
                "'self'",
                "data:",
                "https://fonts.gstatic.com",
                "https://cdnjs.cloudflare.com",
                "https://ka-f.fontawesome.com"
            ],
            'img-src': [
                "'self'",
                'data:',
                'https://ui-avatars.com',
                'https://cdn.jsdelivr.net'
            ],
            # Allow connections to CDNs for module/script loading and any external APIs the frontend
            # may call (add additional origins here if needed).
            'connect-src': [
                "'self'",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
                "https://api.github.com"
            ],
            'frame-ancestors': ["'self'"]
        }

        # Only enable Talisman in non-development and non-debug environments.
        env_flag = os.environ.get('FLASK_ENV') or app.config.get('ENV')
        is_dev = (str(env_flag).lower() == 'development') or bool(app.config.get('DEBUG'))
        if not is_dev:
            # Use explicit FORCE_HTTPS config to avoid forcing HTTPS in local/dev environments.
            force_https_flag = app.config.get('FORCE_HTTPS', False)
            Talisman(
                app,
                content_security_policy=csp,
                content_security_policy_report_only=False,
                force_https=force_https_flag,
                strict_transport_security=force_https_flag,
                strict_transport_security_max_age=app.config.get('HSTS_SECONDS'),
                strict_transport_security_include_subdomains=app.config.get('HSTS_INCLUDE_SUBDOMAINS', False),
                content_types_nosniff=False,
                session_cookie_secure=force_https_flag
            )
            app.logger.info("Talisman security headers enabled")
        else:
            app.logger.info("Skipping Talisman initialization in development/debug mode")
    except Exception as e:
        app.logger.warning(f"Talisman configuration failed: {e}")
    
    # ========== INITIALIZE EXTENSIONS ==========
    db.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    # Expose csrf_token() to Jinja templates so templates can call {{ csrf_token() }}
    try:
        from flask_wtf.csrf import generate_csrf

        @app.context_processor
        def inject_csrf_token():
            return dict(csrf_token=generate_csrf)
    except Exception:
        # If flask-wtf isn't available, templates calling csrf_token() will fail gracefully elsewhere
        pass
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
        # Log DB host/user (masking password) and attempt to create/verify tables.
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        try:
            if uri:
                try:
                    from sqlalchemy.engine.url import make_url
                    url = make_url(uri)
                    host = url.host
                    user = url.username
                    app.logger.info(f"Attempting DB connection to host={host}, user={user}")
                except Exception:
                    app.logger.info(f"Attempting DB connection to configured URI")

            db.create_all()
            app.logger.info("Database tables created/verified")
        except Exception as e:
            # Surface exact DB connection/creation errors so developer can see remote host errors.
            app.logger.error("Database connection/creation failed", exc_info=True)
            raise
    
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
    
    # Register Yape/Financial Integration Blueprint
    from app.routes.yape_routes import yape_bp
    app.register_blueprint(yape_bp)

    # ========== IA OLLAMA MANAGEMENT ==========
    # Solo ejecutar en el proceso principal de Flask para evitar duplicidad al usar el reloader de Werkzeug
    try:
        from app.utils.manage_ollama import init_ia_check
        init_ia_check()
    except Exception as e:
        app.logger.warning(f"Ollama IA Management initialization failed: {e}")

    # Register Llama Copilot Routes (Enhanced)
    from app.routes.llama_routes import llama_bp
    app.register_blueprint(llama_bp)

    # Register Analytics & Monitoring Routes
    from app.routes.analytics_routes import analytics_bp
    app.register_blueprint(analytics_bp)

    # Register Async DAO API Blueprint (V2)
    from app.routes.async_api_routes import async_api_bp
    app.register_blueprint(async_api_bp)

    # ADD JINJA FILTERS
    import json
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value) if value else {}
        except Exception:
            return {}

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
