from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_caching import Cache
from flask_cors import CORS

# Database
db = SQLAlchemy()

# CORS
cors = CORS()

# Password hashing
bcrypt = Bcrypt()

# Email
mail = Mail()

# OAuth2
oauth = OAuth()

# Login management
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    # default_limits=["200 per day", "50 per hour"] # Moved to config
)

# CSRF Protection
csrf = CSRFProtect()

# Caching (optional, for future use)
cache = Cache(config={'CACHE_TYPE': 'simple'})

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
