from authlib.integrations.flask_client import OAuth
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
bcrypt = Bcrypt()
jwt = JWTManager()
socketio = SocketIO()
mail = Mail()
oauth = OAuth()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'

def _rate_limit_key():
    """Clave por usuario autenticado, con fallback a IP remota.

    Toda la clinica sale por la misma IP publica, asi que limitar solo por IP
    hace que los usuarios compartan un solo bucket y se bloqueen entre ellos.
    """
    try:
        user_id = getattr(current_user, 'id', None)
        if user_id:
            return f'user:{user_id}'
        return f'ip:{get_remote_address()}'
    except Exception:
        return 'ip:unknown'


limiter = Limiter(key_func=_rate_limit_key)

csrf = CSRFProtect()

cache = Cache()

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
