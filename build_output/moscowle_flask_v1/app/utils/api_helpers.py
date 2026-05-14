from flask import jsonify, request, g

def api_response(success=True, data=None, error=None, status=200):
    payload = {
        'success': bool(success),
        'data': data or {} if success else None,
        'error': error or None,
        'status': int(status)
    }
    return jsonify(payload), status


def mark_request_api():
    """Detect whether the current request should be treated as an API call.

    Sets `g.is_api = True` when path or headers indicate an API/JSON request.
    """
    try:
        is_api = False
        # Explicit API blueprint or path
        if request.blueprint == 'api' or (request.path and request.path.startswith('/api/')):
            is_api = True

        # Ajax / XHR
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            is_api = True

        # Accept header prefers json
        accept = request.headers.get('Accept', '')
        if 'application/json' in accept:
            is_api = True

        # JSON body
        if request.is_json:
            is_api = True

        g.is_api = is_api
    except RuntimeError:
        # No request context
        g.is_api = False
