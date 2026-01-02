from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
oauth = OAuth()
login_manager = LoginManager()
