"""Visibilidad del asistente (botón flotante del chatbot) por tipo de usuario.

- `GET /api/assistant/visibility`: el ajuste del centro y si el usuario actual lo ve.
- `PUT /api/assistant/visibility`: solo admin. `{admin, terapista, jugador}` (el supervisor sigue al admin).

Apagado para un rol, el botón no aparece y `/mcp/chat` responde 403 para ese rol.
"""

from flask import jsonify, request

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models.system_setting import SystemSetting
from app.routes.api import api_bp

ROLES = ('admin', 'terapista', 'jugador')
# Hoy el asistente es solo del admin (PRP 009): terapeutas y pacientes se encienden desde Configuración.
DEFAULTS = {'admin': True, 'terapista': False, 'jugador': False}


def _key(role):
    return f'assistant.visible.{role}'


def visibility():
    out = {}
    for role in ROLES:
        row = db.session.get(SystemSetting, _key(role))
        out[role] = DEFAULTS[role] if row is None or row.value is None else row.value == '1'
    return out


def visible_for(role) -> bool:
    group = 'admin' if role in ('admin', 'supervisor') else role
    return bool(visibility().get(group, False))


@api_bp.route('/assistant/visibility', methods=['GET', 'PUT'])
@login_required
def assistant_visibility():
    if request.method == 'PUT':
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Solo un administrador puede cambiarlo'}), 403
        data = request.get_json(silent=True) or {}
        for role in ROLES:
            if role in data:
                row = db.session.get(SystemSetting, _key(role)) or SystemSetting(key=_key(role))
                row.value = '1' if data[role] else '0'
                row.updated_by_id = current_user.id
                db.session.add(row)
        db.session.commit()
    return jsonify({'success': True, **visibility(), 'visible': visible_for(current_user.role)})
