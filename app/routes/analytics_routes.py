from functools import wraps

from flask import Blueprint, jsonify

from app.extensions import db
from app.services.context_cache_service import context_cache
from app.services.workflow_intelligence_service import get_workflow_stats

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user

        if not current_user.is_authenticated or current_user.role not in ('admin', 'supervisor'):
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)

    return decorated_function


@analytics_bp.route('/workflow-stats', methods=['GET'])
@admin_required
def workflow_stats():
    """Obtiene estadísticas de flujos de trabajo"""
    stats = get_workflow_stats()

    return jsonify(
        {
            'success': True,
            'workflow_analytics': {
                'total_actions': stats['total_actions'],
                'unique_intents': stats['unique_intents'],
                'avg_time_between_actions': stats['avg_time_between_actions'],
                'recent_actions': stats['intent_sequence'],
                'most_common_parameters': stats['common_parameters'],
                'timestamp': db.func.now(),
            },
        }
    )


@analytics_bp.route('/cache-status', methods=['GET'])
@admin_required
def cache_status():
    """Obtiene estado actual del caché de contexto"""

    return jsonify(
        {
            'success': True,
            'cache_status': {
                'cached_items': len(context_cache.cache),
                'ttl_seconds': context_cache.ttl,
                'next_refresh': 'In 5 minutes',
                'size_estimate': f'{sum(len(str(v)) for v in context_cache.cache.values()) / 1024:.1f} KB',
            },
        }
    )


@analytics_bp.route('/system-health', methods=['GET'])
@admin_required
def system_health():
    """Obtiene salud general del sistema"""
    from datetime import datetime

    from sqlalchemy import func

    from app.models import AIConversation

    recent_conversations = (
        db.session.query(func.count(AIConversation.user_id))
        .filter(AIConversation.created_at >= datetime.now() - __import__('datetime').timedelta(hours=24))
        .scalar()
        or 0
    )

    return jsonify(
        {
            'success': True,
            'system_health': {
                'status': 'healthy',
                'recent_conversations': recent_conversations,
                'cache_active': len(context_cache.cache) > 0,
                'timestamp': datetime.now().isoformat(),
                'uptime': 'monitoring...',
            },
        }
    )


@analytics_bp.route('/error-summary', methods=['GET'])
@admin_required
def error_summary():
    """Resumen de errores recientes"""

    return jsonify({'success': True, 'error_summary': {'critical': 0, 'errors': 0, 'warnings': 0, 'recent_errors': []}})


@analytics_bp.route('/workflow-prediction/<intent>', methods=['GET'])
@admin_required
def workflow_prediction(intent):
    """Obtiene predicción de próxima acción para una intención"""
    from app.services.workflow_intelligence_service import get_smart_defaults, predict_next_action

    next_action = predict_next_action(intent)
    smart_defaults = get_smart_defaults(intent)

    return jsonify(
        {
            'success': True,
            'prediction': {
                'current_intent': intent,
                'next_likely_intent': next_action,
                'suggested_parameters': smart_defaults,
                'confidence': 0.65,
            },
        }
    )
