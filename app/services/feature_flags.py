import json
import os
from functools import wraps

from flask import abort

from app.auth_compat import current_user

_FLAGS_CACHE = None


def _default_flags():
    return {
        "new_dashboard": {"enabled": False, "description": "Nuevo dashboard con gráficos"},
        "ai_chat_v2": {"enabled": False, "description": "Chat IA con modelo mejorado"},
        "payment_reminders": {"enabled": True, "description": "Recordatorios automáticos de pago"},
        "dark_mode": {"enabled": False, "description": "Interfaz con tema oscuro"},
        "export_reports": {"enabled": True, "description": "Exportar reportes a PDF/Excel"},
        "telehealth": {"enabled": False, "description": "Videollamadas integradas"},
        "bulk_import": {"enabled": False, "description": "Importación masiva de pacientes"},
    }


def _env_overrides(flags):
    override_json = os.environ.get('FEATURE_FLAGS')
    if override_json:
        try:
            overrides = json.loads(override_json)
            for key, value in overrides.items():
                if key in flags and isinstance(value, dict):
                    flags[key].update(value)
                elif key in flags:
                    flags[key]['enabled'] = bool(value)
        except (json.JSONDecodeError, TypeError):
            pass
    return flags


def get_flags():
    global _FLAGS_CACHE
    if _FLAGS_CACHE is None:
        flags = _default_flags()
        _FLAGS_CACHE = _env_overrides(flags)
    return _FLAGS_CACHE


def invalidate_cache():
    global _FLAGS_CACHE
    _FLAGS_CACHE = None


def flag_required(flag_name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            flags = get_flags()
            if not flags.get(flag_name, {}).get('enabled', False):
                if current_user.is_authenticated and current_user.role == 'admin':
                    return f(*args, **kwargs)
                abort(404)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def inject_flags():
    return {'feature_flags': get_flags()}
