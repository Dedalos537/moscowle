import hashlib
import os
import time
from html import escape
from urllib.parse import quote

from flask import Blueprint, Response, abort, current_app, jsonify, redirect, request, send_from_directory, url_for

from app.extensions import csrf, db, limiter

public_bp = Blueprint('public', __name__, url_prefix='/api/public')


_UNSUB_PAGE = (
    '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Resumen diario</title></head>'
    '<body style="font-family:system-ui,sans-serif;max-width:28rem;margin:3rem auto;padding:0 1rem;color:#222">'
    '<h1 style="font-size:1.25rem">Centro Juan Pablo II</h1>{body}</body></html>'
)


def _unsub_page(body, status=200):
    return Response(_UNSUB_PAGE.format(body=body), status=status, mimetype='text/html')


@public_bp.route('/email/unsubscribe', methods=['GET', 'POST'])
@csrf.exempt
def email_unsubscribe():
    """Baja del resumen diario por correo, sin login (token firmado en el enlace).

    POST aplica la baja (baja con un clic, RFC 8058: la usa el propio Gmail). GET solo
    muestra la confirmacion: un escaner de enlaces que abra la URL no debe dar de baja."""
    from app.models.notification import UserNotificationPreference
    from app.utils.email_tokens import read_unsubscribe_token

    token = request.args.get('t', '')
    user_id = read_unsubscribe_token(token)
    if user_id is None:
        return _unsub_page('<p>El enlace no es válido o venció.</p>', 400)

    if request.method == 'GET':
        return _unsub_page(
            '<p>¿Quieres dejar de recibir el <strong>resumen diario</strong> por correo?</p>'
            f'<form method="post" action="?t={escape(quote(token))}">'
            '<button type="submit" style="padding:.6rem 1rem;font-size:1rem">Sí, darme de baja</button></form>'
            '<p style="font-size:.85rem;color:#666">Puedes volver a activarlo desde Preferencias en la plataforma.</p>'
        )

    prefs = UserNotificationPreference.query.filter_by(user_id=user_id).first()
    if prefs is None:
        prefs = UserNotificationPreference(user_id=user_id)
        db.session.add(prefs)
    prefs.digest_enabled = False
    db.session.commit()
    return _unsub_page('<p>Listo: ya no recibirás el resumen diario por correo.</p>')


@public_bp.route('/app-key', methods=['GET'])
@limiter.exempt
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
