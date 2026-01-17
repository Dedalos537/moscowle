from flask import Flask, request
from config import Config
from app.extensions import db, bcrypt, mail, oauth, login_manager, limiter
from flask_talisman import Talisman
from app.models import User, CSPReport
from flask_login import current_user
from app.services.ai_service import train_model
# Optional Sentry integration for error/report aggregation
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
except Exception:
    sentry_sdk = None
from flask_wtf import CSRFProtect
import os
from email_validator import validate_email, EmailNotValidError
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from pythonjsonlogger import jsonlogger
from flask import g, has_request_context
from uuid import uuid4
from collections import defaultdict
import threading
try:
    import redis as redis_lib
except Exception:
    redis_lib = None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Security: apply HTTPS/HSTS and basic CSP via Talisman in production
    try:
        csp = {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", 'data:'],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'self'"]
        }
        # Allow report-only mode and a configurable report URI via environment variables
        report_only = os.getenv('CSP_REPORT_ONLY', 'False') == 'True'
        report_uri = os.getenv('CSP_REPORT_URI', '/csp-report')

        # Force HTTPS only if configured (e.g. in production)
        force_https = os.getenv('FORCE_HTTPS', 'False') == 'True'
        Talisman(app,
            content_security_policy=csp,
            content_security_policy_report_only=report_only,
            content_security_policy_report_uri=report_uri,
            force_https=force_https,
            strict_transport_security=force_https,
            strict_transport_security_max_age=app.config.get('HSTS_SECONDS', 31536000),
            strict_transport_security_include_subdomains=app.config.get('HSTS_INCLUDE_SUBDOMAINS', True)
        )
    except Exception as e:
        # Don't fail app startup if Talisman not available or misconfigured
        app.logger.warning(f"Talisman not applied: {e}")

    # If app is behind a reverse proxy (common in cPanel/Apache setups), enable ProxyFix
    # Use env var USE_PROXYFIX=True to enable behavior in production where a proxy sets X-Forwarded-* headers
    try:
        if os.getenv('USE_PROXYFIX', 'False') == 'True':
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    except Exception as e:
        app.logger.warning(f"ProxyFix not applied: {e}")

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Initialize rate limiter
    try:
        # If a persistent storage URL is configured, Limiter will use it.
        # `RATELIMIT_STORAGE_URL` can be a Redis URI (recommended for production).
        if app.config.get('RATELIMIT_STORAGE_URL'):
            app.logger.info('Rate limiter storage configured: using persistent backend')
        limiter.init_app(app)
    except Exception as e:
        app.logger.warning(f"Limiter not initialized: {e}")

    # Initialize Sentry if DSN provided
    try:
        sentry_dsn = os.getenv('SENTRY_DSN')
        if sentry_dsn and sentry_sdk is not None:
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.0'))
            )
            app.logger.info('Sentry initialized')
        elif sentry_dsn:
            app.logger.warning('SENTRY_DSN present but sentry-sdk not installed')
    except Exception as e:
        app.logger.warning(f"Sentry initialization failed: {e}")

    # CSRF protection for forms and session-based requests
    try:
        csrf = CSRFProtect()
        csrf.init_app(app)
    except Exception as e:
        app.logger.warning(f"CSRFProtect not initialized: {e}")

    # Structured JSON logging setup
    try:
        # Simplified logging setup - User requested removal of asctime/JSON
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Avoid adding duplicate handlers in repeated create_app calls
        if not root_logger.handlers:
            handler = logging.StreamHandler()
            # Simplified text logging without asctime
            fmt = logging.Formatter('%(levelname)s %(name)s: %(message)s')
            handler.setFormatter(fmt)
            root_logger.addHandler(handler)
    except Exception as e:
        app.logger.warning(f"Logging setup failed: {e}")

        # Ensure each request has a request_id
        @app.before_request
        def inject_request_id():
            rid = request.headers.get('X-Request-ID') or str(uuid4())
            g.request_id = rid
            # Also add to response headers later
            # Note: can't set response here

        @app.after_request
        def add_request_id_header(response):
            try:
                if hasattr(g, 'request_id'):
                    response.headers.setdefault('X-Request-ID', g.request_id)
            except Exception:
                pass
            return response

        # Initialize rate-limit counters storage (Redis preferred; fallback to in-memory)
        app.redis_client = None
        app._inmem_ratelimit_counters = defaultdict(int)
        app._inmem_ratelimit_lock = threading.Lock()
        try:
            storage_url = app.config.get('RATELIMIT_STORAGE_URL')
            if storage_url and redis_lib is not None:
                try:
                    app.redis_client = redis_lib.from_url(storage_url, decode_responses=True)
                    app.logger.info('Connected to Redis for metrics/rate-limit counters')
                except Exception as e:
                    app.logger.warning(f'Could not connect to Redis: {e}; falling back to in-memory counters')
        except Exception:
            pass
    except Exception as e:
        app.logger.warning(f"Structured logging not configured: {e}")

    # Add additional security headers after each request to ensure coverage
    @app.after_request
    def set_secure_headers(response):
        # Prevent MIME type sniffing
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        # Clickjacking protection
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        # Referrer policy
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        # Permissions policy (opt-in minimal surface)
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=()')
        return response

    # Custom handler for rate limit responses (429)
    @app.errorhandler(429)
    def ratelimit_handler(e):
        # Return JSON for API calls, otherwise a simple text response
        retry_after = getattr(e, 'description', None)
        endpoint = request.endpoint or 'unknown'
        # Increment counters in Redis or in-memory
        try:
            if getattr(app, 'redis_client', None):
                r = app.redis_client
                pipe = r.pipeline()
                pipe.incr('ratelimit:total')
                pipe.incr(f'ratelimit:by_endpoint:{endpoint}')
                # keep counters for 30 days
                pipe.expire('ratelimit:total', 60 * 60 * 24 * 30)
                pipe.expire(f'ratelimit:by_endpoint:{endpoint}', 60 * 60 * 24 * 30)
                pipe.execute()
            else:
                with app._inmem_ratelimit_lock:
                    app._inmem_ratelimit_counters['total'] += 1
                    app._inmem_ratelimit_counters[f'by_endpoint:{endpoint}'] += 1
        except Exception as ex:
            app.logger.warning(f'Failed to increment rate-limit counter: {ex}')

        # Log the event for Loki/Grafana
        try:
            app.logger.warning('rate_limited', extra={'endpoint': endpoint, 'request_id': getattr(g, 'request_id', None)})
        except Exception:
            app.logger.warning('rate_limited')

        payload = {'error': 'rate_limited', 'message': 'Too many requests', 'endpoint': endpoint}
        resp = jsonify(payload)
        resp.status_code = 429
        if retry_after:
            resp.headers['Retry-After'] = str(retry_after)
        return resp

    @app.route('/metrics')
    def metrics():
        # Optional simple auth via env token
        token = os.getenv('METRICS_AUTH_TOKEN')
        if token:
            auth = request.headers.get('Authorization', '')
            if not auth.startswith('Bearer ') or auth.split(' ', 1)[1] != token:
                return jsonify({'error': 'unauthorized'}), 401

        data = {}
        try:
            if getattr(app, 'redis_client', None):
                r = app.redis_client
                keys = r.keys('ratelimit:*')
                for k in keys:
                    try:
                        data[k] = int(r.get(k) or 0)
                    except Exception:
                        data[k] = r.get(k)
            else:
                with app._inmem_ratelimit_lock:
                    data = dict(app._inmem_ratelimit_counters)
        except Exception as ex:
            app.logger.warning(f'Error reading metrics: {ex}')
            data = {'error': 'metrics_unavailable'}

        return jsonify({'metrics': data})

    # Register CSP report endpoint helper (if configured)
    try:
        _register_csp_report_endpoint(app)
    except Exception as e:
        app.logger.warning(f"Failed to register CSP report endpoint: {e}")

    # Configure OAuth providers
    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    microsoft = oauth.register(
        name='microsoft',
        client_id=os.getenv('MICROSOFT_CLIENT_ID'),
        client_secret=os.getenv('MICROSOFT_CLIENT_SECRET'),
        server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.api_routes import api_bp
    from app.routes.patient_routes import patient_bp
    from app.routes.therapist_routes import therapist_bp
    from app.routes.admin_routes import admin_bp
    # Protected uploads blueprint (serves files from `instance/uploads` with auth)
    try:
        from app.routes.uploads import uploads_bp
        app.register_blueprint(uploads_bp)
    except Exception:
        # Non-fatal if uploads blueprint missing
        pass
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(patient_bp)
    app.register_blueprint(therapist_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Initialize database and admin user
    with app.app_context():
        if not os.path.exists('ai_models'): 
            os.mkdir('ai_models')
        # Ensure upload folder exists and is outside public static
        try:
            upload_folder = app.config.get('UPLOAD_FOLDER')
            if upload_folder and not os.path.exists(upload_folder):
                os.makedirs(upload_folder, exist_ok=True)
        except Exception as e:
            app.logger.warning(f"Could not create upload folder: {e}")
        db.create_all()
        
        # Lightweight SQLite schema migration
        try:
            from sqlalchemy import text
            conn = db.engine.connect()
            def has_column(table, col):
                rows = conn.execute(text(f"PRAGMA table_info({table})")).mappings().all()
                return any(r['name'] == col for r in rows)
            
            if not has_column('user', 'game_profile'):
                conn.execute(text("ALTER TABLE user ADD COLUMN game_profile TEXT"))
            if not has_column('user', 'assigned_therapist_id'):
                conn.execute(text("ALTER TABLE user ADD COLUMN assigned_therapist_id INTEGER REFERENCES user(id)"))
            if not has_column('appointment', 'games'):
                conn.execute(text("ALTER TABLE appointment ADD COLUMN games TEXT"))
            if not has_column('session_metrics', 'session_id'):
                conn.execute(text("ALTER TABLE session_metrics ADD COLUMN session_id INTEGER REFERENCES appointment(id)"))
            if not has_column('session_metrics', 'game_id'):
                conn.execute(text("ALTER TABLE session_metrics ADD COLUMN game_id INTEGER REFERENCES game(id)"))
            conn.close()
        except Exception as e:
            app.logger.warning(f"Schema migration warning: {e}")
        
        # Initial model training behavior is configurable via env vars:
        # - SKIP_MODEL_TRAIN=1 : skip training entirely at startup
        # - TRAIN_IN_BACKGROUND=0 : run training synchronously (blocking)
        # By default training runs in background (daemon thread) to avoid delaying startup.
        try:
            if os.getenv('SKIP_MODEL_TRAIN') == '1':
                app.logger.info('SKIP_MODEL_TRAIN=1 — skipping initial model training.')
            else:
                if os.getenv('TRAIN_IN_BACKGROUND', '1') == '1':
                    def _bg_train():
                        try:
                            train_model()
                        except Exception as ex:
                            app.logger.exception(f'Background training failed: {ex}')

                    thr = threading.Thread(target=_bg_train, daemon=True)
                    thr.start()
                    app.logger.info('Started background model training thread')
                else:
                    app.logger.info('TRAIN_IN_BACKGROUND=0 — running initial train_model() synchronously')
                    try:
                        train_model()
                    except Exception as ex:
                        app.logger.exception(f'Initial training failed: {ex}')
        except Exception as ex:
            app.logger.exception(f'Error while scheduling initial training: {ex}')
        
        # Create admin user
        admin_email_env = (os.getenv('ADMIN_EMAIL') or '').strip()
        try:
            admin_email = validate_email(admin_email_env).email if admin_email_env else 'diegocenteno537@gmail.com'
        except EmailNotValidError:
            app.logger.warning(f"Invalid ADMIN_EMAIL '{admin_email_env}' in .env; using default fallback email.")
            admin_email = 'diegocenteno537@gmail.com'
        
        admin_password = os.getenv('ADMIN_PASSWORD') or 'Rucula_530'
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            hashed_pw = bcrypt.generate_password_hash(admin_password).decode('utf-8')
            admin = User(
                username='Administrador',
                email=admin_email,
                password=hashed_pw,
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user created: {admin_email}")
        else:
            changed = False
            if admin.role != 'admin':
                admin.role = 'admin'
                changed = True
            if not admin.is_active:
                admin.is_active = True
                changed = True
            if os.getenv('ADMIN_FORCE_RESET') == '1':
                admin.password = bcrypt.generate_password_hash(admin_password).decode('utf-8')
                changed = True
            if changed:
                db.session.commit()
                print(f"Admin user ensured/updated: {admin_email}")

    return app


def _register_csp_report_endpoint(app):
    # Register a route to accept CSP violation reports. Use JSON body from browsers.
    report_uri = os.getenv('CSP_REPORT_URI', '/csp-report')

    def csp_report():
        try:
            payload = request.get_json(force=True, silent=True) or {}
            # Determine client IP (respect X-Forwarded-For if present)
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)

            # Extract common fields
            report = payload.get('csp-report') or payload.get('report') or {}
            document_uri = report.get('document-uri') if isinstance(report, dict) else None
            violated_directive = report.get('violated-directive') if isinstance(report, dict) else None
            blocked_uri = report.get('blocked-uri') if isinstance(report, dict) else None
            original_policy = report.get('original-policy') if isinstance(report, dict) else None

            # Persist to DB
            try:
                cr = CSPReport(
                    document_uri=document_uri,
                    violated_directive=violated_directive,
                    blocked_uri=blocked_uri,
                    original_policy=original_policy,
                    raw_report=str(payload),
                    ip_address=ip,
                    user_id=(current_user.get_id() if current_user and current_user.is_authenticated else None)
                )
                db.session.add(cr)
                db.session.commit()
            except Exception as db_e:
                app.logger.warning(f"Failed to save CSP report to DB: {db_e}")

            # Send to Sentry if configured
            try:
                if 'sentry_sdk' in globals() and sentry_sdk is not None and os.getenv('SENTRY_DSN'):
                    with sentry_sdk.push_scope() as scope:
                        scope.set_extra('csp_report', payload)
                        scope.set_tag('csp', True)
                        if document_uri:
                            scope.set_extra('document_uri', document_uri)
                        if current_user and current_user.is_authenticated:
                            scope.set_user({'id': current_user.get_id(), 'email': getattr(current_user, 'email', None)})
                        sentry_sdk.capture_message('CSP violation reported')
            except Exception as sentry_e:
                app.logger.warning(f"Failed to send CSP report to Sentry: {sentry_e}")

            app.logger.warning(f"CSP violation report received: {payload}")
        except Exception as e:
            app.logger.warning(f"CSP report parse error: {e}")
        return ('', 204)

    # Add the url rule only if it doesn't already exist
    try:
        # Avoid re-registering when create_app is called multiple times
        if report_uri not in [r.rule for r in app.url_map.iter_rules()]:
            app.add_url_rule(report_uri, 'csp_report', csp_report, methods=['POST'])
            # If CSRFProtect is initialized, exempt this endpoint so browsers can POST reports without tokens
            try:
                csrf_ext = app.extensions.get('csrf')
                if csrf_ext:
                    csrf_ext.exempt(csp_report)
            except Exception as e:
                app.logger.warning(f"Could not exempt CSP report endpoint from CSRF: {e}")
    except Exception as e:
        app.logger.warning(f"Could not register CSP report endpoint: {e}")
