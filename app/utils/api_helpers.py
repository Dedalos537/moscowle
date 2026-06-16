from flask import g, jsonify, request


def api_response(success=True, data=None, error=None, status=200):
    payload = {
        'success': bool(success),
        'data': data or {} if success else None,
        'error': error or None,
        'status': int(status),
    }
    return jsonify(payload), status


def mark_request_api():
    """Detect whether the current request should be treated as an API call.

    Sets `g.is_api = True` when path or headers indicate an API/JSON request.
    """
    try:
        is_api = False
        path = request.path or ''

        if '/api/' in path:
            is_api = True

        if request.blueprint == 'api':
            is_api = True

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            is_api = True

        accept = request.headers.get('Accept', '')
        if 'application/json' in accept or '*/json' in accept or '*/*' in accept:
            is_api = True

        if request.is_json:
            is_api = True

        g.is_api = is_api
    except RuntimeError:
        g.is_api = False
