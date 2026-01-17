from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required
from app.extensions import limiter
from app.services.auth_service import AuthService
from email_validator import validate_email, EmailNotValidError
from app.schemas.auth_schema import validate_login_input

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes")
def login():
    if request.method == 'POST':
        form = {
            'email': request.form.get('email', '').strip().lower(),
            'password': request.form.get('password', '')
        }
        data, errors = validate_login_input(form)
        if errors:
            flash('Por favor corrige los errores del formulario.', 'error')
            current_app.logger.debug(f"Login validation errors: {errors}")
            return render_template('login.html')

        email = data['email']
        password = data['password']

        success, user = auth_service.login(email, password)

        if success:
            return redirect(url_for('main.dashboard'))
        else:
            flash('Credenciales inválidas o cuenta desactivada.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    auth_service.logout()
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/auth/validate', methods=['POST'])
@limiter.limit("10 per minute")
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
        current_app.logger.warning(f"/api/auth/validate error: {e}")
        return jsonify({'valid': False})

# OAuth routes (commented out as in original)
# @auth_bp.route('/login/google')
# def login_google():
#     # ...
#     pass
