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

db = SQLAlchemy()
cors = CORS()
bcrypt = Bcrypt()
mail = Mail()
oauth = OAuth()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
# Protección básica pa que no flashee en dev. En prod poner 'strong'.
login_manager.session_protection = 'basic'

limiter = Limiter(key_func=get_remote_address)

csrf = CSRFProtect()

cache = Cache(config={'CACHE_TYPE': 'simple'})

from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
