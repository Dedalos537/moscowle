"""
AI Routes Blueprint
REST API endpoints for AI-powered recommendations in Moscowle

Endpoints:
    POST /api/ai/recommend_level        - Get AI recommendation and save metric
    GET /api/ai/status                  - Check model and service status
    GET /api/ai/patient/<patient_id>/recommendations  - Get recommendation history

Author: AI Assistant
Date: December 3, 2025
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.patient import Patient
from ..models.session_metrics import SessionMetrics
from ..schemas.ai_schemas import (
    RecommendLevelRequestSchema,
    RecommendLevelResponseSchema,
    AIStatusSchema
)
from ..services.ai_service import (
    predict_next_level,
    get_model_info,
    AIServiceError
)

# Create blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# Setup logging
logger = logging.getLogger(__name__)

# Initialize schemas
recommend_request_schema = RecommendLevelRequestSchema()
recommend_response_schema = RecommendLevelResponseSchema()
ai_status_schema = AIStatusSchema()


# Prediction level mappings
LEVEL_MESSAGES = {
    0: 'Mantener Nivel',
    1: 'Avanzar Nivel',
    2: 'Retroceder Nivel'
}

LEVEL_DESCRIPTIONS = {
    0: 'Your current level is suitable. Keep practicing!',
    1: 'Great job! You are ready to advance to the next level.',
    2: 'Let\'s practice more at this level to build confidence.'
}


@ai_bp.route('/recommend_level', methods=['POST'])
@jwt_required()
def recommend_level():
    """
    Get AI-powered level recommendation and save session metric.
    
    This endpoint:
    1. Receives student metrics
    2. Validates input with Marshmallow schema
    3. Checks patient exists in database
    4. Calls predict_next_level() from ai_service
    5. Saves SessionMetrics with prediction
    6. Returns recommendation with confidence
    
    Required JSON payload:
    {
        "patient_id": 1,
        "game_name": "Memoria Visual",
        "accuracy_rate": 85.5,
        "average_time": 45.3,
        "failed_attempts": 5,
        "previous_level": 2
    }
    
    Returns:
    {
        "success": true,
        "recommended_level": 1,
        "message": "Avanzar Nivel",
        "confidence": 0.9978,
        "probabilities": {
            "Mantener": 0.0000,
            "Avanzar": 0.9978,
            "Retroceder": 0.0022
        },
        "session_metric_id": 42,
        "student_message": "Great job! You are ready to advance..."
    }
    
    Status Codes:
        201: Successfully created metric and got recommendation
        400: Validation error (invalid input)
        404: Patient not found
        500: Internal server error
    """
    
    try:
        # Get current user (patient or therapist)
        current_user = get_jwt_identity()
        logger.info(f"Recommendation request from user: {current_user}")
        
        # Get JSON payload
        data = request.get_json() or {}
        logger.info(f"Request data: {data}")
        
        # Validate request with Marshmallow schema
        errors = recommend_request_schema.validate(data)
        if errors:
            logger.warning(f"Validation errors: {errors}")
            return jsonify({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }), 400
        
        # Extract validated data
        patient_id = data['patient_id']
        game_name = data['game_name']
        accuracy_rate = data['accuracy_rate']
        average_time = data['average_time']
        failed_attempts = data['failed_attempts']
        previous_level = data['previous_level']
        
        # Check if patient exists
        patient = Patient.query.get(patient_id)
        if not patient:
            logger.error(f"Patient {patient_id} not found")
            return jsonify({
                'success': False,
                'message': f'Patient with ID {patient_id} not found'
            }), 404
        
        logger.info(f"Patient found: {patient.email}")
        
        # Prepare metrics for AI prediction
        metrics_for_prediction = {
            'Tasa_Aciertos': accuracy_rate,
            'Tiempo_Promedio': average_time,
            'Intentos_Fallidos': failed_attempts,
            'Nivel_Actual': previous_level
        }
        
        # Get AI prediction
        logger.info(f"Calling AI service with metrics: {metrics_for_prediction}")
        
        try:
            ai_result = predict_next_level(metrics_for_prediction)
            predicted_level = ai_result['prediction']
            confidence = ai_result['confidence']
            probabilities = ai_result['probabilities']
            
            logger.info(f"AI prediction: {LEVEL_MESSAGES[predicted_level]} "
                       f"(confidence: {confidence:.2%})")
        
        except AIServiceError as e:
            logger.error(f"AI prediction failed: {str(e)}")
            # Use null prediction if AI fails - metric will still be saved
            predicted_level = data.get('predicted_next_level')
            confidence = None
            probabilities = None
            ai_result = None
        
        # Create SessionMetrics record
        session_metric = SessionMetrics(
            patient_id=patient_id,
            game_name=game_name,
            accuracy_rate=accuracy_rate,
            average_time=average_time,
            failed_attempts=failed_attempts,
            previous_level=previous_level,
            predicted_next_level=predicted_level or data.get('predicted_next_level'),
            cluster_id=data.get('cluster_id')
        )
        
        # Save to database
        db.session.add(session_metric)
        db.session.commit()
        
        logger.info(f"SessionMetrics saved with ID: {session_metric.id}")
        
        # Build response
        response_data = {
            'success': True,
            'recommended_level': predicted_level or 0,
            'message': LEVEL_MESSAGES.get(predicted_level, 'Sin recomendación'),
            'session_metric_id': session_metric.id,
            'student_message': LEVEL_DESCRIPTIONS.get(predicted_level, 'Keep playing!')
        }
        
        # Add AI confidence info if available
        if confidence is not None:
            response_data['confidence'] = confidence
            response_data['probabilities'] = probabilities
            response_data['ai_available'] = True
        else:
            response_data['ai_available'] = False
            response_data['confidence'] = None
        
        # Add student info
        response_data['patient'] = {
            'id': patient.id,
            'email': patient.email
        }
        
        logger.info(f"Response: {response_data}")
        
        return jsonify(response_data), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500


@ai_bp.route('/status', methods=['GET'])
@jwt_required()
def get_ai_status():
    """
    Get AI service and model status.
    
    Returns information about the trained SVM model:
    - Whether model is loaded
    - Model performance metrics
    - File sizes
    - Overall service status
    
    Status Codes:
        200: Status retrieved successfully
        500: Error retrieving status
    """
    
    try:
        logger.info("Checking AI service status")
        
        model_info = get_model_info()
        
        if model_info:
            status_response = {
                'status': 'Ready',
                'model_loaded': True,
                'model_size_mb': model_info['model_size_mb'],
                'scaler_loaded': model_info['scaler_exists'],
                'total_size_mb': model_info['total_size_mb'],
                'message': 'SVM model is ready for predictions'
            }
        else:
            status_response = {
                'status': 'Warning',
                'model_loaded': False,
                'message': 'Model not found. Will be trained on first use.'
            }
        
        logger.info(f"Status: {status_response['status']}")
        return jsonify(status_response), 200
    
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return jsonify({
            'status': 'Error',
            'message': f'Error retrieving status: {str(e)}'
        }), 500


@ai_bp.route('/patient/<int:patient_id>/recommendations', methods=['GET'])
@jwt_required()
def get_patient_recommendations(patient_id):
    """
    Get AI recommendations history for a patient.
    
    Returns all SessionMetrics with AI predictions for a specific patient.
    
    Query Parameters:
        - limit (int, default=50): Max records to return
        - offset (int, default=0): Pagination offset
        - game_name (str, optional): Filter by game name
    
    Returns list of recommendations with dates and confidence scores.
    
    Status Codes:
        200: Recommendations retrieved
        404: Patient not found
        500: Server error
    """
    
    try:
        # Check if patient exists
        patient = Patient.query.get(patient_id)
        if not patient:
            logger.warning(f"Patient {patient_id} not found")
            return jsonify({
                'message': f'Patient with ID {patient_id} not found'
            }), 404
        
        # Get query parameters
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        game_name = request.args.get('game_name', type=str)
        
        # Query SessionMetrics
        query = SessionMetrics.query.filter_by(patient_id=patient_id)
        
        if game_name:
            query = query.filter(SessionMetrics.game_name.ilike(f"%{game_name}%"))
        
        # Order by most recent first
        metrics = query.order_by(
            SessionMetrics.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        total = query.count()
        
        # Build recommendations list
        recommendations = []
        for metric in metrics:
            recommendation = {
                'id': metric.id,
                'game_name': metric.game_name,
                'accuracy_rate': metric.accuracy_rate,
                'average_time': metric.average_time,
                'failed_attempts': metric.failed_attempts,
                'previous_level': metric.previous_level,
                'predicted_next_level': metric.predicted_next_level,
                'message': LEVEL_MESSAGES.get(metric.predicted_next_level, 'N/A'),
                'created_at': metric.created_at.isoformat()
            }
            recommendations.append(recommendation)
        
        logger.info(f"Retrieved {len(recommendations)} recommendations for patient {patient_id}")
        
        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'patient_email': patient.email,
            'total': total,
            'limit': limit,
            'offset': offset,
            'recommendations': recommendations
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving recommendations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving recommendations: {str(e)}'
        }), 500


@ai_bp.route('/recommend_level', methods=['OPTIONS'])
def recommend_level_options():
    """
    Handle CORS preflight requests for recommend_level endpoint.
    """
    return '', 204


@ai_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    logger.error(f"Bad request: {str(error)}")
    return jsonify({
        'success': False,
        'message': 'Bad request',
        'error': str(error)
    }), 400


@ai_bp.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    return jsonify({
        'success': False,
        'message': 'Resource not found'
    }), 404


@ai_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    logger.error(f"Internal server error: {str(error)}")
    db.session.rollback()
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500
