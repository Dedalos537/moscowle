"""
Example Flask Routes for K-Means Segmentation
Integration examples showing how to use run_k_means_segmentation in API endpoints

Author: AI Assistant
Date: December 3, 2025
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models import SessionMetrics
from app.services.ai_service import run_k_means_segmentation, AIServiceError
import logging

logger = logging.getLogger(__name__)

# Create blueprint
clustering_bp = Blueprint('clustering', __name__, url_prefix='/api/clustering')


@clustering_bp.route('/run', methods=['POST'])
@jwt_required()
def run_clustering():
    """
    Execute K-Means clustering on session metrics data
    
    POST /api/clustering/run
    
    Request Body (optional):
    {
        "k": 3  # number of clusters (default: 3)
    }
    
    Response:
    {
        "status": "success",
        "message": "Clustering completed. X sessions updated.",
        "data": {
            "k_clusters": 3,
            "total_sessions": 100,
            "updated_sessions": 100,
            "centroids": {...},
            "clusters_summary": {...},
            ...
        }
    }
    """
    try:
        # Get parameters
        data = request.get_json() or {}
        k = data.get('k', 3)
        
        # Validate k parameter
        if not isinstance(k, int) or k < 2 or k > 10:
            return jsonify({
                'status': 'error',
                'message': 'Invalid k parameter. Must be integer between 2 and 10'
            }), 400
        
        logger.info(f"Running K-Means clustering with k={k}")
        
        # Execute clustering
        result = run_k_means_segmentation(db, SessionMetrics, k=k)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': f"Clustering completed. {result['updated_sessions']} sessions updated.",
                'data': result
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'Clustering failed'),
                'data': result
            }), 400
    
    except AIServiceError as e:
        logger.error(f"AI Service Error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'AI Service Error: {str(e)}'
        }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500


@clustering_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_clustering_summary():
    """
    Get clustering summary and statistics
    
    GET /api/clustering/summary
    
    Response:
    {
        "status": "success",
        "clusters": {...},
        "centroids": {...},
        "quality_metrics": {
            "inertia": 123.45,
            "silhouette_score": 0.678
        },
        "timestamp": "2025-12-03T10:30:00.000000"
    }
    """
    try:
        logger.info("Retrieving clustering summary")
        
        # Get current clustering
        result = run_k_means_segmentation(db, SessionMetrics)
        
        if result['success']:
            summary = {
                'status': 'success',
                'clusters': result['clusters_summary'],
                'centroids': result['centroids'],
                'quality_metrics': {
                    'inertia': result['inertia'],
                    'silhouette_score': result['silhouette_score'],
                    'total_sessions': result['total_sessions']
                },
                'timestamp': result['timestamp']
            }
            return jsonify(summary), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'Failed to get clustering summary')
            }), 400
    
    except Exception as e:
        logger.error(f"Error getting clustering summary: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500


@clustering_bp.route('/centroids', methods=['GET'])
@jwt_required()
def get_centroids():
    """
    Get cluster centroids
    
    GET /api/clustering/centroids
    
    Response:
    {
        "status": "success",
        "centroids": {
            "cluster_0": {
                "accuracy_rate": 95.2,
                "average_time": 10.5,
                "label": "Avanzados"
            },
            ...
        }
    }
    """
    try:
        result = run_k_means_segmentation(db, SessionMetrics)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'centroids': result['centroids']
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error')
            }), 400
    
    except Exception as e:
        logger.error(f"Error getting centroids: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@clustering_bp.route('/cluster/<int:cluster_id>/sessions', methods=['GET'])
@jwt_required()
def get_cluster_sessions(cluster_id):
    """
    Get all sessions in a specific cluster
    
    GET /api/clustering/cluster/{cluster_id}/sessions
    
    Response:
    {
        "status": "success",
        "cluster_id": 0,
        "cluster_label": "Avanzados",
        "sessions_count": 25,
        "sessions": [...]
    }
    """
    try:
        # Validate cluster_id
        if cluster_id not in [0, 1, 2]:
            return jsonify({
                'status': 'error',
                'message': 'Invalid cluster_id. Must be 0, 1, or 2'
            }), 400
        
        # Get clustering result for labels
        result = run_k_means_segmentation(db, SessionMetrics)
        
        if not result['success']:
            return jsonify({
                'status': 'error',
                'message': result.get('error')
            }), 400
        
        # Get sessions in cluster
        sessions = db.session.query(SessionMetrics).filter(
            SessionMetrics.cluster_id == cluster_id
        ).all()
        
        cluster_label = result['cluster_labels'].get(cluster_id, 'Unknown')
        
        return jsonify({
            'status': 'success',
            'cluster_id': cluster_id,
            'cluster_label': cluster_label,
            'sessions_count': len(sessions),
            'sessions': [session.to_dict() for session in sessions]
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting cluster sessions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@clustering_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_clustering_statistics():
    """
    Get detailed clustering statistics
    
    GET /api/clustering/statistics
    
    Response:
    {
        "status": "success",
        "total_sessions": 100,
        "clusters": {
            "cluster_0": {
                "label": "Avanzados",
                "size": 25,
                "percentage": 25.0,
                "accuracy_stats": {...},
                "time_stats": {...}
            },
            ...
        }
    }
    """
    try:
        result = run_k_means_segmentation(db, SessionMetrics)
        
        if result['success']:
            statistics = {
                'status': 'success',
                'total_sessions': result['total_sessions'],
                'k_clusters': result['k_clusters'],
                'quality': {
                    'inertia': result['inertia'],
                    'silhouette_score': result['silhouette_score']
                },
                'clusters': {}
            }
            
            for cluster_id, label in result['cluster_labels'].items():
                summary = result['clusters_summary'].get(f'cluster_{cluster_id}', {})
                statistics['clusters'][f'cluster_{cluster_id}'] = {
                    'label': label,
                    'size': summary.get('size', 0),
                    'percentage': summary.get('percentage', 0),
                    'accuracy_statistics': summary.get('accuracy_rate', {}),
                    'time_statistics': summary.get('average_time', {})
                }
            
            return jsonify(statistics), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error')
            }), 400
    
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@clustering_bp.route('/export', methods=['GET'])
@jwt_required()
def export_clustering_results():
    """
    Export clustering results as JSON
    
    GET /api/clustering/export
    
    Response: Complete clustering result object (as JSON)
    """
    try:
        result = run_k_means_segmentation(db, SessionMetrics)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'export_timestamp': result['timestamp'],
                'data': result
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error')
            }), 400
    
    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Register blueprint in your Flask app
def register_clustering_routes(app):
    """
    Register clustering routes to Flask app
    
    Usage in app/__init__.py:
    from routes.clustering_routes import register_clustering_routes
    
    def create_app():
        app = Flask(__name__)
        ...
        register_clustering_routes(app)
        return app
    """
    app.register_blueprint(clustering_bp)
    logger.info("Clustering routes registered")
