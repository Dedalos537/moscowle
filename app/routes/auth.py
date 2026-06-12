from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request
from flask_wtf.csrf import generate_csrf
from app.auth_compat import current_user, login_required
from app.extensions import bcrypt, csrf, db, limiter
from app.schemas.auth_schema import validate_login_input
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.models.refresh_token import RefreshToken
from app.models.password_reset import PasswordReset
from app.models.user import User

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()


def _auto_start_session(user):
    """If therapist logs in during a scheduled session, auto-start recording and create audit."""
    if user.role != 'terapista':
        return
    try:
        now = datetime.utcnow()
        from app.models import Appointment, SessionAudit

        upcoming = Appointment.query.filter(
            Appointment.therapist_id == user.id,
            Appointment.status == 'scheduled',
            Appointment.start_time <= now,
            Appointment.end_time >= now,
        ).all()
        for appt in upcoming:
            appt.status = 'in_progress'
            audit = SessionAudit.query.filter_by(appointment_id=appt.id).first()
            if not audit:
                audit = SessionAudit(appointment_id=appt.id)
                db.session.add(audit)
        if upcoming:
            db.session.commit()
    except Exception:
        pass


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
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        remember = data.get('remember', False)

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email y contraseña requeridos'}), 400

        success, user = auth_service.login(email, password, remember=remember)

        if success == 'mfa_required':
            return jsonify({'success': False, 'mfa_required': True, 'email': user.email}), 401
        if success:
            _auto_start_session(user)
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            csrf_token = generate_csrf()
            response = jsonify(
                {
                    'success': True,
                    'csrf_token': csrf_token,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'role': user.role,
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
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        if not email or not password:
            return jsonify({'valid': False})

        is_valid = auth_service.validate_credentials(email, password)
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
            }
        )
    except Exception as e:
        current_app.logger.warning(f'/api/auth/me error: {e}')
        return jsonify({'error': 'Error al obtener usuario'}), 500


@auth_bp.route('/api/auth/refresh', methods=['POST'])
@csrf.exempt
def api_auth_refresh():
    from flask_jwt_extended import get_jwt
    try:
        verify_jwt_in_request(refresh=True, locations=['cookies'])
        identity = get_jwt_identity()

        # Rotar refresh token: revocar viejo, crear nuevo
        claims = get_jwt()
        jti = claims.get('jti')
        if jti:
            old = RefreshToken.query.filter_by(token_hash=RefreshToken._hash(jti)).first()
            if old:
                old.revoke()

        new_refresh_token = create_refresh_token(identity=identity)
        access_token = create_access_token(identity=identity)

        response = jsonify({'success': True, 'message': 'Token refrescado'})
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, new_refresh_token)
        return response
    except Exception as e:
        current_app.logger.debug(f'Token refresh failed: {e}')
        return jsonify({'success': False, 'error': 'Token inválido o expirado'}), 401


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
            PasswordReset.status == 'pending',
            PasswordReset.expires_at > now,
        ).first()
        if recent:
            return jsonify({'success': True, 'message': 'Si el email existe, recibirás instrucciones.'})

        PasswordReset.query.filter(
            PasswordReset.email == email,
            PasswordReset.status == 'pending',
            PasswordReset.expires_at <= now,
        ).update({'status': 'expired'})
        db.session.commit()

        user = User.query.filter_by(email=email).first()
        record = PasswordReset.create_for_email(email, user_id=user.id if user else None)

        if user:
            EmailService.send_password_reset_code(email, user.username or email, record.code)
            admins = User.query.filter_by(role='admin', is_active=True).all()
            for admin in admins:
                EmailService.send_password_reset_notification_admin(admin.email, email, user.username or email)

        return jsonify({'success': True, 'message': 'Si el email existe, recibirás instrucciones.'})
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

        record = PasswordReset.query.filter(
            PasswordReset.email == email,
            PasswordReset.code == code,
            PasswordReset.status == 'pending',
            PasswordReset.expires_at > datetime.utcnow(),
        ).order_by(PasswordReset.created_at.desc()).first()

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
