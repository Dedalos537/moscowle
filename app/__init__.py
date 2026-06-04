import hashlib
import logging
import os
import traceback
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from uuid import uuid4

import click
from flask import Flask, g, has_request_context, jsonify, render_template, request
from flask_login import current_user
from flask_talisman import Talisman
from pythonjsonlogger import jsonlogger
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import bcrypt, cache, cors, csrf, db, limiter, login_manager, mail, oauth, socketio
from config import Config


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
                # Por si la BD se fue al muere, devolvemos None no más
                app.logger.debug('User lookup failed in user_loader; DB may be unavailable')
                return None
    except Exception as e:
        # Registrar user_loader pa que flask-login no llore
        def _dummy_loader(user_id):
            return None

        login_manager.user_loader(_dummy_loader)
        try:
            app.logger.warning(f'register_auth_loader failed to import models: {e}')
        except Exception:
            pass

    @login_manager.unauthorized_handler
    def unauthorized():
        path = request.path or ''
        if '/api/' in path or getattr(g, 'is_api', False) or request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'message': 'Unauthorized - Please log in'}), 401
        from flask import redirect, url_for

        return redirect(url_for('auth.login', next=request.url))


def setup_logging(app):
    """Logs chéveres con formato JSON y rotación"""

    # Create logs directory
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    os.makedirs(log_dir, exist_ok=True)

    # Remove default handlers
    app.logger.handlers.clear()

    # File handler with rotation
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'], maxBytes=app.config['LOG_MAX_SIZE'], backupCount=app.config['LOG_BACKUP_COUNT']
    )

    # JSON formatter for production logging (ELK/Splunk compatible)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(exc_info)s %(request_id)s %(path)s %(method)s %(status_code)s %(duration_ms)s',
        timestamp=True,
    )
    file_handler.setFormatter(formatter)

    # Console handler for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')
        console_handler.setFormatter(console_formatter)
        app.logger.addHandler(console_handler)

    # In-memory capture handler for admin log viewer
    from app.services.log_service import log_capture_handler

    capture_formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')
    log_capture_handler.setFormatter(capture_formatter)
    app.logger.addHandler(log_capture_handler)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

    # Log startup
    app.logger.info(
        'Application initialized',
        extra={'env': app.config['ENV'], 'debug': app.debug, 'timestamp': datetime.utcnow().isoformat()},
    )


def _is_api_request():
    """Check if the current request targets an API endpoint."""
    path = request.path or ''
    if '/api/' in path:
        return True
    if getattr(g, 'is_api', False):
        return True
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    if request.is_json:
        return True
    return False


def register_error_handlers(app):
    """Manejadores de errores globales"""
    # CSRF errors should return JSON for API calls
    try:
        from flask_wtf.csrf import CSRFError

        from app.utils.api_helpers import api_response

        @app.errorhandler(CSRFError)
        def handle_csrf_error(e):
            app.logger.warning(
                'CSRF validation failed',
                exc_info=True,
                extra={'path': request.path, 'method': request.method, 'ip': request.remote_addr},
            )
            if _is_api_request():
                return api_response(False, error={'message': str(e)}, status=400)
            return render_template('errors/csrf.html', reason=str(e)), 400
    except Exception:
        app.logger.debug('flask_wtf not available, CSRF error handler skipped')

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(
            f'400 Bad Request: {error}', exc_info=True, extra={'path': request.path, 'method': request.method}
        )
        if _is_api_request():
            return jsonify({'error': 'Bad request', 'message': str(error)}), 400
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(
            f'403 Forbidden: {error}',
            exc_info=True,
            extra={
                'path': request.path,
                'method': request.method,
                'ip': request.remote_addr,
                'user_agent': request.user_agent.string,
            },
        )
        if _is_api_request():
            return jsonify({'error': 'Access denied'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        if _is_api_request():
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(
            f'429 Rate Limited: {e}',
            extra={
                'path': request.path,
                'ip': request.remote_addr,
                'limit': str(e.description) if hasattr(e, 'description') else None,
            },
        )
        if _is_api_request():
            return jsonify({'error': 'Rate limit exceeded', 'description': str(e.description)}), 429
        return render_template('errors/429.html', error=e), 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        request_id = g.get('request_id', 'unknown')
        app.logger.error('500 Internal Server Error', exc_info=True, extra={'request_id': request_id})
        if _is_api_request():
            return jsonify({'error': 'Internal server error', 'request_id': request_id}), 500
        return render_template('errors/500.html', error=error), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        db.session.rollback()
        request_id = g.get('request_id', 'unknown')
        app.logger.error(
            f'Unhandled exception: {type(error).__name__}',
            exc_info=True,
            extra={'request_id': request_id, 'error_type': type(error).__name__},
        )
        if _is_api_request():
            return jsonify({'error': 'Server error', 'request_id': request_id}), 500
        return render_template('errors/500.html', error=error), 500


def register_request_handlers(app):
    """Handlers de request/response lifecycle"""

    @app.before_request
    def before_request():
        # Generate request ID for tracking
        g.request_id = str(uuid4())[:8]
        g.request_start_time = datetime.utcnow()

        # Log incoming request
        app.logger.debug(
            'Request started',
            extra={
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_id': current_user.id if current_user.is_authenticated else None,
            },
        )
        # Mark whether this request is an API call
        try:
            from app.utils.api_helpers import mark_request_api

            mark_request_api()
        except Exception:
            g.is_api = False

        # Validar App-Key pa que solo el frontend edysync pueda acceder
        if request.path.startswith('/api/') or request.path.startswith('/admin/api/'):
            # Saltar validacion pa: webhooks, auth, login, health, OPTIONS, sesiones activas
            skip_appkey = (
                request.method == 'OPTIONS'
                or 'webhook' in request.path
                or request.path.startswith('/api/auth/')
                or request.path in ('/api/login', '/api/logout')
                or request.path.startswith('/api/health')
                or request.path.startswith('/api/public/')
                or current_user.is_authenticated
            )
            if not skip_appkey:
                app_key = request.headers.get('X-App-Key')
                if not app_key:
                    app.logger.warning(
                        'Missing App-Key header', extra={'path': request.path, 'ip': request.remote_addr}
                    )
                    return jsonify({'success': False, 'message': 'Missing App-Key header'}), 403

                try:
                    parts = app_key.split('.')
                    if len(parts) != 2:
                        raise ValueError('Invalid key format')

                    client_timestamp = int(parts[0])

                    # Verify timestamp is within valid window (+/- 1 window = 300s)
                    import time

                    current_timestamp = int(time.time() / 300)
                    if abs(current_timestamp - client_timestamp) > 1:
                        app.logger.warning('Expired App-Key', extra={'path': request.path, 'ip': request.remote_addr})
                        return jsonify({'success': False, 'message': 'Expired App-Key'}), 403

                    # Compute expected hash
                    secret = app.config.get('APP_SECRET_KEY', 'dev-app-key-change-in-production')
                    message = f'{secret}:{client_timestamp}'
                    expected_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()

                    if client_hash != expected_hash:
                        app.logger.warning(
                            'Invalid App-Key hash', extra={'path': request.path, 'ip': request.remote_addr}
                        )
                        return jsonify({'success': False, 'message': 'Invalid App-Key'}), 403

                except Exception as e:
                    app.logger.warning(
                        f'App-Key validation failed: {e}',
                        exc_info=True,
                        extra={'path': request.path, 'ip': request.remote_addr},
                    )
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
                'Request completed with error',
                extra={
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'duration_ms': duration * 1000,
                    'method': request.method,
                    'path': request.path,
                },
            )
        else:
            app.logger.debug(
                'Request completed',
                extra={'request_id': request_id, 'status_code': response.status_code, 'duration_ms': duration * 1000},
            )

        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response


def create_app(config_class=None):
    if config_class is None:
        env = os.environ.get('FLASK_ENV', 'development')
        is_railway = (
            os.environ.get('RAILWAY_ENVIRONMENT') is not None or os.environ.get('RAILWAY_SERVICE_NAME') is not None
        )
        if env == 'production' or is_railway:
            from config import ProductionConfig

            config_class = ProductionConfig
        else:
            config_class = Config
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Ojo: la BD es MySQL desde env. Nada de SQLite.

    # ========== LOGGING - SETUP FIRST ==========
    setup_logging(app)

    # ========== SWAGGER / OPENAPI ==========
    try:
        from flasgger import Swagger

        from app.swagger_config import swagger_config, swagger_template

        swagger = Swagger(app, config=swagger_config, template=swagger_template)
        app.logger.info('Swagger UI available at /api/docs/')
    except Exception as e:
        app.logger.warning(f'Swagger initialization failed: {e}')

    # ========== SENTRY ERROR MONITORING ==========
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration

            send_pii = os.environ.get('SENTRY_SEND_PII', 'False') == 'True'
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
                environment=app.config.get('ENV', 'production'),
                send_default_pii=send_pii,
            )
            app.logger.info('Sentry error monitoring initialized')
        except Exception as e:
            app.logger.warning(f'Sentry initialization failed: {e}')
    else:
        app.logger.info('SENTRY_DSN not set — skipping Sentry setup')

    # ========== SECURITY MIDDLEWARE ==========
    # ProxyFix for reverse proxies (cPanel, Nginx)
    if app.config.get('USE_PROXYFIX', True):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
        app.logger.info('ProxyFix middleware enabled')

    # Talisman for security headers and HSTS
    try:
        # Content Security Policy: allow common CDNs used by the frontend (Chart.js, Tailwind CDN,
        # Font providers and FontAwesome). Keep defaults restrictive otherwise.
        csp = {
            'default-src': ["'self'"],
            'script-src': [
                "'self'",
                "'unsafe-inline'",
                'https://cdn.tailwindcss.com',
                'https://cdnjs.cloudflare.com',
                'https://cdn.jsdelivr.net',
                'https://npmcdn.com',
                'https://ka-f.fontawesome.com',
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",
                'https://fonts.googleapis.com',
                'https://cdn.jsdelivr.net',
                'https://cdnjs.cloudflare.com',
                'https://ka-f.fontawesome.com',
            ],
            'font-src': [
                "'self'",
                'data:',
                'https://fonts.gstatic.com',
                'https://cdnjs.cloudflare.com',
                'https://ka-f.fontawesome.com',
            ],
            'img-src': ["'self'", 'data:', 'https://ui-avatars.com', 'https://cdn.jsdelivr.net'],
            # CDNs pa que el frontend cargue bien
            'connect-src': [
                "'self'",
                'https://cdn.jsdelivr.net',
                'https://cdnjs.cloudflare.com',
                'https://api.github.com',
                'wss://moscowle-backend-production.up.railway.app',
                'https://moscowle-backend-production.up.railway.app',
            ],
            'frame-ancestors': ["'self'"],
        }

        # Solo activar Talisman en produccion, no en dev
        env_flag = os.environ.get('FLASK_ENV') or app.config.get('ENV')
        is_dev = (str(env_flag).lower() == 'development') or bool(app.config.get('DEBUG'))
        if not is_dev:
            # Forzar HTTPS solo si la config lo pide, no en local
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
                session_cookie_secure=force_https_flag,
            )
            app.logger.info('Talisman security headers enabled')
        else:
            app.logger.info('Skipping Talisman initialization in development/debug mode')
    except Exception as e:
        app.logger.warning(f'Talisman configuration failed: {e}')

    # ========== INITIALIZE EXTENSIONS ==========
    db.init_app(app)
    from app.extensions import migrate

    migrate.init_app(app, db)
    bcrypt.init_app(app)
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    cors_origins = (
        app.config.get(
            'CORS_ORIGINS', 'https://moscowle.centrojuanpabloii.com https://centrojuanpabloii.com http://localhost:4200'
        )
        .replace(',', ' ')
        .split()
    )
    cors.init_app(
        app,
        resources={r'/api/*': {'origins': cors_origins}, r'/admin/*': {'origins': cors_origins}},
        supports_credentials=True,
        allow_headers=['Content-Type', 'X-App-Key', 'Authorization', 'X-CSRFToken'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        max_age=3600,
    )
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
    socketio.init_app(app, cors_allowed_origins='*')

    # ========== IMPORT SOCKETIO EVENTS ==========
    from importlib import import_module

    try:
        import_module('app.socketio_events')
        app.logger.info('SocketIO event handlers registered')
    except Exception as e:
        app.logger.warning(f'SocketIO event registration failed: {e}')

    # ========== RATE LIMITING ==========
    try:
        limiter.init_app(app)
        app.logger.info(f'Rate limiter initialized with storage: {app.config.get("RATELIMIT_STORAGE_URL")}')
    except Exception as e:
        app.logger.warning(f'Rate limiter initialization failed: {e}')

    # ========== ERROR HANDLERS ==========
    register_auth_loader(app)
    register_error_handlers(app)
    register_request_handlers(app)

    # ========== DATABASE ==========
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User': __import__('app.models', fromlist=['User']).User}

    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        try:
            if uri:
                try:
                    from sqlalchemy.engine.url import make_url

                    url = make_url(uri)
                    app.logger.info(f'Attempting DB connection to host={url.host}, user={url.username}')
                except Exception:
                    app.logger.info('Attempting DB connection to configured URI')

            from app import models as _all_models

            db.create_all()
            app.logger.info('Database tables created/verified')

            try:
                from flask_migrate import upgrade as migrate_upgrade

                migrate_upgrade()
                app.logger.info('Pending migrations applied (if any)')
            except Exception:
                app.logger.debug('No migrations to apply or migration system not yet initialized')
        except Exception:
            app.logger.error('Database connection/creation failed', exc_info=True)
            raise
        finally:
            db.session.remove()

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

    from app.routes.api import api_bp

    app.register_blueprint(api_bp)

    from app.routes.uploads import uploads_bp

    app.register_blueprint(uploads_bp)

    from app.routes.admin import admin_bp

    app.register_blueprint(admin_bp)

    # Register Yape/Financial Integration Blueprint
    from app.routes.yape_routes import yape_bp

    app.register_blueprint(yape_bp)

    # Register Chat Blueprint (Telegram-style messaging)
    from app.routes.chat_routes import chat_bp

    app.register_blueprint(chat_bp)

    # ========== CLI COMMANDS ==========
    @app.cli.command('migrate-messages')
    def migrate_messages_command():
        """Backfill Chat records for existing messages without a chat_id"""
        from app.models import Chat, ChatParticipant, Message, User

        pairs = (
            db.session.query(Message.sender_id, Message.receiver_id).filter(Message.chat_id.is_(None)).distinct().all()
        )
        count = 0
        for sender_id, receiver_id in pairs:
            existing = (
                Chat.query.join(ChatParticipant, ChatParticipant.chat_id == Chat.id)
                .filter(ChatParticipant.user_id == sender_id)
                .filter(
                    Chat.id.in_(
                        db.session.query(ChatParticipant.chat_id).filter(ChatParticipant.user_id == receiver_id)
                    )
                )
                .first()
            )
            if existing:
                chat_id = existing.id
            else:
                chat = Chat(created_by_id=sender_id)
                db.session.add(chat)
                db.session.flush()
                for uid in [sender_id, receiver_id]:
                    db.session.add(ChatParticipant(chat_id=chat.id, user_id=uid))
                chat_id = chat.id
            updated = Message.query.filter(
                Message.sender_id == sender_id, Message.receiver_id == receiver_id, Message.chat_id.is_(None)
            ).update({'chat_id': chat_id}, synchronize_session=False)
            count += updated
            for op_id in [sender_id, receiver_id]:
                ChatParticipant.query.filter_by(chat_id=chat_id, user_id=op_id).update(
                    {'last_read_at': db.func.now()}, synchronize_session=False
                )
        db.session.commit()
        click.echo(f'Migrated {count} messages into {len(pairs)} chat(s).')

    # ========== IA OLLAMA MANAGEMENT ==========
    # Solo ejecutar en el proceso principal de Flask para evitar duplicidad al usar el reloader de Werkzeug
    try:
        from app.utils.manage_ollama import init_ia_check

        init_ia_check()
    except Exception as e:
        app.logger.warning(f'Ollama IA Management initialization failed: {e}')

    # Register Llama Copilot Routes (Enhanced)
    from app.routes.llama_routes import llama_bp

    app.register_blueprint(llama_bp)

    # Register Analytics & Monitoring Routes
    from app.routes.analytics_routes import analytics_bp

    app.register_blueprint(analytics_bp)

    # Register Health Check Route
    from app.routes.health_routes import health_bp

    app.register_blueprint(health_bp)

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

    # ========== BACKGROUND TASKS ==========
    try:
        from app.tasks import init_scheduler

        init_scheduler(app)
        app.logger.info('Scheduler initialized')
    except Exception as e:
        app.logger.error(f'Scheduler initialization failed: {e}')

    app.logger.info('Application initialization complete')
    return app
