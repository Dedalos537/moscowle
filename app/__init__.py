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

from app.extensions import bcrypt, cache, cors, csrf, db, jwt, limiter, login_manager, mail, oauth, socketio
from config import Config

# Modo CGI (cPanel workaround): cada request es un proceso nuevo y paga el boot
# de create_app completo. Se desactivan los extras que solo sirven en procesos
# persistentes (flasgger, scheduler, celery, ollama, create_all) para que cada
# boot sea lo mas barato posible. La bandera la define app.cgi (MOSCOWLE_CGI=1);
# Passenger/dev no la ponen y conservan todo el comportamiento.
IS_CGI = os.environ.get('MOSCOWLE_CGI') == '1'

# Modo LEAN (servidor persistente local, server_local.py): el backend vive en
# gunicorn en 127.0.0.1:8765 y Apache lo alcanza via el relay app.cgi. Quiere el
# socketio + API al 100%, pero NO necesita los extras pesados del boot que antes
# vivian en Railway (flasgger, celery, scheduler APScheduler, ollama, sentry,
# create_all/migraciones). Se omiten igual que en CGI para que el boot sea
# ligero y no reviente la memoria del cPanel. La bandera la define
# server_local.py (MOSCOWLE_LEAN=1). La DB ya existe: no hace falta create_all.
IS_LEAN = IS_CGI or os.environ.get('MOSCOWLE_LEAN') == '1'


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
                app.logger.debug('User lookup failed in user_loader; DB may be unavailable')
                return None
    except Exception as e:

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


def register_jwt_session_blocklist(jwt_instance):
    """Habilita la validacion de sesiones JWT contra la tabla user_session.

    Si el jti del token no tiene una sesion activa en la DB (revocada o
    inexistente), el token se rechaza. Si la DB no esta disponible se deja
    pasar (fail-open) para no tumbar toda la app.
    """

    @jwt_instance.token_in_blocklist_loader
    def _token_in_blocklist(_jwt_header, jwt_payload):
        try:
            from app.models import UserSession

            return not UserSession.is_jti_valid(jwt_payload.get('jti'))
        except Exception:
            return False

    return jwt_instance


def setup_logging(app):
    """Logs chéveres con formato JSON y rotación"""

    log_dir = os.path.dirname(app.config['LOG_FILE'])
    os.makedirs(log_dir, exist_ok=True)

    app.logger.handlers.clear()

    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'], maxBytes=app.config['LOG_MAX_SIZE'], backupCount=app.config['LOG_BACKUP_COUNT']
    )

    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s %(exc_info)s %(request_id)s %(path)s %(method)s %(status_code)s %(duration_ms)s',
        timestamp=True,
    )
    file_handler.setFormatter(formatter)

    if app.debug:
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')
        console_handler.setFormatter(console_formatter)
        app.logger.addHandler(console_handler)

    from app.services.log_service import log_capture_handler

    capture_formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s]: %(message)s')
    log_capture_handler.setFormatter(capture_formatter)
    app.logger.addHandler(log_capture_handler)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))

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
    try:
        from app.middleware.metrics_middleware import init_metrics_middleware

        init_metrics_middleware(app)
        app.logger.info('Metrics middleware initialized')
    except Exception as e:
        app.logger.warning(f'Metrics middleware initialization failed: {e}')

    @app.before_request
    def before_request():
        g.request_id = str(uuid4())[:8]
        g.request_start_time = datetime.utcnow()

        try:
            from flask_jwt_extended import verify_jwt_in_request as _vji

            _vji(locations=['cookies', 'headers'], optional=True)
            from flask_jwt_extended import get_jwt_identity as _gji

            _uid = _gji()
            if _uid:
                from app.models import User as _U

                _user = _U.query.get(int(_uid))
                if _user:
                    g._login_user = _user
                    g.current_user = _user
        except Exception:
            pass

        has_cookie = 'moscowle_session=' in (request.headers.get('Cookie', ''))
        app.logger.debug(
            'Request started',
            extra={
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_id': current_user.id if current_user.is_authenticated else None,
                'auth': current_user.is_authenticated,
                'has_session_cookie': has_cookie,
                'scheme': request.scheme,
                'is_secure': request.is_secure,
                'origin': request.headers.get('Origin', ''),
            },
        )
        try:
            from app.utils.api_helpers import mark_request_api

            mark_request_api()
        except Exception:
            g.is_api = False

        if request.path.startswith('/api/') or request.path.startswith('/admin/api/'):
            _has_jwt = False
            try:
                from flask_jwt_extended import verify_jwt_in_request as _vji

                _vji(locations=['cookies', 'headers'], optional=True)
                from flask_jwt_extended import get_jwt_identity as _gji

                _has_jwt = _gji() is not None
            except Exception:
                pass

            skip_appkey = (
                request.method == 'OPTIONS'
                or 'webhook' in request.path
                or request.path.startswith('/api/auth/')
                or request.path in ('/api/login', '/api/logout')
                or request.path.startswith('/api/health')
                or request.path.startswith('/api/public/')
                or request.path.startswith('/admin/api/')
                or request.path.startswith('/api/admin/')
                or request.path.startswith('/api/server/')
                or request.path.startswith('/api/notifications')
                or current_user.is_authenticated
                or _has_jwt
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
                    client_hash = parts[1]

                    import time

                    current_timestamp = int(time.time() / 300)
                    if abs(current_timestamp - client_timestamp) > 1:
                        app.logger.warning('Expired App-Key', extra={'path': request.path, 'ip': request.remote_addr})
                        return jsonify({'success': False, 'message': 'Expired App-Key'}), 403

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
        start_time = getattr(g, 'request_start_time', None)
        duration = (datetime.utcnow() - start_time).total_seconds() if start_time else 0

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

        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response


def create_app(config_class=None):
    if config_class is None:
        env = os.environ.get('FLASK_ENV', 'development')
        is_railway = (
            os.environ.get('RAILWAY_ENVIRONMENT') is not None
            or os.environ.get('RAILWAY_SERVICE_NAME') is not None
            or os.environ.get('RAILWAY_REPLICA_ID') is not None
            or os.environ.get('RAILWAY_GIT_COMMIT_SHA') is not None
        )
        if env == 'production' or is_railway:
            from config import ProductionConfig

            config_class = ProductionConfig
        else:
            config_class = Config
    app = Flask(__name__)
    app.config.from_object(config_class)

    setup_logging(app)

    if not IS_LEAN:
        try:
            from flasgger import Swagger

            from app.swagger_config import swagger_config, swagger_template

            swagger = Swagger(app, config=swagger_config, template=swagger_template)
            app.logger.info('Swagger UI available at /api/docs/')
        except Exception as e:
            app.logger.warning(f'Swagger initialization failed: {e}')

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

    if app.config.get('USE_PROXYFIX', True):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
        app.logger.info('ProxyFix middleware enabled')

    try:
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
            'connect-src': [
                "'self'",
                'https://cdn.jsdelivr.net',
                'https://cdnjs.cloudflare.com',
                'https://api.github.com',
                'wss://api-centrojuanpabloii.online',
                'https://api-centrojuanpabloii.online',
                'wss://backend.centrojuanpabloii.com',
                'https://backend.centrojuanpabloii.com',
                'wss://moscowle.centrojuanpabloii.com',
                'https://moscowle.centrojuanpabloii.com',
            ],
            'frame-ancestors': ["'self'"],
        }

        env_flag = os.environ.get('FLASK_ENV') or app.config.get('ENV')
        is_dev = (str(env_flag).lower() == 'development') or bool(app.config.get('DEBUG'))
        if not is_dev:
            force_https_flag = app.config.get('FORCE_HTTPS', False)
            Talisman(
                app,
                content_security_policy=csp,
                content_security_policy_report_only=False,
                force_https=force_https_flag,
                strict_transport_security=force_https_flag,
                strict_transport_security_max_age=app.config.get('HSTS_SECONDS'),
                strict_transport_security_include_subdomains=app.config.get('HSTS_INCLUDE_SUBDOMAINS', False),
            )
            app.logger.info('Talisman security headers enabled')
        else:
            app.logger.info('Skipping Talisman initialization in development/debug mode')
    except Exception as e:
        app.logger.warning(f'Talisman configuration failed: {e}')

    db.init_app(app)
    from app.extensions import migrate

    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    register_jwt_session_blocklist(jwt)
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    from app.routes.api import api_bp

    csrf.exempt(api_bp)
    from app.routes.admin import admin_bp

    csrf.exempt(admin_bp)

    from app.routes.mcp_routes import mcp_bp

    csrf.exempt(mcp_bp)

    from app.routes.telegram_routes import telegram_bp

    csrf.exempt(telegram_bp)
    cors_origins = (
        app.config.get(
            'CORS_ORIGINS', 'https://moscowle.centrojuanpabloii.com https://centrojuanpabloii.com http://localhost:4200'
        )
        .replace(',', ' ')
        .split()
    )
    cors.init_app(
        app,
        resources={
            r'/api/*': {'origins': cors_origins},
            r'/admin/*': {'origins': cors_origins},
            r'/therapist/*': {'origins': cors_origins},
            r'/mcp/*': {'origins': cors_origins},
            r'/uploads/*': {'origins': cors_origins},
        },
        supports_credentials=True,
        allow_headers=['Content-Type', 'X-App-Key', 'Authorization', 'X-CSRFToken', 'X-Requested-With'],
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        max_age=3600,
    )

    def _allowed_origin():
        """Return the request Origin if it's in the allowed list, else first allowed."""
        origin = request.headers.get('Origin', '')
        if origin in cors_origins:
            return origin
        return cors_origins[0] if cors_origins else ''

    @app.before_request
    def _global_cors_preflight():
        """Handle ALL OPTIONS preflight requests with full CORS headers."""
        if request.method == 'OPTIONS':
            resp = app.make_default_options_response()
            resp.headers['Access-Control-Allow-Origin'] = _allowed_origin()
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = (
                'Content-Type, X-App-Key, Authorization, X-CSRFToken, X-Requested-With'
            )
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers['Access-Control-Max-Age'] = '3600'
            return resp

    @app.after_request
    def _global_cors_headers(response):
        """Add CORS headers to EVERY response (not just MCP)."""
        response.headers['Access-Control-Allow-Origin'] = _allowed_origin()
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    try:
        from flask_wtf.csrf import generate_csrf

        @app.context_processor
        def inject_csrf_token():
            return dict(csrf_token=generate_csrf)
    except Exception:
        app.logger.debug('flask-wtf not available, skipping csrf_token injection')
    cache.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='eventlet', manage_session=False)

    if not IS_LEAN:
        try:
            from app.celery_app import init_celery

            init_celery(app)
            app.logger.info('Celery initialized')
        except Exception as e:
            app.logger.warning(f'Celery initialization failed (non-fatal): {e}')

    from importlib import import_module

    try:
        import_module('app.socketio_events')
        app.logger.info('SocketIO event handlers registered')
    except Exception as e:
        app.logger.warning(f'SocketIO event registration failed: {e}')

    try:
        limiter.init_app(app)
        app.logger.info(f'Rate limiter initialized with storage: {app.config.get("RATELIMIT_STORAGE_URL")}')
    except Exception as e:
        app.logger.warning(f'Rate limiter initialization failed: {e}')

    register_auth_loader(app)
    register_error_handlers(app)
    register_request_handlers(app)

    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User': __import__('app.models', fromlist=['User']).User}

    with app.app_context():
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if uri:
            try:
                from sqlalchemy.engine.url import make_url

                url = make_url(uri)
                app.logger.info(f'DB host={url.host}, user={url.username}')
            except Exception:
                app.logger.info('DB configured URI')

        from app import models as _all_models

        if not IS_LEAN:
            try:
                db.create_all()
                app.logger.info('Database tables created/verified')
            except Exception as e:
                app.logger.warning(f'Database tables creation failed (non-fatal): {e}')

            try:
                from sqlalchemy import text

                result = db.session.execute(
                    text(
                        'SELECT COUNT(*) FROM information_schema.columns '
                        "WHERE table_name = 'incidente' AND column_name = 'impacto'"
                    )
                )
                if result.scalar() == 0:
                    app.logger.info('Adding ITIL columns to incidente table...')
                    for col_def in [
                        'ALTER TABLE incidente ADD COLUMN impacto INTEGER NOT NULL DEFAULT 2',
                        'ALTER TABLE incidente ADD COLUMN urgencia INTEGER NOT NULL DEFAULT 2',
                        'ALTER TABLE incidente ADD COLUMN post_mortem TEXT NULL',
                        'ALTER TABLE incidente ADD COLUMN causa_raiz TEXT NULL',
                        'ALTER TABLE incidente ADD COLUMN lecciones_aprendidas TEXT NULL',
                    ]:
                        db.session.execute(text(col_def))
                    db.session.commit()
                    app.logger.info('ITIL columns added successfully')
                else:
                    app.logger.info('ITIL columns already exist')
            except Exception as e:
                app.logger.warning(f'ITIL column migration (non-fatal): {e}')
                db.session.rollback()

            try:
                from sqlalchemy import text

                result = db.session.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'user' AND column_name = 'sex'"
                    )
                )
                if result.scalar() == 0:
                    app.logger.info('Adding patient detail columns to user table...')
                    for col_def in [
                        'ALTER TABLE user ADD COLUMN sex VARCHAR(20) NULL',
                        'ALTER TABLE user ADD COLUMN preliminary_diagnosis TEXT NULL',
                        'ALTER TABLE user ADD COLUMN guardian_type VARCHAR(50) NULL',
                    ]:
                        db.session.execute(text(col_def))
                    db.session.commit()
                    app.logger.info('Patient detail columns added successfully')
                else:
                    app.logger.info('Patient detail columns already exist')
            except Exception as e:
                app.logger.warning(f'Patient detail column migration (non-fatal): {e}')
                db.session.rollback()

        db.session.remove()

    _blueprints = [
        ('auth', 'app.routes.auth', 'auth_bp'),
        ('main', 'app.routes.main', 'main_bp'),
        ('therapist', 'app.routes.therapist_routes', 'therapist_bp'),
        ('patient', 'app.routes.patient_routes', 'patient_bp'),
        ('api', 'app.routes.api', 'api_bp'),
        ('uploads', 'app.routes.uploads', 'uploads_bp'),
        ('admin', 'app.routes.admin', 'admin_bp'),
        ('yape', 'app.routes.yape_routes', 'yape_bp'),
        ('chat', 'app.routes.chat_routes', 'chat_bp'),
        ('analytics', 'app.routes.analytics_routes', 'analytics_bp'),
        ('health', 'app.routes.health_routes', 'health_bp'),
        ('public', 'app.routes.public_routes', 'public_bp'),
        ('spa', 'app.routes.public_routes', 'spa_bp'),
        ('async_api', 'app.routes.async_api_routes', 'async_api_bp'),
        ('metrics', 'app.routes.metrics_routes', 'metrics_bp'),
        ('mcp', 'app.routes.mcp_routes', 'mcp_bp'),
        ('admin_ai', 'app.routes.admin_ai', 'bp'),
        ('telegram', 'app.routes.telegram_routes', 'telegram_bp'),
    ]
    for name, module_path, bp_name in _blueprints:
        try:
            bp = __import__(module_path, fromlist=[bp_name]).__dict__[bp_name]
            app.register_blueprint(bp)
            app.logger.debug('Blueprint registered: %s', name)
        except Exception as e:
            import traceback

            app.logger.error('Blueprint %s FAILED to load: %s\n%s', name, e, traceback.format_exc())

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

    if not IS_LEAN:
        try:
            from app.utils.manage_ollama import init_ia_check

            init_ia_check()
        except Exception as e:
            app.logger.warning('Ollama IA Management initialization failed: %s', e)

    import json

    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value) if value else {}
        except Exception:
            return {}

    if not IS_LEAN:
        try:
            from app.tasks import init_scheduler

            init_scheduler(app)
            app.logger.info('Scheduler initialized')
        except Exception as e:
            app.logger.error('Scheduler initialization failed: %s', e)

    app.logger.info('Application initialization complete')
    return app


# ──────────────────────────────────────────────────────────────────────
# create_app_lite: Lightweight Flask factory for shared-hosting CGI
# Only initializes: db, jwt, bcrypt, login_manager, csrf, cors, mail,
# oauth, cache, socketio, limiter. Registers 6 essential blueprints.
# Skips: sentry, flasgger, celery, scheduler, ollama, metrics,
# proxyfix, talisman, 9 non-essential blueprints.
# Boot target: <2s on shared hosting (vs 5-14s for full create_app).
# ──────────────────────────────────────────────────────────────────────


def create_app_lite():
    env = os.environ.get('FLASK_ENV', os.environ.get('FLASK_DEBUG', 'production'))
    if env in ('production', 'prod'):
        try:
            from config import ProductionConfig

            config_class = ProductionConfig
        except Exception:
            from config import Config

            config_class = Config
    else:
        from config import Config

        config_class = Config

    app = Flask(__name__)
    app.config.from_object(config_class)

    setup_logging(app)

    from flask_jwt_extended import JWTManager

    jwt = JWTManager(app)

    from app.extensions import bcrypt, cache, cors, csrf, db, limiter, login_manager, mail, oauth, socketio

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    register_jwt_session_blocklist(jwt)
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.routes.admin import admin_bp
    from app.routes.admin_ai import bp as admin_ai_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.health_routes import health_bp
    from app.routes.main import main_bp
    from app.routes.mcp_routes import mcp_bp
    from app.routes.public_routes import public_bp
    from app.routes.telegram_routes import telegram_bp
    from app.routes.uploads import uploads_bp
    from app.routes.yape_routes import yape_bp

    csrf.exempt(api_bp)
    csrf.exempt(mcp_bp)
    csrf.exempt(admin_bp)
    csrf.exempt(telegram_bp)
    csrf.exempt(uploads_bp)

    for bp in [
        auth_bp,
        api_bp,
        public_bp,
        mcp_bp,
        health_bp,
        chat_bp,
        main_bp,
        admin_bp,
        telegram_bp,
        yape_bp,
        admin_ai_bp,
        uploads_bp,
    ]:
        try:
            app.register_blueprint(bp)
        except Exception as e:
            app.logger.error('Blueprint %s failed: %s', bp.name, e)

    cors_origins = (
        app.config.get(
            'CORS_ORIGINS', 'https://moscowle.centrojuanpabloii.com https://centrojuanpabloii.com http://localhost:4200'
        )
        .replace(',', ' ')
        .split()
    )
    cors.init_app(
        app,
        resources={
            r'/api/*': {'origins': cors_origins},
            r'/admin/*': {'origins': cors_origins},
            r'/mcp/*': {'origins': cors_origins},
            r'/uploads/*': {'origins': cors_origins},
            r'/api/telegram/*': {'origins': cors_origins},
        },
        supports_credentials=True,
        allow_headers=['Content-Type', 'X-App-Key', 'Authorization', 'X-CSRFToken', 'X-Requested-With'],
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        max_age=3600,
    )

    def _allowed_origin():
        origin = request.headers.get('Origin', '')
        if origin in cors_origins:
            return origin
        return cors_origins[0] if cors_origins else ''

    @app.before_request
    def _global_cors_preflight():
        if request.method == 'OPTIONS':
            resp = app.make_default_options_response()
            resp.headers['Access-Control-Allow-Origin'] = _allowed_origin()
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = (
                'Content-Type, X-App-Key, Authorization, X-CSRFToken, X-Requested-With'
            )
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers['Access-Control-Max-Age'] = '3600'
            return resp

    @app.before_request
    def _jwt_bootstrap():
        """Authenticate current_user from JWT cookies/headers so @login_required
        and admin auth guards work in the lite app factory."""
        g.request_id = str(uuid4())[:8]
        g.request_start_time = datetime.utcnow()
        try:
            from flask_jwt_extended import get_jwt_identity as _gji
            from flask_jwt_extended import verify_jwt_in_request as _vji

            _vji(locations=['cookies', 'headers'], optional=True)
            _uid = _gji()
            if _uid:
                from app.models import User as _U

                _user = _U.query.get(int(_uid))
                if _user:
                    g._login_user = _user
                    g.current_user = _user
        except Exception:
            pass

    @app.after_request
    def _global_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = _allowed_origin()
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    try:
        from flask_wtf.csrf import generate_csrf

        @app.context_processor
        def inject_csrf_token():
            return dict(csrf_token=generate_csrf)
    except Exception:
        pass

    cache.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='eventlet', manage_session=False)

    register_auth_loader(app)
    register_error_handlers(app)

    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Database tables created/verified (lite)')
        except Exception as e:
            app.logger.warning(f'db.create_all failed (non-fatal): {e}')
        try:
            from app.utils.ensure_columns import ensure_columns

            ensure_columns()
        except Exception as e:
            app.logger.warning(f'ensure_columns failed (non-fatal): {e}')

    app.logger.info('Application initialized (lite mode)')
    return app
