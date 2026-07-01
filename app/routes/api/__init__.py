from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import each sub-module individually so a failure in one doesn't block others.
# Errors are printed to stderr (visible in Railway logs); the blueprint is still
# registered with whatever routes loaded successfully.
import sys as _sys  # noqa: E402

_modules = ['sessions', 'admin', 'reports', 'payments', 'games', 'notifications', 'misc', 'mcp_api']
for _mod in _modules:
    try:
        __import__(f'app.routes.api.{_mod}')
    except Exception as _e:
        print(f'[api] ERROR loading module {_mod}: {_e}', file=_sys.stderr)
        import traceback as _tb

        _tb.print_exc(file=_sys.stderr)
