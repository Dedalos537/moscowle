from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

from . import sessions, admin, reports, payments, games, notifications, misc
