import pytest
from app import create_app
from app.extensions import db as _db, bcrypt
from config import Config
from app.models import User
# from werkzeug.security import generate_password_hash # Removed

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False # Disable rate limiter for tests
    SERVER_NAME = 'localhost.localdomain' # Required for url_for in tests without request context if needed
    
    # Reset engine options for SQLite (StaticPool does not support pool_size etc.)
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    PROPAGATE_EXCEPTIONS = True

@pytest.fixture(scope='session')
def app():
    app = create_app(TestConfig)
    
    # Push an application context
    ctx = app.app_context()
    ctx.push()
    
    yield app
    
    ctx.pop()

@pytest.fixture(scope='session')
def db(app):
    # create_app already calls db.create_all() for us in this setup, 
    # but ensuring it here is fine.
    _db.create_all()
    
    yield _db
    
    _db.drop_all()

@pytest.fixture(scope='function')
def session(db):
    """Creates a new database session for a test."""
    db.session.begin_nested()
    
    yield db.session
    
    db.session.rollback()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def test_user(session, db):
    existing = User.query.filter_by(email='test@example.com').first()
    if existing:
        return existing
        
    user = User(
        username='testuser', 
        email='test@example.com', 
        password=bcrypt.generate_password_hash('password123').decode('utf-8'),
        role='admin'
    )
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return User.query.filter_by(email='test@example.com').first()
        
    return user
