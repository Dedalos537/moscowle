from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user, logout_user
from app.extensions import bcrypt
from app.models import db
from app.services.email_service import EmailService
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'terapista':
        return redirect(url_for('therapist.dashboard'))
    elif current_user.role == 'jugador':
        return redirect(url_for('patient.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/game')
@login_required
def game():
    return render_template('game.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# ==================== MESSAGING SYSTEM ====================
@main_bp.route('/messages')
@login_required
def messages_list():
    if current_user.role == 'admin':
        return redirect(url_for('admin.messages'))
    elif current_user.role == 'jugador':
        return redirect(url_for('patient.messages'))
    elif current_user.role == 'terapista':
        return redirect(url_for('therapist.messages'))
    
    return redirect(url_for('main.dashboard'))

# ==================== PROFILE MANAGEMENT ====================
@main_bp.route('/profile')
@login_required
def profile():
    if current_user.role == 'admin':
        return redirect(url_for('admin.profile'))
    elif current_user.role == 'jugador':
        return redirect(url_for('patient.profile'))
    elif current_user.role == 'terapista':
        return redirect(url_for('therapist.profile'))
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    # Accept JSON body only; return JSON
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    phone = (data.get('phone') or '').strip()
    date_of_birth = (data.get('date_of_birth') or '').strip()
    timezone = (data.get('timezone') or '').strip()

    # Validate timezone (basic allowlist matching the UI options)
    allowed_tz = {
        'America/Lima',
        'America/New_York',
        'America/Mexico_City',
        'America/Bogota',
        'America/Argentina/Buenos_Aires',
        'Europe/Madrid'
    }
    if timezone and timezone not in allowed_tz:
        return jsonify({'success': False, 'message': 'Zona horaria inválida'}), 400

    # Parse date_of_birth (accept YYYY-MM-DD and DD/MM/YYYY)
    dob_dt = None
    if date_of_birth:
        parsed = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                parsed = datetime.strptime(date_of_birth, fmt).date()
                break
            except Exception:
                continue
        if not parsed:
            return jsonify({'success': False, 'message': 'Fecha de nacimiento inválida'}), 400
        dob_dt = parsed

    # Apply changes
    try:
        current_user.username = username or current_user.username
        current_user.phone = phone
        current_user.timezone = timezone or current_user.timezone
        current_user.date_of_birth = dob_dt if dob_dt else current_user.date_of_birth
        db.session.commit()
        return jsonify({'success': True, 'message': 'Perfil actualizado correctamente'})
    except Exception as e:
        current_app.logger.error(f"Profile update failed for user {current_user.id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al actualizar el perfil'}), 500


@main_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    # Basic validations aligned with UI
    if not current_password or not new_password:
        return jsonify({'success': False, 'message': 'Completa todos los campos'}), 400

    # Verify current password
    try:
        if not bcrypt.check_password_hash(current_user.password, current_password):
            return jsonify({'success': False, 'message': 'La contraseña actual es incorrecta'}), 400
    except Exception:
        # In case legacy hashes cause issues, fail securely
        return jsonify({'success': False, 'message': 'No se pudo verificar la contraseña actual'}), 400

    # Enforce minimum strength (sync with front-end suggestions)
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 8 caracteres'}), 400
    if not any(c.islower() for c in new_password):
        return jsonify({'success': False, 'message': 'La contraseña debe incluir una letra minúscula'}), 400
    if not any(c.isupper() for c in new_password):
        return jsonify({'success': False, 'message': 'La contraseña debe incluir una letra mayúscula'}), 400
    if not any(c.isdigit() for c in new_password):
        return jsonify({'success': False, 'message': 'La contraseña debe incluir un número'}), 400

    # Update password
    try:
        hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
        current_user.password = hashed_pw
        db.session.commit()
        # Fire-and-forget email (do not block success)
        try:
            EmailService.send_password_change_email(current_user.email, new_password, current_user.username)
        except Exception as e:
            current_app.logger.warning(f"Non-blocking: error sending password change email: {e}")
        return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'})
    except Exception as e:
        current_app.logger.error(f"Password change failed: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al cambiar la contraseña'}), 500



