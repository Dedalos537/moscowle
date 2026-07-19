import hashlib
import time
from datetime import datetime
from uuid import uuid4

from flask import Flask, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.auth_compat import current_user


def _is_api_request() -> bool:
    path = request.path or ''
    if '/api/' in path:
        return True
    if getattr(g, 'is_api', False):
        return True
    if request.blueprint == 'api':
        return True
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    if request.is_json:
        return True
    accept = request.headers.get('Accept', '')
    return '*/*' in accept


def register_request_handlers(app: Flask) -> None:
    @app.before_request
    def before_request():
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin', '')
            resp = jsonify({})
            resp.status_code = 200
            allowed = app.config.get('CORS_ORIGINS', 'https://moscowle.centrojuanpabloii.com').replace(',', ' ').split()
            if origin and (origin in allowed or '*' in allowed):
                resp.headers['Access-Control-Allow-Origin'] = origin
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-App-Key, X-CSRFToken'
            resp.headers['Access-Control-Max-Age'] = '86400'
            return resp

        g.request_id = str(uuid4())[:8]
        g.request_start_time = datetime.utcnow()

        has_cookie = 'moscowle_session=' in (request.headers.get('Cookie', ''))
        app.logger.debug(
            'Request started',
            extra={
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_id': current_user.id if current_user.is_authenticated else None,
                'auth': current_user.is_authenticated,
                'has_session_cookie': has_cookie,
                'scheme': request.scheme,
                'is_secure': request.is_secure,
                'origin': request.headers.get('Origin', ''),
            },
        )
        try:
            from app.utils.api_helpers import mark_request_api

            mark_request_api()
        except Exception:
            g.is_api = False

        # Try to authenticate via JWT before App-Key check so authenticated
        # users are recognized even in before_request.
        try:
            verify_jwt_in_request(locations=['cookies', 'headers'], optional=True)
            uid = get_jwt_identity()
            if uid is not None:
                from app.models import User

                g.current_user = User.query.get(int(uid))
        except Exception:
            pass

        if request.path.startswith('/api/') or request.path.startswith('/admin/api/'):
            skip_appkey = (
                app.testing
                or request.method == 'OPTIONS'
                or 'webhook' in request.path
                or request.path.startswith('/api/auth/')
                or request.path in ('/api/login', '/api/logout')
                or request.path.startswith('/api/health')
                or request.path.startswith('/api/public/')
                or request.path.startswith('/api/mcp/')
                or request.path in ('/admin/api/railway-metrics', '/admin/api/logs')
                or current_user.is_authenticated
            )
            if not skip_appkey:
                app_key = request.headers.get('X-App-Key')
                if not app_key:
                    app.logger.warning(
                        'Missing App-Key header', extra={'path': request.path, 'ip': request.remote_addr}
                    )
                    return jsonify({'success': False, 'message': 'Missing App-Key header'}), 403

                try:
                    parts = app_key.split('.')
                    if len(parts) != 2:
                        raise ValueError('Invalid key format')

                    client_timestamp = int(parts[0])
                    client_hash = parts[1]

                    current_timestamp = int(time.time() / 300)
                    if abs(current_timestamp - client_timestamp) > 1:
                        app.logger.warning('Expired App-Key', extra={'path': request.path, 'ip': request.remote_addr})
                        return jsonify({'success': False, 'message': 'Expired App-Key'}), 403

                    secret = app.config['APP_SECRET_KEY']
                    message = f'{secret}:{client_timestamp}'
                    expected_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()

                    if client_hash != expected_hash:
                        app.logger.warning(
                            'Invalid App-Key hash', extra={'path': request.path, 'ip': request.remote_addr}
                        )
                        return jsonify({'success': False, 'message': 'Invalid App-Key'}), 403

                except Exception as e:
                    app.logger.warning(
                        f'App-Key validation failed: {e}',
                        exc_info=True,
                        extra={'path': request.path, 'ip': request.remote_addr},
                    )
                    return jsonify({'success': False, 'message': 'Invalid App-Key format'}), 403

    @app.after_request
    def after_request(response):
        start_time = getattr(g, 'request_start_time', None)
        duration = (datetime.utcnow() - start_time).total_seconds() if start_time else 0

        request_id = getattr(g, 'request_id', 'unknown')

        if response.status_code >= 400:
            app.logger.warning(
                'Request completed with error',
                extra={
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'duration_ms': duration * 1000,
                    'method': request.method,
                    'path': request.path,
                },
            )
        else:
            app.logger.debug(
                'Request completed',
                extra={'request_id': request_id, 'status_code': response.status_code, 'duration_ms': duration * 1000},
            )

        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        origin = request.headers.get('Origin', '')
        if origin and 'Access-Control-Allow-Origin' not in response.headers:
            allowed = app.config.get('CORS_ORIGINS', 'https://moscowle.centrojuanpabloii.com').replace(',', ' ').split()
            if origin in allowed or '*' in allowed:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-App-Key, X-CSRFToken'

        return response
