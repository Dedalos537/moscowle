import sys
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Print diagnostic: how many routes before imports
_routes_before = len(api_bp.deferred_functions) if hasattr(api_bp, 'deferred_functions') else 'N/A'
_api_id = id(api_bp)
print(f'API_BP DIAG: id={_api_id}, routes_before={_routes_before}', file=sys.stderr)

_modules = ['sessions', 'admin', 'reports', 'payments', 'games', 'notifications', 'misc']
for _mod in _modules:
    try:
        __import__(f'app.routes.api.{_mod}')
        _route_count = len(api_bp.deferred_functions) if hasattr(api_bp, 'deferred_functions') else 'N/A'
        print(f'API_BP DIAG: after {_mod} → routes={_route_count}', file=sys.stderr)
    except Exception as _e:
        print(f'API IMPORT ERROR [{_mod}]: {_e}', file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise
