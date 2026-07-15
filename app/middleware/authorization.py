"""Centralized authorization middleware with role-based access control.

Usage:
    @role_required('admin', 'supervisor')
    def my_route():
        ...

    @role_required('admin')
    def admin_only():
        ...

Permission matrix is defined in PERMISSION_MATRIX below.
"""

from functools import wraps

from flask import jsonify

from app.auth_compat import current_user

# Permission matrix: route pattern -> allowed roles
# Extend this as new routes are added
PERMISSION_MATRIX = {
    # Admin routes
    '/admin/dashboard': ('admin', 'supervisor'),
    '/admin/users': ('admin',),
    '/admin/sedes': ('admin', 'supervisor'),
    '/admin/finanzas': ('admin', 'supervisor'),
    '/admin/games': ('admin',),
    '/admin/reports': ('admin', 'supervisor'),
    '/admin/messages': ('admin', 'supervisor'),
    '/admin/incidents': ('admin', 'supervisor'),
    '/admin/sessions': ('admin', 'supervisor'),
    # API admin routes
    '/api/admin/profile': ('admin', 'supervisor'),
    '/api/admin/users': ('admin',),
    '/api/admin/sedes': ('admin', 'supervisor'),
    '/api/incidents/dashboard': ('admin', 'supervisor'),
    '/api/incidents/metrics': ('admin', 'supervisor'),
    '/api/incidents': ('admin', 'supervisor', 'terapista', 'jugador'),
    # Therapist routes
    '/therapist/dashboard': ('terapista',),
    '/therapist/sessions': ('terapista',),
    '/therapist/patients': ('terapista',),
    '/therapist/incidents': ('terapista',),
    # Patient routes
    '/patient/dashboard': ('jugador',),
    '/patient/sessions': ('jugador',),
    '/patient/incidents': ('jugador',),
}


def role_required(*allowed_roles):
    """Decorator that restricts access to users with specific roles.

    Must be used AFTER @login_required.

    Args:
        *allowed_roles: One or more role strings that are allowed access.
            e.g. @role_required('admin', 'supervisor')
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'No autenticado'}), 401

            if current_user.role not in allowed_roles:
                return jsonify({'error': 'Acceso denegado', 'required_roles': list(allowed_roles)}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def check_permission(route_path):
    """Check if current user has permission for a given route path.

    Returns True if allowed, False otherwise.
    """
    if not current_user.is_authenticated:
        return False

    allowed = PERMISSION_MATRIX.get(route_path)
    if allowed is None:
        return True  # No restriction defined = public

    return current_user.role in allowed
