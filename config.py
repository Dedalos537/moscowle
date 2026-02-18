import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # ========== FLASK CONFIGURATION ==========
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'
    
    # ========== DATABASE OPTIMIZATION ==========
    # Ensure absolute path for SQLite to avoid cwd issues in production
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Priority: Environment Variable (MySQL) > Local SQLite fallback
    # Example MySQL URI: mysql+pymysql://user:password@localhost/db_name
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    
    if not SQLALCHEMY_DATABASE_URI:
        # Fallback to SQLite for local development only
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'moscowle.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    
    # CRITICAL: Connection pool optimization for MySQL
    # Prevent "MySQL server has gone away" during idle periods
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,              # Maintain 10 connections
        'max_overflow': 20,           # Allow up to 20 bursts
        'pool_recycle': 1800,         # Recycle connections every 30 mins (MySQL default timeout is often 8hrs, but strict firewalls cut sooner)
        'pool_pre_ping': True,        # Vital: Check connection aliveness before query
        'pool_timeout': 30            # Fail fast if pool is exhausted
    }
    
    # ========== SECURITY - RATE LIMITING ==========
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    
    # ========== GEMINI API_KEY ==========
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # ========== FILE UPLOADS ==========
    basedir = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(basedir, 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max
    ALLOWED_UPLOAD_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'webp',
        'pdf', 'mp4', 'mov', 'webm',
        'mp3', 'wav', 'ogg', 'm4a', 
        'xls', 'xlsx', 'doc', 'docx', 'txt', 'zip'
    }
    
    # ========== EMAIL CONFIGURATION ==========
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    # Timeout para SMTP (prevent hanging)
    MAIL_TIMEOUT = 10  # segundos
    
    # ========== SESSION CONFIGURATION - CRITICAL ==========
    # These settings help prevent session leaking and improve security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_REFRESH_EACH_REQUEST = True
    # For production, these should terminate https
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax' # Changed to Lax for compatibility
    SESSION_COOKIE_NAME = 'moscowle_session'
    
    # Remember cookie settings
    REMEMBER_COOKIE_SECURE = os.getenv('REMEMBER_COOKIE_SECURE', 'False') == 'True'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    
    # ========== CSRF CONFIGURATION ==========
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit on CSRF tokens
    WTF_CSRF_SSL_STRICT = False 
    
    # ========== SECURITY HEADERS ==========
    PREFERRED_URL_SCHEME = os.getenv('PREFERRED_URL_SCHEME', 'https')
    HSTS_SECONDS = int(os.getenv('HSTS_SECONDS', 31536000))
    HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
    
    # ========== RATE LIMITING - OPTIMIZED ==========
    # Use Redis in production: redis://localhost:6379
    # Fallback to memory if not set
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = "1000 per day,100 per hour"  # Realistic limits
    
    # ========== LOGGING CONFIGURATION ==========
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB per file
    LOG_BACKUP_COUNT = 10
    
    # ========== CELERY CONFIGURATION (for async tasks) ==========
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

class DevelopmentConfig(Config):
    ENV = 'development'
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    ENV = 'production'
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
