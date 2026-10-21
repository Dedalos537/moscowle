"""Revisión de actividad por usuario (PRP 012). Solo admin."""

import io
from datetime import datetime, timedelta
from functools import wraps

from flask import jsonify, request, send_file

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models import User
from app.routes.admin import admin_bp
from app.services import activity_review as act


def _admin_only(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not getattr(current_user, 'is_authenticated', False) or current_user.role != 'admin':
            return jsonify({'error': 'Solo el administrador puede revisar la actividad'}), 403
        return fn(*args, **kwargs)

    return wrapper


def _date(value, default):
    try:
        return datetime.fromisoformat(value) if value else default
    except ValueError:
        return default


def _target(user_id):
    user = db.session.get(User, user_id)
    return user if user else None


@admin_bp.route('/api/activity/users', methods=['GET'])
@login_required
@_admin_only
def activity_users():
    rows = act.users_overview(
        role=request.args.get('role') or None,
        sede_id=request.args.get('sede_id') or None,
        only_pending=request.args.get('only_pending') == '1',
        query=request.args.get('q') or None,
    )
    return jsonify({'users': rows})


@admin_bp.route('/api/activity/users/<int:user_id>', methods=['GET'])
@login_required
@_admin_only
def activity_user_detail(user_id):
    user = _target(user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    # Quién miró a quién: la revisión también deja rastro.
    act.record(current_user.id, 'activity.viewed', 'user', user.id, f'Revisó la actividad de {user.username}')
    db.session.commit()
    return jsonify(
        {
            'user': {
                'id': user.id,
                'name': user.username or user.email,
                'role': user.role,
                'login_code': user.login_code,
            },
            'pending': act.pending_for(user),
            'sessions': act.sessions_of(user),
            'daily': act.daily_counts(user),
        }
    )


@admin_bp.route('/api/activity/users/<int:user_id>/timeline', methods=['GET'])
@login_required
@_admin_only
def activity_user_timeline(user_id):
    user = _target(user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    end = _date(request.args.get('to'), datetime.utcnow())
    start = _date(request.args.get('from'), end - timedelta(days=30))
    types = [t for t in (request.args.get('types') or '').split(',') if t] or None
    page = max(1, int(request.args.get('page') or 1))
    return jsonify(act.timeline(user, start, end, types, page))


@admin_bp.route('/api/activity/users/<int:user_id>/revoke-sessions', methods=['POST'])
@login_required
@_admin_only
def activity_revoke_sessions(user_id):
    user = _target(user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if user.id == current_user.id:
        return jsonify({'error': 'Para cerrar tus propias sesiones usa «Cerrar sesión» en tu perfil.'}), 400
    return jsonify({'success': True, 'revoked': act.revoke_sessions(user, current_user.id)})


@admin_bp.route('/api/activity/export.xlsx', methods=['GET'])
@login_required
@_admin_only
def activity_export():
    from openpyxl import Workbook
    from openpyxl.styles import Font

    end = _date(request.args.get('to'), datetime.utcnow())
    start = _date(request.args.get('from'), end - timedelta(days=30))
    ids = [int(request.args['user_id'])] if request.args.get('user_id') else None
    users = User.query.filter(User.id.in_(ids)).all() if ids else User.query.filter(User.is_active.isnot(False)).all()
    wb = Workbook()
    ws = wb.active
    ws.title = 'Actividad'
    ws.append(['Fecha (UTC)', 'Usuario', 'Rol', 'Tipo', 'Detalle'])
    for c in ws[1]:
        c.font = Font(bold=True)
    for u in users:
        for ev in act.timeline(u, start, end, page=1, per_page=100000)['events']:
            ws.append([ev['at'], u.username or u.email, u.role, ev['type'], ev['summary']])
    for col, width in zip('ABCDE', (22, 28, 12, 18, 80), strict=False):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    act.record(current_user.id, 'activity.exported', 'user', ids[0] if ids else None, 'Exportó la actividad a Excel')
    db.session.commit()
    name = f'actividad_{start:%Y%m%d}_{end:%Y%m%d}.xlsx'
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=name,
    )
