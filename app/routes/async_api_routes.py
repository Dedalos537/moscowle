from flask import Blueprint, jsonify, request
from app.dao.db_async import get_async_db
from app.dao.user_dao import UserDAO
from app.dao.appointment_dao import AppointmentDAO
from app.dao.session_metrics_dao import SessionMetricsDAO
from app.models import User, Appointment, SessionMetrics
from app.utils.async_utils import api_response
from datetime import datetime, timedelta
import asyncio

async_api_bp = Blueprint('async_api', __name__, url_prefix='/api/async')

@async_api_bp.route('/users/active', methods=['GET'])
async def get_active_users():
    """
    Fetch active therapists efficiently using Async DAO with selectinload.
    """
    try:
        skip = request.args.get('skip', default=0, type=int)
        limit = request.args.get('limit', default=20, type=int)

        async with get_async_db() as session:
            user_dao = UserDAO(User, session)
            # Fetch active therapists
            therapists = await user_dao.get_active_therapists(skip=skip, limit=limit)
            
            data = []
            for t in therapists:
                # Relationship loaded via selectinload, safe to access
                sedes = [{'id': s.id, 'name': s.name} for s in t.assigned_sedes]
                data.append({
                    'id': t.id,
                    'username': t.username,
                    'email': t.email,
                    'role': t.role,
                    'sedes': sedes
                })
                
            return api_response(data=data, message="Active therapists fetched successfully")
            
    except Exception as e:
        return api_response(message=str(e), status_code=500, success=False)

@async_api_bp.route('/appointments/upcoming', methods=['GET'])
async def get_upcoming_appointments():
    """
    Fetch upcoming appointments optimized with async.
    """
    try:
        user_id = request.args.get('user_id', type=int) # In real app, get from token/session
        role = request.args.get('role', default='terapista', type=str)
        limit = request.args.get('limit', default=10, type=int)
        
        if not user_id:
             return api_response(message="User ID required", status_code=400, success=False)

        async with get_async_db() as session:
            appt_dao = AppointmentDAO(Appointment, session)
            appointments = await appt_dao.get_upcoming_for_user(user_id=user_id, role=role, limit=limit)
            
            data = [{
                'id': a.id,
                'title': a.title,
                'start': a.start_time.isoformat(),
                'status': a.status
            } for a in appointments]
            
            return api_response(data=data)
            
    except Exception as e:
        return api_response(message=str(e), status_code=500, success=False)

@async_api_bp.route('/metrics/user/<int:user_id>', methods=['GET'])
async def get_user_metrics(user_id):
    """
    Fetch user metrics asynchronously.
    """
    try:
        async with get_async_db() as session:
            metrics_dao = SessionMetricsDAO(SessionMetrics, session)
            metrics = await metrics_dao.get_by_user(user_id=user_id, limit=20)
            avg_score = await metrics_dao.get_average_scores(user_id=user_id)
            
            data = {
                "average_accuracy": round(avg_score, 2),
                "recent_sessions": [{
                    "id": m.id,
                    "game": m.game_name,
                    "accuracy": m.accurracy,
                    "date": m.date.isoformat()
                } for m in metrics]
            }
            
            return api_response(data=data)
    except Exception as e:
        return api_response(message=str(e), status_code=500, success=False)
