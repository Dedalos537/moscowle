from flask import Blueprint, request

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository
from app.utils.api_helpers import api_response

async_api_bp = Blueprint('async_api', __name__, url_prefix='/api/async')


@async_api_bp.route('/users/active', methods=['GET'])
def get_active_users():
    try:
        skip = request.args.get('skip', default=0, type=int)
        limit = request.args.get('limit', default=20, type=int)

        therapists = UserRepository.get_active_therapists(skip=skip, limit=limit)

        data = []
        for t in therapists:
            sedes = [{'id': s.id, 'name': s.name} for s in t.assigned_sedes]
            data.append({'id': t.id, 'username': t.username, 'email': t.email, 'role': t.role, 'sedes': sedes})

        return api_response(success=True, data=data, error=None, status=200)

    except Exception as e:
        return api_response(success=False, data=None, error=str(e), status=500)


@async_api_bp.route('/appointments/upcoming', methods=['GET'])
def get_upcoming_appointments():
    try:
        user_id = request.args.get('user_id', type=int)
        role = request.args.get('role', default='terapista', type=str)
        limit = request.args.get('limit', default=10, type=int)

        if not user_id:
            return api_response(success=False, data=None, error='User ID required', status=400)

        appointments = AppointmentRepository.get_upcoming_for_user(user_id=user_id, role=role, limit=limit)

        data = [
            {'id': a.id, 'title': a.title, 'start': a.start_time.isoformat(), 'status': a.status} for a in appointments
        ]

        return api_response(success=True, data=data, error=None, status=200)

    except Exception as e:
        return api_response(success=False, data=None, error=str(e), status=500)


@async_api_bp.route('/metrics/user/<int:user_id>', methods=['GET'])
def get_user_metrics(user_id):
    try:
        metrics = MetricsRepository.get_by_user(user_id=user_id, limit=20)
        avg_score = MetricsRepository.get_average_scores(user_id=user_id)

        data = {
            'average_accuracy': round(avg_score, 2),
            'recent_sessions': [
                {'id': m.id, 'game': m.game_name, 'accuracy': m.accurracy, 'date': m.date.isoformat()} for m in metrics
            ],
        }

        return api_response(success=True, data=data, error=None, status=200)
    except Exception as e:
        return api_response(success=False, data=None, error=str(e), status=500)
