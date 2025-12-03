from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.session_metrics import SessionMetrics
from ..schemas.session_metrics_schema import (
    SessionMetricsSchema,
    CreateSessionMetricsSchema,
    UpdateSessionMetricsSchema
)
from ..services.ai_service import predict_next_level, AIServiceError
from ..errors import NotFoundError, ValidationError

session_metrics_bp = Blueprint('session_metrics', __name__)

session_metrics_schema = SessionMetricsSchema()
session_metrics_list_schema = SessionMetricsSchema(many=True)
create_schema = CreateSessionMetricsSchema()
update_schema = UpdateSessionMetricsSchema()


@session_metrics_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_session_metrics():
    """Get all session metrics with optional filtering."""
    try:
        # Optional query parameters for filtering
        patient_id = request.args.get('patient_id', type=int)
        game_name = request.args.get('game_name', type=str)
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        query = SessionMetrics.query
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        if game_name:
            query = query.filter(SessionMetrics.game_name.ilike(f"%{game_name}%"))
        
        # Order by most recent first
        metrics = query.order_by(SessionMetrics.created_at.desc()).limit(limit).offset(offset).all()
        
        total = query.count()
        
        return jsonify({
            'data': session_metrics_list_schema.dump(metrics),
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'msg': f'Error retrieving session metrics: {str(e)}'}), 500


@session_metrics_bp.route('/<int:metric_id>', methods=['GET'])
@jwt_required()
def get_session_metric(metric_id):
    """Get a specific session metric by ID."""
    try:
        metric = SessionMetrics.query.get(metric_id)
        
        if not metric:
            return jsonify({'msg': 'Session metric not found'}), 404
        
        return jsonify(session_metrics_schema.dump(metric)), 200
        
    except Exception as e:
        return jsonify({'msg': f'Error retrieving session metric: {str(e)}'}), 500


@session_metrics_bp.route('/patient/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient_metrics(patient_id):
    """Get all metrics for a specific patient."""
    try:
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        metrics = SessionMetrics.query.filter_by(patient_id=patient_id).order_by(
            SessionMetrics.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        total = SessionMetrics.query.filter_by(patient_id=patient_id).count()
        
        return jsonify({
            'data': session_metrics_list_schema.dump(metrics),
            'total': total,
            'patient_id': patient_id,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'msg': f'Error retrieving patient metrics: {str(e)}'}), 500


@session_metrics_bp.route('/', methods=['POST'])
@jwt_required()
def create_session_metric():
    """Create a new session metric record and predict next level using AI."""
    try:
        data = request.get_json() or {}
        
        # Validate input
        errors = create_schema.validate(data)
        if errors:
            return jsonify({'msg': 'Validation failed', 'errors': errors}), 400
        
        # Check if patient exists
        from ..models.patient import Patient
        patient = Patient.query.get(data['patient_id'])
        if not patient:
            return jsonify({'msg': f"Patient with id {data['patient_id']} not found"}), 404
        
        # Prepare metrics for AI prediction
        metrics_for_prediction = {
            'Tasa_Aciertos': data['accuracy_rate'],
            'Tiempo_Promedio': data['average_time'],
            'Intentos_Fallidos': data['failed_attempts'],
            'Nivel_Actual': data['previous_level']
        }
        
        # Get AI prediction if not provided
        predicted_next_level = data.get('predicted_next_level')
        ai_prediction = None
        
        try:
            ai_result = predict_next_level(metrics_for_prediction)
            ai_prediction = ai_result['prediction']
            
            # Only use AI prediction if not explicitly provided
            if predicted_next_level is None:
                predicted_next_level = ai_prediction
        
        except AIServiceError as e:
            # Log AI error but continue - prediction is optional
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"AI prediction failed: {str(e)}. Using provided value or None.")
        
        # Create new metric
        metric = SessionMetrics(
            patient_id=data['patient_id'],
            game_name=data['game_name'],
            accuracy_rate=data['accuracy_rate'],
            average_time=data['average_time'],
            failed_attempts=data['failed_attempts'],
            previous_level=data['previous_level'],
            predicted_next_level=predicted_next_level,
            cluster_id=data.get('cluster_id')
        )
        
        db.session.add(metric)
        db.session.commit()
        
        # Build response with AI prediction info
        response = session_metrics_schema.dump(metric)
        if ai_prediction is not None:
            response['ai_prediction'] = {
                'predicted_level': ai_prediction,
                'used_for_prediction': predicted_next_level == ai_prediction,
                'all_probabilities': ai_result['probabilities'] if 'ai_result' in locals() else None
            }
        
        return jsonify(response), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': f'Error creating session metric: {str(e)}'}), 500


@session_metrics_bp.route('/<int:metric_id>', methods=['PUT'])
@jwt_required()
def update_session_metric(metric_id):
    """Update an existing session metric."""
    try:
        metric = SessionMetrics.query.get(metric_id)
        
        if not metric:
            return jsonify({'msg': 'Session metric not found'}), 404
        
        data = request.get_json() or {}
        
        # Validate input
        errors = update_schema.validate(data)
        if errors:
            return jsonify({'msg': 'Validation failed', 'errors': errors}), 400
        
        # Update fields if provided
        if 'game_name' in data:
            metric.game_name = data['game_name']
        if 'accuracy_rate' in data:
            metric.accuracy_rate = data['accuracy_rate']
        if 'average_time' in data:
            metric.average_time = data['average_time']
        if 'failed_attempts' in data:
            metric.failed_attempts = data['failed_attempts']
        if 'previous_level' in data:
            metric.previous_level = data['previous_level']
        if 'predicted_next_level' in data:
            metric.predicted_next_level = data['predicted_next_level']
        if 'cluster_id' in data:
            metric.cluster_id = data['cluster_id']
        
        db.session.commit()
        
        return jsonify(session_metrics_schema.dump(metric)), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': f'Error updating session metric: {str(e)}'}), 500


@session_metrics_bp.route('/<int:metric_id>', methods=['DELETE'])
@jwt_required()
def delete_session_metric(metric_id):
    """Delete a session metric record."""
    try:
        metric = SessionMetrics.query.get(metric_id)
        
        if not metric:
            return jsonify({'msg': 'Session metric not found'}), 404
        
        db.session.delete(metric)
        db.session.commit()
        
        return jsonify({'msg': 'Session metric deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': f'Error deleting session metric: {str(e)}'}), 500


@session_metrics_bp.route('/patient/<int:patient_id>/summary', methods=['GET'])
@jwt_required()
def get_patient_metrics_summary(patient_id):
    """
    Get aggregated metrics summary for a patient across all games.
    Useful for dashboards and ML preprocessing.
    """
    try:
        from sqlalchemy import func
        
        # Get all metrics for patient
        metrics = SessionMetrics.query.filter_by(patient_id=patient_id).all()
        
        if not metrics:
            return jsonify({'msg': 'No metrics found for this patient'}), 404
        
        # Aggregate by game
        game_summaries = {}
        for metric in metrics:
            if metric.game_name not in game_summaries:
                game_summaries[metric.game_name] = {
                    'count': 0,
                    'avg_accuracy': 0,
                    'avg_time': 0,
                    'total_failed': 0,
                    'levels': set(),
                    'clusters': set()
                }
            
            summary = game_summaries[metric.game_name]
            summary['count'] += 1
            summary['total_failed'] += metric.failed_attempts
            summary['levels'].add(metric.previous_level)
            if metric.cluster_id is not None:
                summary['clusters'].add(metric.cluster_id)
        
        # Calculate averages
        for game_name in game_summaries:
            metrics_for_game = [m for m in metrics if m.game_name == game_name]
            count = len(metrics_for_game)
            if count > 0:
                game_summaries[game_name]['avg_accuracy'] = sum(m.accuracy_rate for m in metrics_for_game) / count
                game_summaries[game_name]['avg_time'] = sum(m.average_time for m in metrics_for_game) / count
            
            # Convert sets to lists for JSON serialization
            game_summaries[game_name]['levels'] = list(game_summaries[game_name]['levels'])
            game_summaries[game_name]['clusters'] = list(game_summaries[game_name]['clusters'])
        
        return jsonify({
            'patient_id': patient_id,
            'total_sessions': len(metrics),
            'games_played': list(game_summaries.keys()),
            'summary': game_summaries
        }), 200
        
    except Exception as e:
        return jsonify({'msg': f'Error retrieving summary: {str(e)}'}), 500
