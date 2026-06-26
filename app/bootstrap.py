from flask import Flask, g, jsonify, redirect, request, url_for
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import bcrypt, cache, cors, csrf, db, jwt, limiter, login_manager, mail, oauth, socketio


def register_auth_loader(app: Flask) -> None:
    try:
        from app.extensions import jwt as _jwt
        from app.models import User

        @_jwt.user_identity_loader
        def user_identity_lookup(user):
            return str(user.id) if hasattr(user, 'id') else str(user)

        @_jwt.user_lookup_loader
        def user_lookup_callback(_jwt_header, jwt_data):
            identity = jwt_data.get('sub')
            if identity is None:
                return None
            return User.query.get(int(identity))

        @_jwt.expired_token_loader
        def expired_token_callback(_jwt_header, _jwt_data):
            if '/api/' in request.path or getattr(g, 'is_api', False) or request.accept_mimetypes.accept_json:
                return jsonify({'success': False, 'message': 'Token expirado, inicia sesión de nuevo'}), 401
            return redirect(url_for('auth.login'))

        @_jwt.invalid_token_loader
        def invalid_token_callback(_error):
            return jsonify({'success': False, 'message': 'Token inválido'}), 401

        @_jwt.unauthorized_loader
        def missing_token_callback(_error):
            path = request.path or ''
            if '/api/' in path or getattr(g, 'is_api', False) or request.accept_mimetypes.accept_json:
                return jsonify({'success': False, 'message': 'Authorization required'}), 401
            return redirect(url_for('auth.login', next=request.url))

        @_jwt.revoked_token_loader
        def revoked_token_callback(_jwt_header, _jwt_data):
            return jsonify({'success': False, 'message': 'Token revocado'}), 401
    except Exception as e:
        app.logger.warning(f'register_auth_loader failed to register JWT handlers: {e}')


def register_error_handlers(app: Flask) -> None:
    from app.middleware.request_handlers import _is_api_request

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
            return app.jinja_env.get_template('errors/csrf.html').render(reason=str(e)), 400
    except Exception:
        app.logger.debug('flask_wtf not available, CSRF error handler skipped')

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(
            f'400 Bad Request: {error}', exc_info=True, extra={'path': request.path, 'method': request.method}
        )
        if _is_api_request():
            return jsonify({'error': 'Bad request', 'message': str(error)}), 400
        return app.jinja_env.get_template('errors/400.html').render(error=error), 400

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
        return app.jinja_env.get_template('errors/403.html').render(), 403

    @app.errorhandler(404)
    def not_found(error):
        if _is_api_request():
            return jsonify({'error': 'Not found'}), 404
        return app.jinja_env.get_template('errors/404.html').render(), 404

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
        return app.jinja_env.get_template('errors/429.html').render(error=e), 429

    @app.errorhandler(500)
    def internal_error(error):
        from app.extensions import db

        db.session.rollback()
        request_id = g.get('request_id', 'unknown')
        app.logger.error('500 Internal Server Error', exc_info=True, extra={'request_id': request_id})
        if _is_api_request():
            return jsonify({'error': 'Internal server error', 'request_id': request_id}), 500
        return app.jinja_env.get_template('errors/500.html').render(error=error), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        from app.extensions import db

        db.session.rollback()
        request_id = g.get('request_id', 'unknown')
        app.logger.error(
            f'Unhandled exception: {type(error).__name__}',
            exc_info=True,
            extra={'request_id': request_id, 'error_type': type(error).__name__},
        )
        if _is_api_request():
            return jsonify({'error': 'Server error', 'request_id': request_id}), 500
        return app.jinja_env.get_template('errors/500.html').render(error=error), 500


def init_swagger(app: Flask) -> None:
    try:
        from flasgger import Swagger

        from app.swagger_config import swagger_config, swagger_template

        Swagger(app, config=swagger_config, template=swagger_template)
        app.logger.info('Swagger UI available at /api/docs/')
    except Exception as e:
        app.logger.warning(f'Swagger initialization failed: {e}')


def init_sentry(app: Flask) -> None:
    import os

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


def init_security(app: Flask) -> None:
    if app.config.get('USE_PROXYFIX', True):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
        app.logger.info('ProxyFix middleware enabled')

    app_secret = app.config.get('APP_SECRET_KEY', '')
    default_keys = {'dev-app-key-change-in-production', 'change-in-production', 'EdySync_Mvp_Secret_2026'}
    if app_secret in default_keys:
        app.logger.warning(
            'APP_SECRET_KEY is set to an insecure default! Set APP_SECRET_KEY env var in production.',
            extra={'env': app.config.get('ENV', 'unknown')},
        )

    try:
        csp = {
            'default-src': ["'self'"],
            'base-uri': ["'self'"],
            'object-src': ["'none'"],
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
                'https://cdnjs.cloudflare.com',
                'https://api.github.com',
                'wss://moscowle-backend-production.up.railway.app',
                'https://moscowle-backend-production.up.railway.app',
            ],
            'frame-ancestors': ["'none'"],
        }

        import os

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


def init_extensions(app: Flask) -> None:
    db.init_app(app)
    from app.extensions import migrate

    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.routes.api import api_bp

    csrf.exempt(api_bp)

    cors_origins = (
        app.config.get(
            'CORS_ORIGINS',
            'https://moscowle.centrojuanpabloii.com https://centrojuanpabloii.com https://moscowle.app http://localhost:4200 http://localhost:5173',
        )
        .replace(',', ' ')
        .split()
    )
    cors.init_app(
        app,
        resources={
            r'/api/*': {'origins': cors_origins},
            r'/admin/*': {'origins': cors_origins},
            r'/llama/*': {'origins': cors_origins},
        },
        supports_credentials=True,
        allow_headers=['Content-Type', 'X-App-Key', 'Authorization', 'X-CSRFToken'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        max_age=3600,
    )

    try:
        from flask_wtf.csrf import generate_csrf

        @app.context_processor
        def inject_csrf_token():
            return dict(csrf_token=generate_csrf)
    except Exception:
        app.logger.debug('flask-wtf not available, skipping csrf_token injection')

    try:
        from app.services.feature_flags import inject_flags

        @app.context_processor
        def inject_feature_flags():
            return inject_flags()
    except Exception:
        app.logger.debug('feature_flags not available, skipping')

    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'simple'),
    }
    if app.config.get('CACHE_REDIS_URL'):
        cache_config['CACHE_REDIS_URL'] = app.config['CACHE_REDIS_URL']
    cache.init_app(app, cache_config)
    _cors = app.config.get('CORS_ORIGINS', 'https://moscowle.centrojuanpabloii.com')
    socketio.init_app(app, cors_allowed_origins=_cors.split())

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

    try:
        from app.db.routing import init_db_routing

        if app.config.get('REPLICA_DATABASE_URL'):
            init_db_routing(app)
    except Exception as e:
        app.logger.warning(f'DB routing initialization failed: {e}')

    try:
        from app.services.crisis_monitor import crisis_monitor

        crisis_monitor.init_app(app)
    except Exception as e:
        app.logger.warning(f'CrisisMonitor initialization failed: {e}')

    try:
        from app.auth.oauth import init_oauth

        if app.config.get('GOOGLE_CLIENT_ID'):
            init_oauth(app)
    except Exception as e:
        app.logger.warning(f'OAuth initialization failed: {e}')


def register_blueprints(app: Flask) -> None:
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
        ('llama', 'app.routes.llama_routes', 'llama_bp'),
        ('analytics', 'app.routes.analytics_routes', 'analytics_bp'),
        ('health', 'app.routes.health_routes', 'health_bp'),
        ('public', 'app.routes.public_routes', 'public_bp'),
        ('spa', 'app.routes.public_routes', 'spa_bp'),
        ('async_api', 'app.routes.async_api_routes', 'async_api_bp'),
        ('metrics', 'app.routes.metrics_routes', 'metrics_bp'),
        ('mfa', 'app.routes.mfa', 'mfa_bp'),
        ('oauth', 'app.auth.oauth', 'oauth_bp'),
        ('api_service_requests', 'app.api.service_requests', 'api_sr'),
        ('incidents', 'app.routes.incident_routes', 'incident_bp'),
    ]
    for name, module_path, bp_name in _blueprints:
        try:
            bp = __import__(module_path, fromlist=[bp_name]).__dict__[bp_name]
            app.register_blueprint(bp)
            app.logger.debug('Blueprint registered: %s', name)
        except Exception as e:
            app.logger.warning('Blueprint %s failed to load: %s', name, e)


def init_template_filters(app: Flask) -> None:
    import json

    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value) if value else {}
        except Exception:
            return {}


def init_scheduler_and_ollama(app: Flask) -> None:
    try:
        from app.utils.manage_ollama import init_ia_check

        init_ia_check()
    except Exception as e:
        app.logger.warning('Ollama IA Management initialization failed: %s', e)

    try:
        from app.tasks import init_scheduler

        init_scheduler(app)
        app.logger.info('Scheduler initialized')
    except Exception as e:
        app.logger.error('Scheduler initialization failed: %s', e)
