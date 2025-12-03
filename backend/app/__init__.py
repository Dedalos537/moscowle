from flask import Flask
from .config import Config
from .extensions import db, migrate, jwt, cache, cors, bcrypt


def create_app(config_object: str = None):
    app = Flask(__name__, instance_relative_config=False)

    # Load configuration
    if config_object:
        app.config.from_object(config_object)
    else:
        app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cache.init_app(app)
    
    # Configure CORS to allow requests from frontend and dashboard
    cors_config = {
        "origins": [
            "http://localhost:3001",  # Dashboard
            "http://localhost:3002",  # Principal_Page
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
    }
    cors.init_app(app, resources={"/api/*": cors_config})
    bcrypt.init_app(app)

    # Register blueprints (import here to avoid circular imports)
    # Ensure models are imported so SQLAlchemy can register all mappers
    # Importing models here avoids mapper resolution errors due to import order
    from .models import user as _user  # noqa: F401
    from .models import patient as _patient  # noqa: F401
    from .models import therapies as _therapies  # noqa: F401
    from .models import appointments as _appointments  # noqa: F401
    from .models import session_metrics as _session_metrics  # noqa: F401
    from .models import contact as _contact  # noqa: F401

    from .routes.auth_routes import auth_bp
    from .routes.patient_routes import patient_bp
    from .routes.appointment_routes import appointment_bp
    from .routes.roles_routes import roles_bp
    from .routes.users_routes import users_bp
    from .routes.session_metrics_routes import session_metrics_bp
    from .routes.ai_routes import ai_bp
    from .routes.contact_routes import contact_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(patient_bp, url_prefix="/api/patients")
    app.register_blueprint(appointment_bp, url_prefix="/api/appointments")
    app.register_blueprint(roles_bp, url_prefix="/api/roles")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(session_metrics_bp, url_prefix="/api/session-metrics")
    app.register_blueprint(ai_bp)
    app.register_blueprint(contact_bp, url_prefix="/api")

    # Register centralized error handlers
    from .errors import register_error_handlers
    register_error_handlers(app)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
