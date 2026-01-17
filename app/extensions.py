from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
oauth = OAuth()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
