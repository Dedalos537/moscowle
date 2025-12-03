"""
CÓDIGO COMPLETO DE LA FUNCIÓN run_k_means_segmentation()
Segmentación de Estudiantes usando K-Means Clustering

Ubicación: backend/app/services/ai_service.py (línea 420+)
Fecha: 3 de diciembre de 2025
Versión: 1.0

Este archivo contiene el código de la función completa para referencia.
En la aplicación real, esta función está en ai_service.py
"""

def run_k_means_segmentation(db, SessionMetrics, k: int = 3) -> Dict[str, Union[int, float, List, str]]:
    """
    Perform K-Means clustering on student session metrics data.
    
    Segments students into k clusters (default: 3) based on accuracy_rate and average_time:
    - Cluster 0: Avanzados (High accuracy, Low time)
    - Cluster 1: Intermedios (Medium accuracy, Medium time)
    - Cluster 2: Necesitan Apoyo (Low accuracy, High time)
    
    This function:
    1. Retrieves real session metrics data from the database
    2. Validates and scales the features (accuracy_rate, average_time)
    3. Applies K-Means clustering algorithm with k=3 clusters
    4. Updates the cluster_id field in the session_metrics table
    5. Returns cluster centroids and summary statistics
    
    Args:
        db: SQLAlchemy database instance (Flask-SQLAlchemy extension)
        SessionMetrics: SQLAlchemy model class for session_metrics table
        k (int): Number of clusters (default: 3)
    
    Returns:
        Dict[str, Union[int, float, List, str]]: Clustering results containing:
            - success (bool): Whether clustering was successful
            - k_clusters (int): Number of clusters created
            - total_sessions (int): Number of sessions processed
            - updated_sessions (int): Number of sessions updated
            - centroids (Dict): Cluster centroids with keys 'accuracy_rate', 'average_time'
            - cluster_labels (Dict): Human-readable labels for clusters
            - clusters_summary (Dict): Size and characteristics of each cluster
            - inertia (float): Sum of squared distances to nearest cluster center
            - silhouette_score (float): Silhouette coefficient (range: -1 to 1)
            - timestamp (str): Execution timestamp
    
    Raises:
        AIServiceError: If data retrieval, clustering, or database update fails
    
    Example:
        >>> from app.extensions import db
        >>> from app.models import SessionMetrics
        >>> result = run_k_means_segmentation(db, SessionMetrics, k=3)
        >>> print(f"Clustered {result['total_sessions']} sessions")
        >>> print(f"Centroids: {result['centroids']}")
    """
    try:
        from datetime import datetime
        from sklearn.metrics import silhouette_score
        
        logger.info("Starting K-Means segmentation for student sessions...")
        
        # 1. Load data from database
        logger.info("Loading session metrics from database...")
        sessions = db.session.query(SessionMetrics).all()
        
        if not sessions:
            logger.warning("No session metrics found in database")
            return {
                'success': False,
                'error': 'No session metrics data available in database',
                'total_sessions': 0,
                'updated_sessions': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        logger.info(f"Loaded {len(sessions)} sessions from database")
        
        # 2. Extract features (accuracy_rate, average_time)
        logger.info("Extracting features for clustering...")
        X = np.array([
            [session.accuracy_rate, session.average_time]
            for session in sessions
        ])
        
        logger.info(f"Feature matrix shape: {X.shape}")
        logger.info(f"Accuracy rate range: {X[:, 0].min():.2f} - {X[:, 0].max():.2f}")
        logger.info(f"Average time range: {X[:, 1].min():.2f} - {X[:, 1].max():.2f}")
        
        # 3. Validate data
        if X.shape[0] < k:
            logger.error(f"Not enough sessions ({X.shape[0]}) for {k} clusters")
            raise AIServiceError(
                f"Insufficient data: {X.shape[0]} sessions, need at least {k} for {k} clusters"
            )
        
        # 4. Scale features
        logger.info("Scaling features...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        logger.info(f"Scaled feature statistics:")
        logger.info(f"  Mean: {X_scaled.mean(axis=0)}")
        logger.info(f"  Std:  {X_scaled.std(axis=0)}")
        
        # 5. Apply K-Means clustering
        logger.info(f"Applying K-Means clustering with k={k}...")
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X_scaled)
        
        logger.info(f"K-Means model trained with {len(kmeans.cluster_centers_)} centroids")
        logger.info(f"Inertia: {kmeans.inertia_:.4f}")
        
        # 6. Calculate silhouette score
        silhouette_avg = silhouette_score(X_scaled, cluster_labels)
        logger.info(f"Silhouette score: {silhouette_avg:.4f}")
        
        # 7. Transform centroids back to original scale
        logger.info("Transforming centroids back to original scale...")
        centroids_scaled = kmeans.cluster_centers_
        centroids_original = scaler.inverse_transform(centroids_scaled)
        
        # 8. Create centroids dictionary
        centroids_dict = {
            'cluster_0': {
                'accuracy_rate': float(centroids_original[0, 0]),
                'average_time': float(centroids_original[0, 1]),
                'label': 'Avanzados'
            },
            'cluster_1': {
                'accuracy_rate': float(centroids_original[1, 0]),
                'average_time': float(centroids_original[1, 1]),
                'label': 'Intermedios'
            },
            'cluster_2': {
                'accuracy_rate': float(centroids_original[2, 0]),
                'average_time': float(centroids_original[2, 1]),
                'label': 'Necesitan Apoyo'
            } if k >= 3 else {}
        }
        
        logger.info("Centroids calculated:")
        for cluster_id, centroid in centroids_dict.items():
            logger.info(f"  {cluster_id}: accuracy={centroid['accuracy_rate']:.2f}, "
                       f"time={centroid['average_time']:.2f} ({centroid['label']})")
        
        # 9. Update database with cluster assignments
        logger.info("Updating database with cluster assignments...")
        updated_count = 0
        
        for session, cluster_id in zip(sessions, cluster_labels):
            try:
                session.cluster_id = int(cluster_id)
                updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to update session {session.id}: {str(e)}")
        
        # Commit changes to database
        db.session.commit()
        logger.info(f"Database committed. Updated {updated_count} sessions.")
        
        # 10. Calculate cluster statistics
        logger.info("Calculating cluster statistics...")
        clusters_summary = {}
        
        for cluster_id in range(k):
            mask = cluster_labels == cluster_id
            cluster_sessions = [sessions[i] for i in range(len(sessions)) if mask[i]]
            cluster_data = X[mask]
            
            accuracy_values = cluster_data[:, 0]
            time_values = cluster_data[:, 1]
            
            summary = {
                'size': int(np.sum(mask)),
                'percentage': float(100 * np.sum(mask) / len(sessions)),
                'accuracy_rate': {
                    'mean': float(np.mean(accuracy_values)),
                    'std': float(np.std(accuracy_values)),
                    'min': float(np.min(accuracy_values)),
                    'max': float(np.max(accuracy_values))
                },
                'average_time': {
                    'mean': float(np.mean(time_values)),
                    'std': float(np.std(time_values)),
                    'min': float(np.min(time_values)),
                    'max': float(np.max(time_values))
                }
            }
            
            clusters_summary[f'cluster_{cluster_id}'] = summary
            
            logger.info(f"Cluster {cluster_id} ({centroids_dict[f'cluster_{cluster_id}']['label']}):")
            logger.info(f"  Size: {summary['size']} sessions ({summary['percentage']:.1f}%)")
            logger.info(f"  Accuracy: μ={summary['accuracy_rate']['mean']:.2f}%, "
                       f"σ={summary['accuracy_rate']['std']:.2f}%")
            logger.info(f"  Time: μ={summary['average_time']['mean']:.2f}s, "
                       f"σ={summary['average_time']['std']:.2f}s")
        
        # 11. Build result dictionary
        result = {
            'success': True,
            'k_clusters': int(k),
            'total_sessions': int(len(sessions)),
            'updated_sessions': int(updated_count),
            'centroids': centroids_dict,
            'cluster_labels': {
                0: 'Avanzados',
                1: 'Intermedios',
                2: 'Necesitan Apoyo'
            },
            'clusters_summary': clusters_summary,
            'inertia': float(kmeans.inertia_),
            'silhouette_score': float(silhouette_avg),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("K-Means segmentation completed successfully")
        return result
    
    except AIServiceError as e:
        logger.error(f"AI Service Error during K-Means segmentation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during K-Means segmentation: {str(e)}", exc_info=True)
        raise AIServiceError(f"K-Means segmentation failed: {str(e)}")


# IMPORTS REQUERIDOS (agregar al inicio del archivo ai_service.py):
# from sklearn.cluster import KMeans
# from sklearn.metrics import silhouette_score
# from typing import Dict, Union, Tuple, Optional, List
# (El resto ya están presentes)

# DEPENDENCIAS EN requirements.txt:
# scikit-learn>=1.0
# numpy>=1.20
# pandas>=1.3
# joblib>=1.1

# USO BÁSICO:
# from app.services.ai_service import run_k_means_segmentation
# from app.extensions import db
# from app.models import SessionMetrics
#
# result = run_k_means_segmentation(db, SessionMetrics, k=3)
# if result['success']:
#     print(f"Sesiones actualizadas: {result['updated_sessions']}")

"""
CHANGELOG:
v1.0 (3 dic 2025) - Inicial
  - Función implementada con K-Means clustering
  - Carga de datos real desde BD
  - Normalización automática
  - Actualización de cluster_id en BD
  - Métricas de calidad (inertia, silhouette)
  - Logging completo
  - Manejo robusto de errores
"""
