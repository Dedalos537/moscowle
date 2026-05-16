from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_login import login_required, current_user
from app.extensions import limiter, csrf
from app.services.auth_service import AuthService
from email_validator import validate_email, EmailNotValidError
from app.schemas.auth_schema import validate_login_input
from flask_wtf.csrf import generate_csrf

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
    if request.headers.get('Accept') and 'application/json' in request.headers.get('Accept', ''):
        return jsonify({'success': True, 'message': 'Sesión cerrada exitosamente'})
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/logout', methods=['POST'])
@csrf.exempt
def api_logout():
    auth_service.logout()
    return jsonify({'success': True, 'message': 'Sesión cerrada exitosamente'})

@auth_bp.route('/api/login', methods=['POST'])
@limiter.limit("20 per minute")
@csrf.exempt
def api_login():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email y contraseña requeridos'}), 400

        success, user = auth_service.login(email, password)

        if success:
            csrf_token = generate_csrf()
            return jsonify({
                'success': True,
                'csrf_token': csrf_token,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'role': user.role,
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Credenciales inválidas o cuenta desactivada'}), 401
    except Exception as e:
        current_app.logger.warning(f"/api/login error: {e}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


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

@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def api_auth_me():
    try:
        return jsonify({
            'id': current_user.id,
            'email': current_user.email,
            'username': current_user.username,
            'role': current_user.role,
        })
    except Exception as e:
        current_app.logger.warning(f"/api/auth/me error: {e}")
        return jsonify({'error': 'Error al obtener usuario'}), 500

