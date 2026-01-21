import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'moscowle_secret')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///moscowle.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Uploads - store outside the public static tree for protected access
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max limit
    # Allowed upload extensions
    ALLOWED_UPLOAD_EXTENSIONS = set(("png", "jpg", "jpeg", "gif", "webp", "pdf", "mp4", "mov", "webm", "mp3", "wav", "ogg", "m4a", "xls", "xlsx", "doc", "docx", "txt", "zip"))

    # Email configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Session / Cookie security
    # Use environment variables so local development (http) works by default.
    # To enable secure cookies in production set SESSION_COOKIE_SECURE=True in the .env
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True') == 'True'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

    # Remember cookie (Flask-Login) settings
    REMEMBER_COOKIE_SECURE = os.getenv('REMEMBER_COOKIE_SECURE', 'False') == 'True'
    REMEMBER_COOKIE_HTTPONLY = os.getenv('REMEMBER_COOKIE_HTTPONLY', 'True') == 'True'
    REMEMBER_COOKIE_SAMESITE = os.getenv('REMEMBER_COOKIE_SAMESITE', 'Lax')

    # Force HTTPS scheme for URL generation (used by url_for)
    PREFERRED_URL_SCHEME = os.getenv('PREFERRED_URL_SCHEME', 'https')

    # HSTS settings (in seconds) - 1 year default; enable via env
    HSTS_SECONDS = int(os.getenv('HSTS_SECONDS', 31536000))
    HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
    
    # CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True
    # Set to None to disable time limit on CSRF tokens (refresh tokens handled elsewhere)
    WTF_CSRF_TIME_LIMIT = None

    # Rate limiting (Flask-Limiter)
    # Use `RATELIMIT_STORAGE_URL` to point to a Redis or Memcached backend for production.
    # If not set, we default to filesystem storage to avoid memory leaks/loss in multi-worker environments.
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL') or 'memory://'
    # Recommended production setting if Redis is unavailable:
    # RATELIMIT_STORAGE_URL = "filesystem://" + os.path.join(os.getcwd(), "instance", "limits")
    # Enable rate limit headers (X-RateLimit-*) for visibility
    RATELIMIT_HEADERS_ENABLED = os.getenv('RATELIMIT_HEADERS_ENABLED', 'True') == 'True'
    # Default limits (can be overridden per-route with decorators)
    # Format: a list of limits like ["200 per day", "50 per hour"]
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', "200 per day,50 per hour")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
