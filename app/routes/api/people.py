"""Cómo se muestran las personas en el sistema: «nombre y código» o «solo código».

- `GET /api/people/settings`: ajuste del centro (`center_code_only`). Lo lee cualquier usuario del personal.
- `PUT /api/people/settings`: solo admin. Si está activo, todo el personal ve solo códigos y la preferencia
  personal deja de aplicar.
- `GET /api/people/directory`: id, nombre, código y correo de las personas que el usuario ya puede ver
  (admin/supervisor: todos; terapeuta: sus pacientes y el personal). Los pacientes no reciben directorio.
"""

from flask import jsonify, request

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.routes.api import api_bp

SETTING_KEY = 'people.center_code_only'
STAFF_ROLES = ('admin', 'supervisor', 'terapista')


def center_code_only() -> bool:
    row = db.session.get(SystemSetting, SETTING_KEY)
    return bool(row and row.value == '1')


def _row(u):
    return {'id': u.id, 'name': u.username or '', 'code': u.login_code or '', 'email': u.email or '', 'role': u.role}


@api_bp.route('/people/settings', methods=['GET', 'PUT'])
@login_required
def people_settings():
    if request.method == 'PUT':
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Solo un administrador puede cambiarlo'}), 403
        data = request.get_json(silent=True) or {}
        row = db.session.get(SystemSetting, SETTING_KEY) or SystemSetting(key=SETTING_KEY)
        row.value = '1' if data.get('center_code_only') else '0'
        row.updated_by_id = current_user.id
        db.session.add(row)
        db.session.commit()
    return jsonify({'success': True, 'center_code_only': center_code_only()})


@api_bp.route('/people/directory')
@login_required
def people_directory():
    role = current_user.role
    if role in ('admin', 'supervisor'):
        users = User.query.all()
    elif role == 'terapista':
        mine = {p.id: p for p in current_user.associated_patients}
        for p in getattr(current_user, 'assigned_patients', None) or []:
            mine[p.id] = p
        staff = User.query.filter(User.role.in_(STAFF_ROLES)).all()
        users = list(mine.values()) + staff
    else:
        users = []
    seen, out = set(), []
    for u in users:
        if u.id not in seen:
            seen.add(u.id)
            out.append(_row(u))
    return jsonify({'success': True, 'people': out})
