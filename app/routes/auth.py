from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import limiter, csrf
from app.services.auth_service import AuthService
from email_validator import validate_email, EmailNotValidError
from app.schemas.auth_schema import validate_login_input

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("50 per hour")
def login():
    # Redirect authenticated users away from the login page to avoid loops
    try:
        if current_user and current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
    except Exception:
        # If current_user access fails (e.g. user_loader not ready), continue to show login
        pass
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
@limiter.limit("60 per minute")
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
        current_app.logger.warning(f"/api/auth/validate error: {e}")
        return jsonify({'valid': False})

# OAuth routes (commented out as in original)
# @auth_bp.route('/login/google')
# def login_google():
#     # ...
#     pass
