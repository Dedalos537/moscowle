
from functools import wraps
from flask import redirect, url_for, jsonify
from flask_login import current_user


def admin_required(f):
    """
    Decorator que requiere rol 'admin' o 'supervisor'.
    Supervisor solo puede acceder a endpoints GET (lectura).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if hasattr(current_user, '_get_current_object'):
                return jsonify({'error': 'Unauthorized'}), 403
            return redirect(url_for('auth.login'))
        if current_user.role not in ('admin', 'supervisor'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def admin_write_required(f):
    """Decorator para endpoints de escritura — solo admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 403
        if current_user.role != 'admin':
            return jsonify({'error': 'Solo administradores pueden realizar esta acción'}), 403
        return f(*args, **kwargs)
    return decorated_function


def check_write_access():
    """Helper para bloquear escritura a supervisor desde el body de la ruta."""
    if current_user.role == 'supervisor':
        from flask import abort
        abort(403, description='Solo administradores pueden realizar esta acción')


def supervisor_allowed(f):
    """Decorator que permite acceso a admin y supervisor (solo lectura)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 403
        if current_user.role not in ('admin', 'supervisor'):
            return jsonify({'error': 'Access denied'}), 403
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
