from flask import jsonify, g

def api_response(success=True, data=None, error=None, status=200):
    payload = {
        'success': bool(success),
        'data': data or {} if success else None,
        'error': error or None,
        'status': int(status)
    }
    return jsonify(payload), status


def mark_request_api():
    try:
        from app.middleware.request_handlers import _is_api_request
        g.is_api = _is_api_request()
    except RuntimeError:
        g.is_api = False
