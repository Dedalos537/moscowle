import hashlib
import os
import time

from flask import Blueprint, abort, current_app, jsonify, redirect, send_from_directory, url_for

public_bp = Blueprint('public', __name__, url_prefix='/api/public')


@public_bp.route('/app-key', methods=['GET'])
def generate_app_key():
    secret = current_app.config['APP_SECRET_KEY']
    client_timestamp = int(time.time() / 300)
    message = f'{secret}:{client_timestamp}'
    expected_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()
    app_key = f'{client_timestamp}.{expected_hash}'
    return jsonify({'app_key': app_key, 'expires_in': 300})


@public_bp.route('/session-check', methods=['GET'])
def session_check():
    from flask import request as req
    from flask import session
    from flask_login import current_user

    cookie_header = req.headers.get('Cookie', '')
    has_session_cookie = 'moscowle_session=' in cookie_header

    return jsonify(
        {
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
        }
    )


# ========== SERVE ANGULAR SPA FROM FLASK (SAME-ORIGIN) ==========

spa_bp = Blueprint('spa', __name__)

_SPA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'edysync', 'dist', 'edysync', 'browser')
)


@spa_bp.route('/app/')
@spa_bp.route('/app/<path:subpath>')
def serve_spa(subpath='index.html'):
    if not subpath:
        subpath = 'index.html'
    full_path = os.path.normpath(os.path.join(_SPA_DIR, subpath))
    if not full_path.startswith(_SPA_DIR):
        abort(404)
    if os.path.isfile(full_path):
        return send_from_directory(_SPA_DIR, subpath)
    return send_from_directory(_SPA_DIR, 'index.html')


@spa_bp.route('/app')
def redirect_app():
    return redirect(url_for('spa.serve_spa'))
