from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, set_access_cookies

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.services.mfa_service import MFAService

mfa_bp = Blueprint('mfa', __name__, template_folder='../templates')
mfa_service = MFAService()


@mfa_bp.route('/mfa/setup', methods=['GET'])
@login_required
def setup():
    if current_user.mfa_enabled:
        return render_template('mfa_setup.html', qr=None, secret=None, already_enabled=True)
    secret = mfa_service.generate_secret()
    qr = mfa_service.get_qr_svg(secret, current_user.email)
    return render_template('mfa_setup.html', qr=qr, secret=secret, already_enabled=False)


@mfa_bp.route('/mfa/verify-setup', methods=['POST'])
@login_required
def verify_setup():
    code = request.form.get('code', '')
    secret = request.form.get('secret', '')
    if not code or not secret:
        flash('Código requerido', 'error')
        return render_template('mfa_setup.html', qr=mfa_service.get_qr_svg(secret, current_user.email), secret=secret, already_enabled=False)
    if mfa_service.verify_totp(secret, code):
        current_user.otp_secret = secret
        current_user.mfa_enabled = True
        db.session.commit()
        flash('MFA activado exitosamente', 'success')
        return redirect(url_for('main.dashboard'))
    flash('Código inválido. Intenta de nuevo.', 'error')
    return render_template('mfa_setup.html', qr=mfa_service.get_qr_svg(secret, current_user.email), secret=secret, already_enabled=False)


@mfa_bp.route('/mfa/disable', methods=['POST'])
@login_required
def disable():
    current_user.mfa_enabled = False
    current_user.otp_secret = None
    db.session.commit()
    flash('MFA desactivado', 'success')
    return redirect(url_for('main.dashboard'))


@mfa_bp.route('/mfa/login', methods=['GET', 'POST'])
def mfa_login():
    email = request.args.get('email') or request.form.get('email', '')
    if request.method == 'POST':
        code = request.form.get('code', '')
        email = request.form.get('email', '')
        if not code or not email:
            flash('Código requerido', 'error')
            return render_template('mfa_login.html', email=email)
        from app.models import User
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Usuario no encontrado', 'error')
            return render_template('mfa_login.html', email=email)
        lockout = mfa_service.check_lockout(user)
        if lockout['locked']:
            flash(f'Demasiados intentos. Intenta de nuevo en {lockout["minutes_remaining"]} min.', 'error')
            return render_template('mfa_login.html', email=email)
        if user.mfa_enabled and user.otp_secret and mfa_service.verify_totp(user.otp_secret, code):
            mfa_service.record_attempt(user, success=True)
            access_token = create_access_token(identity=str(user.id))
            response = redirect(url_for('main.dashboard'))
            set_access_cookies(response, access_token)
            return response
        mfa_service.record_attempt(user, success=False)
        flash('Código inválido', 'error')
        return render_template('mfa_login.html', email=email)
    return render_template('mfa_login.html', email=email)


@mfa_bp.route('/api/mfa/verify', methods=['POST'])
def api_verify():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    email = data.get('email', '')
    if not code or not email:
        return jsonify({'success': False, 'error': 'Código y email requeridos'}), 400
    from app.models import User
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 401
    lockout = mfa_service.check_lockout(user)
    if lockout['locked']:
        return jsonify({
            'success': False,
            'error': f'Demasiados intentos. Intenta de nuevo en {lockout["minutes_remaining"]} min.',
        }), 429
    if user.mfa_enabled and user.otp_secret and mfa_service.verify_totp(user.otp_secret, code):
        mfa_service.record_attempt(user, success=True)
        access_token = create_access_token(identity=str(user.id))
        response = jsonify({'success': True})
        set_access_cookies(response, access_token)
        return response
    mfa_service.record_attempt(user, success=False)
    return jsonify({'success': False, 'error': 'Código inválido'}), 401
