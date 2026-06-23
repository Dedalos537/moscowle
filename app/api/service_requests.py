from flask import Blueprint, jsonify, request

from app.auth_compat import g, login_required
from app.repositories.service_request_repo import service_request_repo
from app.utils.api_helpers import api_response

api_sr = Blueprint('api_service_requests', __name__, url_prefix='/api/service-requests')


@api_sr.route('', methods=['GET'])
@login_required
def list_requests():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    user = g.current_user

    if user.role == 'admin':
        pagination = service_request_repo.paginate(page=page, per_page=per_page)
    else:
        pagination = service_request_repo.find_by_requester(user.id, page=page, per_page=per_page)

    return jsonify({
        "success": True,
        "data": [r.to_dict() for r in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


@api_sr.route('', methods=['POST'])
@login_required
def create_request():
    data = request.get_json(silent=True) or {}
    required = ['category', 'title']
    for field in required:
        if not data.get(field):
            return api_response(False, error={"message": f"{field} is required"}, status=400)

    record = service_request_repo.create(
        requester_id=g.current_user.id,
        category=data['category'],
        title=data['title'],
        description=data.get('description'),
        priority=data.get('priority', 'normal'),
    )
    return api_response(True, data=record.to_dict(), status=201)


@api_sr.route('/<int:request_id>', methods=['GET'])
@login_required
def get_request(request_id):
    record = service_request_repo.get_by_id_or_404(request_id)
    user = g.current_user
    if user.role != 'admin' and record.requester_id != user.id:
        return api_response(False, error={"message": "Forbidden"}, status=403)
    return api_response(True, data=record.to_dict())


@api_sr.route('/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_request(request_id):
    if g.current_user.role != 'admin':
        return api_response(False, error={"message": "Forbidden"}, status=403)
    data = request.get_json(silent=True) or {}
    record = service_request_repo.approve(request_id, g.current_user.id, data.get('notes'))
    return api_response(True, data=record.to_dict())


@api_sr.route('/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_request(request_id):
    if g.current_user.role != 'admin':
        return api_response(False, error={"message": "Forbidden"}, status=403)
    data = request.get_json(silent=True) or {}
    record = service_request_repo.reject(request_id, g.current_user.id, data.get('notes'))
    return api_response(True, data=record.to_dict())
