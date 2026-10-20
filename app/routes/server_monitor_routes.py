"""Estado del servidor (/api/server-monitor). Solo el rol admin y solo lectura."""

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import User
from app.services import app_metrics, server_monitor

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


# ── Prometheus (PRP 010) ─────────────────────────────────────────────────────
@server_monitor_bp.route('/metrics', methods=['GET'])
@limiter.exempt
def metrics():
    """Métricas para Prometheus del host. Con token (METRICS_TOKEN): por el túnel todo llega desde el host."""
    if not app_metrics.authorized(request.headers.get('Authorization')):
        return Response('unauthorized\n', status=401, mimetype='text/plain')
    return Response(app_metrics.render(), mimetype='text/plain; version=0.0.4')


@server_monitor_bp.route('/alerts', methods=['POST'])
@limiter.exempt
def alerts():
    """Webhook de Alertmanager: avisa a los admins (notificación en la app + Telegram según sus preferencias)."""
    if not app_metrics.authorized(request.headers.get('Authorization'), env='ALERT_WEBHOOK_TOKEN'):
        return jsonify({'error': 'unauthorized'}), 401
    payload = request.get_json(silent=True) or {}
    sent = server_monitor.notify_alerts(payload.get('alerts') or [])
    return jsonify({'ok': True, 'notified': sent})
