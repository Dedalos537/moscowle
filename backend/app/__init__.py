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
    cors.init_app(app)
    bcrypt.init_app(app)

    # Register blueprints (import here to avoid circular imports)
    # Ensure models are imported so SQLAlchemy can register all mappers
    # Importing models here avoids mapper resolution errors due to import order
    from .models import user as _user  # noqa: F401
    from .models import patient as _patient  # noqa: F401
    from .models import therapies as _therapies  # noqa: F401
    from .models import appointments as _appointments  # noqa: F401

    from .routes.auth_routes import auth_bp
    from .routes.patient_routes import patient_bp
    from .routes.appointment_routes import appointment_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(patient_bp, url_prefix="/api/patients")
    app.register_blueprint(appointment_bp, url_prefix="/api/appointments")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
