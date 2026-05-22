
from functools import wraps
from flask import redirect, url_for, jsonify
from flask_login import current_user


def admin_required(f):
    """
    Decorator que requiere que el usuario esté autenticado y tenga rol 'admin'.
    Si no, redirige a login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Si es una request AJAX, retornar JSON
            if hasattr(current_user, '_get_current_object'):
                return jsonify({'error': 'Unauthorized'}), 403
            return redirect(url_for('auth.login'))
        
        if current_user.role != 'admin':
            # Retornar 403 Forbidden
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def therapist_required(f):
    """Decorator que requiere rol 'terapista'."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'terapista':
            return jsonify({'error': 'Therapist access required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function


def patient_required(f):
    """Decorator que requiere rol 'jugador' (paciente)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'jugador':
            return jsonify({'error': 'Patient access required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function
