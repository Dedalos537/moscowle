from flask import jsonify


def api_response(data=None, message='OK', status_code=200, success=True):
    payload = {'success': bool(success), 'data': data, 'message': message}
    return jsonify(payload), status_code
