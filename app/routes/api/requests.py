"""Solicitudes de terapeutas a la coordinación (sesiones, pacientes, grupos)."""

from flask import jsonify, request

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models.action_request import ActionRequest
from app.routes.api import api_bp
from app.services.action_requests import RequestError, notify_staff, resolve, validate


@api_bp.route('/requests', methods=['POST'])
@login_required
def create_action_request():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Solo los terapeutas envían solicitudes.'}), 403
    data = request.get_json(silent=True) or {}
    try:
        payload, summary = validate(data.get('kind'), data.get('payload'), current_user)
    except RequestError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    req = ActionRequest(requester_id=current_user.id, kind=data['kind'], payload=payload, summary=summary)
    db.session.add(req)
    db.session.commit()
    notify_staff(req)
    return jsonify({'success': True, 'request': req.to_dict()}), 201


@api_bp.route('/requests/mine', methods=['GET'])
@login_required
def my_action_requests():
    rows = (
        ActionRequest.query.filter_by(requester_id=current_user.id)
        .order_by(ActionRequest.created_at.desc())
        .limit(100)
        .all()
    )
    return jsonify({'success': True, 'requests': [r.to_dict() for r in rows]})


@api_bp.route('/requests', methods=['GET'])
@login_required
def list_action_requests():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    q = ActionRequest.query
    status = request.args.get('status')
    if status in ('pending', 'approved', 'rejected'):
        q = q.filter_by(status=status)
    rows = q.order_by(ActionRequest.created_at.desc()).limit(200).all()
    pending = ActionRequest.query.filter_by(status='pending').count()
    return jsonify({'success': True, 'requests': [r.to_dict() for r in rows], 'pending': pending})


@api_bp.route('/requests/<int:request_id>/<action>', methods=['POST'])
@login_required
def resolve_action_request(request_id, action):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Solo un administrador puede resolver solicitudes.'}), 403
    if action not in ('approve', 'reject'):
        return jsonify({'success': False, 'error': 'Acción inválida'}), 404
    req = db.session.get(ActionRequest, request_id)
    if not req:
        return jsonify({'success': False, 'error': 'Solicitud no encontrada'}), 404
    data = request.get_json(silent=True) or {}
    try:
        req = resolve(req, current_user, action == 'approve', data.get('note'), data.get('payload'))
    except RequestError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'request': req.to_dict()})


@api_bp.route('/requests/options', methods=['GET'])
@login_required
def action_request_options():
    """Lo que el terapeuta necesita para llenar los formularios: sus pacientes activos, sus grupos y las sedes."""
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    from app.models.patient_group import PatientGroup
    from app.models.user import Sede

    patients = [
        {'id': p.id, 'username': p.username or p.email}
        for p in current_user.associated_patients.filter_by(role='jugador').order_by('username').all()
        if p.is_active is not False and (p.account_status or 'active') in ('active', 'debtor')
    ]
    groups = [
        {
            'id': g.id,
            'name': g.name,
            'member_count': len(g.members),
            'start_time': g.start_time,
            'end_time': g.end_time,
        }
        for g in PatientGroup.query.filter_by(therapist_id=current_user.id, is_active=True).order_by(PatientGroup.name)
    ]
    sedes = [
        {'id': s.id, 'name': s.name}
        for s in Sede.query.filter(db.or_(Sede.is_active.is_(True), Sede.is_active.is_(None))).order_by(Sede.name)
    ]
    return jsonify({'success': True, 'patients': patients, 'groups': groups, 'sedes': sedes})
