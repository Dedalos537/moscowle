import hashlib
import time

from flask import Blueprint, current_app, jsonify

public_bp = Blueprint('public', __name__, url_prefix='/api/public')


@public_bp.route('/app-key', methods=['GET'])
def generate_app_key():
    secret = current_app.config.get('APP_SECRET_KEY', 'dev-app-key-change-in-production')
    client_timestamp = int(time.time() / 300)
    message = f'{secret}:{client_timestamp}'
    expected_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()
    app_key = f'{client_timestamp}.{expected_hash}'
    return jsonify({'app_key': app_key, 'expires_in': 300})


@public_bp.route('/session-check', methods=['GET'])
def session_check():
    from flask import request as req
    from flask_login import current_user
    from flask import session

    cookie_header = req.headers.get('Cookie', '')
    has_session_cookie = 'moscowle_session=' in cookie_header

    return jsonify({
        'authenticated': current_user.is_authenticated,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'has_session_cookie': has_session_cookie,
        'cookie_header_sent': bool(cookie_header),
        'cookies_in_header': cookie_header[:200] if cookie_header else '',
        'session_keys': list(session.keys()),
        'session_permanent': session.permanent if hasattr(session, 'permanent') else False,
        'is_secure': req.is_secure,
        'scheme': req.scheme,
        'remote_addr': req.remote_addr,
        'x_forwarded_proto': req.headers.get('X-Forwarded-Proto', 'not-set'),
        'origin': req.headers.get('Origin', 'not-set'),
    })
