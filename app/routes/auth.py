from contextlib import suppress
from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)
from flask_wtf.csrf import generate_csrf

from app.auth_compat import current_user, login_required
from app.extensions import bcrypt, csrf, db, limiter
from app.models.password_reset import PasswordReset
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth_schema import validate_login_input
from app.services.auth_service import AuthService
from app.services.email_service import EmailService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()


def _token_jti(token):
    """Extrae el jti (identificador) de un JWT emitido por flask-jwt-extended."""
    from flask_jwt_extended.utils import decode_token

    try:
        return decode_token(token).get('jti')
    except Exception:
        return None


def _client_device_info():
    ua = request.headers.get('User-Agent', '') or ''
    return ua[:255]


def _client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()[:45]
    return (request.remote_addr or '')[:45]


def _record_session(user, access_token, refresh_token=None):
    """Persiste una sesion JWT en la DB para permitir revocacion por jti."""
    try:
        from flask import current_app as _app

        access_jti = _token_jti(access_token)
        refresh_jti = _token_jti(refresh_token) if refresh_token else None
        if not access_jti:
            return
        ttl_cfg = _app.config.get('JWT_REFRESH_TOKEN_EXPIRES')
        ttl_seconds = ttl_cfg.total_seconds() if hasattr(ttl_cfg, 'total_seconds') else 30 * 86400
        UserSession.create(
            user_id=user.id,
            access_jti=access_jti,
            refresh_jti=refresh_jti or access_jti,
            ttl_seconds=ttl_seconds,
            device_info=_client_device_info(),
            ip_address=_client_ip(),
        )
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        with suppress(Exception):
            current_app.logger.debug(f'_record_session failed (non-fatal): {exc}')


def _auto_start_session(user):
    """If therapist logs in during a scheduled session, auto-start recording and create audit."""
    if user.role != 'terapista':
        return
    try:
        now = datetime.utcnow()
        from sqlalchemy import or_

        from app.models import Appointment, SessionAudit

        upcoming = Appointment.query.filter(
            Appointment.therapist_id == user.id,
            Appointment.status.in_(['scheduled', 'in_progress']),
            Appointment.start_time <= now,
            or_(Appointment.end_time >= now, Appointment.end_time.is_(None)),
        ).all()
        for appt in upcoming:
            appt.status = 'in_progress'
            audit = SessionAudit.query.filter_by(appointment_id=appt.id).first()
            if not audit:
                audit = SessionAudit(appointment_id=appt.id)
                db.session.add(audit)
        if upcoming:
            db.session.commit()
    except Exception as exc:
        current_app.logger.debug('auto_start_session failed: %s', exc)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('50 per hour')
def login():
    if current_user.is_authenticated:
        next_url = request.args.get('next')
        if next_url and _safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        form = {'email': request.form.get('email', '').strip().lower(), 'password': request.form.get('password', '')}
        data, errors = validate_login_input(form)
        if errors:
            flash('Por favor corrige los errores del formulario.', 'error')
            current_app.logger.debug(f'Login validation errors: {errors}')
            return render_template('login.html')

        email = data['email']
        password = data['password']
        remember = request.form.get('remember') == 'on'

        success, user = auth_service.login(email, password, remember=remember)

        if success == 'mfa_required':
            return redirect(url_for('mfa.mfa_login', email=user.email))
        if success:
            _auto_start_session(user)
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            _record_session(user, access_token, refresh_token)
            next_url = request.form.get('next') or request.args.get('next')
            if next_url and _safe_next_url(next_url):
                response = redirect(next_url)
            else:
                response = redirect(url_for('main.dashboard'))
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
        else:
            flash('Credenciales inválidas o cuenta desactivada.', 'error')
            return render_template('login.html')

    next_url = request.args.get('next')
    return render_template('login.html', next_url=next_url or '')


def _safe_next_url(target):
    from urllib.parse import urljoin, urlparse

    host = urlparse(request.host_url)
    ref = urlparse(urljoin(request.host_url, target))
    return ref.scheme in ('http', 'https') and host.netloc == ref.netloc


@auth_bp.route('/logout')
@login_required
def logout():
    RefreshToken.revoke_all_for_user(current_user.id)
    UserSession.revoke_all_for_user(current_user.id)
    auth_service.logout()
    response = redirect(url_for('auth.login'))
    unset_jwt_cookies(response)
    if request.headers.get('Accept') and 'application/json' in request.headers.get('Accept', ''):
        resp_json = jsonify({'success': True, 'message': 'Sesión cerrada exitosamente'})
        unset_jwt_cookies(resp_json)
        return resp_json
    return response


@auth_bp.route('/api/logout', methods=['POST'])
@csrf.exempt
def api_logout():
    if current_user.is_authenticated:
        RefreshToken.revoke_all_for_user(current_user.id)
        UserSession.revoke_all_for_user(current_user.id)
    auth_service.logout()
    response = jsonify({'success': True, 'message': 'Sesión cerrada exitosamente'})
    unset_jwt_cookies(response)
    return response


@auth_bp.route('/api/login', methods=['POST'])
@limiter.limit('20 per minute')
@csrf.exempt
def api_login():
    try:
        data = request.get_json(silent=True) or {}
        identifier = (data.get('email') or data.get('login_code') or '').strip()
        password = data.get('password') or ''
        remember = data.get('remember', False)

        if not identifier or not password:
            return jsonify({'success': False, 'error': 'Correo/Código y contraseña requeridos'}), 400

        success, user = auth_service.login(identifier, password, remember=remember)

        if success == 'mfa_required':
            return jsonify({'success': False, 'mfa_required': True, 'email': user.email}), 401
        if success:
            _auto_start_session(user)
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            _record_session(user, access_token, refresh_token)
            csrf_token = generate_csrf()
            response = jsonify(
                {
                    'success': True,
                    'csrf_token': csrf_token,
                    'access_token': access_token,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'role': user.role,
                        'login_code': user.login_code,
                        'timezone': getattr(user, 'timezone', None) or 'America/Lima',
                    },
                }
            )
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
        else:
            return jsonify({'success': False, 'error': 'Credenciales inválidas o cuenta desactivada'}), 401
    except Exception as e:
        current_app.logger.warning(f'/api/login error: {e}')
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


@auth_bp.route('/api/auth/validate', methods=['POST'])
@limiter.limit('60 per minute')
@csrf.exempt
def api_auth_validate():
    try:
        data = request.get_json(silent=True) or {}
        identifier = (data.get('email') or data.get('login_code') or '').strip()
        password = data.get('password') or ''
        if not identifier or not password:
            return jsonify({'valid': False})

        is_valid = auth_service.validate_credentials(identifier, password)
        return jsonify({'valid': is_valid})
    except Exception as e:
        current_app.logger.warning(f'/api/auth/validate error: {e}')
        return jsonify({'valid': False})


@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def api_auth_me():
    try:
        return jsonify(
            {
                'id': current_user.id,
                'email': current_user.email,
                'username': current_user.username,
                'role': current_user.role,
                'login_code': getattr(current_user, 'login_code', None),
                'timezone': getattr(current_user, 'timezone', None) or 'America/Lima',
            }
        )
    except Exception as e:
        current_app.logger.warning(f'/api/auth/me error: {e}')
        return jsonify({'error': 'Error al obtener usuario'}), 500


@auth_bp.route('/api/auth/refresh', methods=['POST'])
@csrf.exempt
def api_auth_refresh():
    try:
        verify_jwt_in_request(refresh=True, locations=['cookies', 'headers'])
        identity = get_jwt_identity()

        # Rotar sesion: revocar la fila de la sesion actual y crear una nueva
        claims = get_jwt()
        jti = claims.get('jti')
        if jti:
            old = UserSession.find_by_refresh_jti(jti)
            if old:
                old.revoke()
                db.session.commit()

        user = User.query.get(int(identity)) if identity else None
        new_refresh_token = create_refresh_token(identity=identity)
        access_token = create_access_token(identity=identity)
        if user:
            _record_session(user, access_token, new_refresh_token)

        response = jsonify({'success': True, 'message': 'Token refrescado', 'access_token': access_token})
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, new_refresh_token)
        return response
    except Exception as e:
        current_app.logger.debug(f'Token refresh failed: {e}')
        return jsonify({'success': False, 'error': 'Token inválido o expirado'}), 401


@auth_bp.route('/api/auth/sessions', methods=['GET'])
@login_required
def api_auth_sessions():
    """Lista las sesiones JWT activas del usuario en la DB."""
    try:
        sessions = UserSession.list_active_for_user(current_user.id)
        current_jti = None
        try:
            from flask_jwt_extended import get_jwt

            current_jti = get_jwt().get('jti')
        except Exception:
            pass
        data = [
            {
                'id': s.id,
                'device_info': s.device_info,
                'ip_address': s.ip_address,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'expires_at': s.expires_at.isoformat() if s.expires_at else None,
                'is_current': current_jti in (s.access_jti, s.refresh_jti),
            }
            for s in sessions
        ]
        return jsonify({'success': True, 'sessions': data})
    except Exception as e:
        current_app.logger.warning(f'/api/auth/sessions error: {e}')
        return jsonify({'success': False, 'error': 'Error al listar sesiones'}), 500


@auth_bp.route('/api/auth/sessions/revoke', methods=['POST'])
@csrf.exempt
@login_required
def api_auth_session_revoke():
    """Revoca una sesion especifica del usuario (o todas si session_id es 'all')."""
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id')
        if session_id == 'all' or data.get('revoke_all'):
            UserSession.revoke_all_for_user(current_user.id)
            return jsonify({'success': True, 'message': 'Todas las sesiones fueron revocadas'})
        if not session_id:
            return jsonify({'success': False, 'error': 'session_id requerido'}), 400
        session = UserSession.query.filter_by(id=int(session_id), user_id=current_user.id).first()
        if not session:
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404
        session.revoke()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sesión revocada'})
    except Exception as e:
        current_app.logger.warning(f'/api/auth/sessions/revoke error: {e}')
        return jsonify({'success': False, 'error': 'Error al revocar sesión'}), 500


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit('5 per hour')
@csrf.exempt
def api_reset_password_request():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()

        if not email:
            return jsonify({'success': False, 'error': 'Email requerido'}), 400

        now = datetime.utcnow()
        recent = PasswordReset.query.filter(
            PasswordReset.email == email,
            PasswordReset.status == 'awaiting_approval',
            PasswordReset.expires_at > now,
        ).first()
        if recent:
            return jsonify({'success': True, 'message': 'Si el email existe, un administrador revisará tu solicitud.'})

        PasswordReset.query.filter(
            PasswordReset.email == email,
            PasswordReset.status.in_(['awaiting_approval', 'pending']),
            PasswordReset.expires_at <= now,
        ).update({'status': 'expired'})
        db.session.commit()

        user = User.query.filter_by(email=email).first()
        record = PasswordReset.create_for_email(
            email,
            user_id=user.id if user else None,
            requester_ip=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=request.headers.get('User-Agent', ''),
        )

        if user:
            try:
                from app.services.notification_service import NotificationService

                notif = NotificationService()
                admins = User.query.filter(User.role.in_(['admin', 'supervisor']), User.is_active.is_(True)).all()
                link = '/admin/password-resets'
                for admin in admins:
                    notif.create_notification(
                        user_id=admin.id,
                        title='Solicitud de reseteo de contraseña',
                        message=(
                            f'El usuario {user.username or user.email} ({user.role}) solicitó reseteo de contraseña. '
                            f'Contraseña temporal propuesta: {record.temp_password_plain}. '
                            f'Aprueba o rechaza en la sección de solicitudes.'
                        ),
                        notif_type='warning',
                        link=link,
                        category='security',
                        priority='high',
                        icon='key',
                        metadata_json={
                            'reset_request_id': record.id,
                            'target_user_id': user.id,
                            'target_email': user.email,
                            'target_username': user.username,
                            'temp_password': record.temp_password_plain,
                            'requester_ip': record.requester_ip,
                        },
                    )
            except Exception as ne:
                current_app.logger.error(f'Notif create failed in reset-password: {ne}')

            with suppress(Exception):
                EmailService.send_password_reset_notification_admin(
                    User.query.filter(User.role.in_(['admin', 'supervisor']), User.is_active.is_(True)).first().email
                    if User.query.filter(User.role.in_(['admin', 'supervisor']), User.is_active.is_(True)).first()
                    else email,
                    email,
                    user.username or email,
                )

        return jsonify({'success': True, 'message': 'Si el email existe, un administrador revisará tu solicitud.'})
    except Exception as e:
        current_app.logger.error(f'/api/auth/reset-password error: {e}')
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


@auth_bp.route('/api/auth/reset-password/confirm', methods=['POST'])
@csrf.exempt
def api_reset_password_confirm():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        code = (data.get('code') or '').strip()
        new_password = data.get('new_password') or ''

        if not email or not code or not new_password:
            return jsonify({'success': False, 'error': 'Email, código y nueva contraseña requeridos'}), 400

        if len(new_password) < 8:
            return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

        record = (
            PasswordReset.query.filter(
                PasswordReset.email == email,
                PasswordReset.code == code,
                PasswordReset.status == 'pending',
                PasswordReset.expires_at > datetime.utcnow(),
            )
            .order_by(PasswordReset.created_at.desc())
            .first()
        )

        if not record:
            return jsonify({'success': False, 'error': 'Código inválido o expirado'}), 400

        record.mark_verified()

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()

        record.mark_completed()

        EmailService.send_password_change_email(email, new_password, user.username or email)

        return jsonify({'success': True, 'message': 'Contraseña actualizada exitosamente.'})
    except Exception as e:
        current_app.logger.error(f'/api/auth/reset-password/confirm error: {e}')
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
