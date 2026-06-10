from authlib.integrations.flask_client import OAuth
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
bcrypt = Bcrypt()
socketio = SocketIO()
mail = Mail()
oauth = OAuth()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
# Protección básica pa que no flashee en dev. En prod poner 'strong'.
login_manager.session_protection = 'basic'

limiter = Limiter(key_func=get_remote_address)

csrf = CSRFProtect()

cache = Cache()

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
