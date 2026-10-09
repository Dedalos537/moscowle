"""Estado del servidor (/api/server-monitor). Solo el rol admin y solo lectura."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import User
from app.services import server_monitor

server_monitor_bp = Blueprint('server_monitor', __name__, url_prefix='/api/server-monitor')


def _is_admin():
    user = db.session.get(User, int(get_jwt_identity()))
    return bool(user and user.role == 'admin' and user.is_active)


@server_monitor_bp.route('/status', methods=['GET'])
@jwt_required()
def status():
    if not _is_admin():
        return jsonify({'error': 'Solo el administrador puede ver el estado del servidor'}), 403
    return jsonify(server_monitor.snapshot_now())


@server_monitor_bp.route('/history', methods=['GET'])
@jwt_required()
def history():
    if not _is_admin():
        return jsonify({'error': 'Solo el administrador puede ver el estado del servidor'}), 403
    try:
        hours = int(request.args.get('hours', 24))
    except ValueError:
        hours = 24
    return jsonify({'snapshots': server_monitor.history(hours)})
