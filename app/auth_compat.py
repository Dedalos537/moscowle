from functools import wraps

from flask import g, jsonify, make_response, redirect, request, url_for
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.local import LocalProxy


class AnonymousUser:
    is_authenticated = False
    is_active = False
    is_anonymous = True
    id = None
    role = None

    def __bool__(self):
        return False


_anonymous = AnonymousUser()


def _get_current_user():
    return g.get('current_user', _anonymous)


current_user = LocalProxy(_get_current_user)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return make_response('', 204)
        try:
            verify_jwt_in_request(locations=['cookies', 'headers'])
            user_id = get_jwt_identity()
            if user_id is None:
                raise ValueError('No user identity in token')
            from app.models import User  # noqa: PLC0415

            g.current_user = User.query.get(int(user_id))
            if g.current_user is None:
                raise ValueError('User not found')
        except Exception:
            path = request.path or ''
            if '/api/' in path or getattr(g, 'is_api', False) or request.accept_mimetypes.accept_json:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def mfa_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.mfa_enabled:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function
