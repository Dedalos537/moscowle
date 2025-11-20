import os
from dotenv import load_dotenv
from pathlib import Path

# load .env from backend folder
env_path = Path(__file__).resolve().parents[1] / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:3306/{os.getenv('DB_NAME')}"
    )

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'change-me'))
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_EXPIRES', 3600))

    # Cache (Flask-Caching simple for dev)
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))

    # Flask-Migrate
    MIGRATION_DIR = os.getenv('MIGRATION_DIR', 'migrations')

    # Other
    PROPAGATE_EXCEPTIONS = True
    # Admin email used to identify administrator accounts (no schema change required)
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', os.getenv('DB_ADMIN_EMAIL', 'mamiebamos2@gmail.com'))
