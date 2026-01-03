from flask import Flask
from config import Config
from app.extensions import db, bcrypt, mail, oauth, login_manager
from app.models import User
from app.services.ai_service import train_model
import os
from email_validator import validate_email, EmailNotValidError

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

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
        
        train_model()
        
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
