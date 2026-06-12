import os
from datetime import timedelta

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
load_dotenv(os.path.join(basedir, '.env.local'), override=True)


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
    # Read DB URI from environment; do NOT fallback to SQLite here.
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')

    # Read/Write Split — replica connection for SELECT queries
    REPLICA_DATABASE_URL = os.getenv('REPLICA_DATABASE_URL', '')

    SQLALCHEMY_BINDS = {}

    # ========== OLLAMA / LLM CONFIGURATION ==========
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    # CRITICAL: Connection pool optimization for MySQL
    # Prevent "MySQL server has gone away" during idle periods
    # NOTE: SQLite uses NullPool implicitly — skip pooling options for SQLite.
    _uri = os.getenv('SQLALCHEMY_DATABASE_URI', '')
    if _uri.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_recycle': 1800,
            'pool_pre_ping': True,
            'pool_timeout': 30,
        }
        if 'aivencloud.com' in _uri:
            SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {'ssl': {}}

    # ========== SECURITY - RATE LIMITING ==========
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = '200 per day;50 per hour'
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'

    # ========== ALERTING / MONITORING ==========
    CRISIS_CHECK_INTERVAL = int(os.getenv('CRISIS_CHECK_INTERVAL', '300'))
    ALERT_SLACK_WEBHOOK_URL = os.getenv('ALERT_SLACK_WEBHOOK_URL', '')
    ALERT_TELEGRAM_BOT_TOKEN = os.getenv('ALERT_TELEGRAM_BOT_TOKEN', '')
    ALERT_TELEGRAM_CHAT_ID = os.getenv('ALERT_TELEGRAM_CHAT_ID', '')
    ALERT_EMAIL_TO = os.getenv('ALERT_EMAIL_TO', '')
    ALERT_DB_CONN_THRESHOLD = int(os.getenv('ALERT_DB_CONN_THRESHOLD', '50'))
    ALERT_BRUTE_FORCE_THRESHOLD = int(os.getenv('ALERT_BRUTE_FORCE_THRESHOLD', '20'))
    ALERT_BRUTE_FORCE_WINDOW_MINUTES = int(os.getenv('ALERT_BRUTE_FORCE_WINDOW_MINUTES', '15'))

    # ========== TIMEZONE (Peru = UTC-5, no DST) ==========
    TIMEZONE = 'America/Lima'

    # ========== LLM API KEYS ==========
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')

    # ========== FILE UPLOADS ==========
    basedir = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(basedir, 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max
    ALLOWED_UPLOAD_EXTENSIONS = {
        'png',
        'jpg',
        'jpeg',
        'gif',
        'webp',
        'pdf',
        'mp4',
        'mov',
        'webm',
        'mp3',
        'wav',
        'ogg',
        'm4a',
        'xls',
        'xlsx',
        'doc',
        'docx',
        'txt',
        'zip',
    }

    # ========== EMAIL CONFIGURATION ==========
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    # Timeout para SMTP (prevent hanging)
    MAIL_TIMEOUT = 10  # segundos

    # ========== CORS ==========
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'https://moscowle.centrojuanpabloii.com https://centrojuanpabloii.com http://localhost:4200 https://moscowle-backend-production.up.railway.app',
    )
    SOCKET_CORS_ORIGINS = os.getenv('SOCKET_CORS_ORIGINS', 'https://moscowle.ai')

    # ========== SESSION CONFIGURATION - CRITICAL ==========
    # These settings help prevent session leaking and improve security
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_REFRESH_EACH_REQUEST = True
    # For production, these should terminate https
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'None')
    SESSION_COOKIE_NAME = 'moscowle_session'
    # Ensure cookie domain is not set for local development (accept localhost/127.0.0.1)
    SESSION_COOKIE_DOMAIN = None

    # Remember cookie settings
    REMEMBER_COOKIE_SECURE = os.getenv('REMEMBER_COOKIE_SECURE', 'False') == 'True'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)

    # ========== JWT CONFIGURATION ==========
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('APP_SECRET_KEY', SECRET_KEY))
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = os.getenv('JWT_COOKIE_SECURE', 'False') == 'True'
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_SAMESITE = os.getenv('JWT_COOKIE_SAMESITE', 'Lax')
    JWT_SESSION_COOKIE = False  # browser-session vs persistent
    REFRESH_TOKEN_LENGTH = int(os.getenv('REFRESH_TOKEN_LENGTH', '64'))

    # ========== MFA RATE LIMITING ==========
    MFA_MAX_ATTEMPTS = int(os.getenv('MFA_MAX_ATTEMPTS', '5'))
    MFA_LOCKOUT_MINUTES = int(os.getenv('MFA_LOCKOUT_MINUTES', '15'))

    # ========== OAUTH PROVIDERS ==========
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    FACEBOOK_CLIENT_ID = os.getenv('FACEBOOK_CLIENT_ID', '')
    FACEBOOK_CLIENT_SECRET = os.getenv('FACEBOOK_CLIENT_SECRET', '')
    OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', '')

    # ========== APP-SECRET (for App-Key validation) ==========
    APP_SECRET_KEY = os.getenv('APP_SECRET_KEY', 'dev-app-key-change-in-production')

    # ========== CSRF CONFIGURATION ==========
    WTF_CSRF_ENABLED = os.getenv('WTF_CSRF_ENABLED', 'True') == 'True'
    WTF_CSRF_TIME_LIMIT = int(os.getenv('WTF_CSRF_TIME_LIMIT', '3600'))
    WTF_CSRF_SSL_STRICT = os.getenv('WTF_CSRF_SSL_STRICT', 'False') == 'True'

    # ========== SECURITY HEADERS ==========
    PREFERRED_URL_SCHEME = os.getenv('PREFERRED_URL_SCHEME', 'https')
    HSTS_SECONDS = int(os.getenv('HSTS_SECONDS', 31536000))
    HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
    # Allow explicit control to force HTTPS in production via env var.
    FORCE_HTTPS = os.getenv('FORCE_HTTPS', 'False') == 'True'

    # ========== CACHE - Redis support for production ==========
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_REDIS_URL = os.getenv('REDIS_URL')

    # ========== RATE LIMITING - OPTIMIZED ==========
    # Use Redis in production: redis://localhost:6379
    # Fallback to memory if not set
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = '1000 per day,100 per hour'  # Realistic limits

    # ========== LOGGING CONFIGURATION ==========
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', str(10 * 1024 * 1024)))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '10'))
    LOG_JSON_ENABLED = os.getenv('LOG_JSON_ENABLED', 'True') == 'True'

    # ========== CELERY CONFIGURATION (for async tasks) ==========
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')


class DevelopmentConfig(Config):
    ENV = 'development'
    DEBUG = True
    TESTING = False
    # Development-specific relaxation for local HTTP testing
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = False
    FORCE_HTTPS = False


class ProductionConfig(Config):
    ENV = 'production'
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_SAMESITE = 'None'
    WTF_CSRF_SSL_STRICT = True
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = 'None'
    APP_SECRET_KEY = os.getenv('APP_SECRET_KEY', 'change-in-production')

class TestingConfig(Config):
    TESTING = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
