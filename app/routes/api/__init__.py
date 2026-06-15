import sys
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

_modules = ['sessions', 'admin', 'reports', 'payments', 'games', 'notifications', 'misc']
for _mod in _modules:
    try:
        __import__(f'app.routes.api.{_mod}')
    except Exception as _e:
        print(f'API IMPORT ERROR [{_mod}]: {_e}', file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise
