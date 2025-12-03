"""
AI Service Module for Moscowle
Provides machine learning capabilities for predicting student progression levels
using Support Vector Machine (SVM) classification.

Author: AI Assistant
Date: December 3, 2025
Version: 1.0
"""

import os
import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.cluster import KMeans
import joblib
from typing import Dict, Union, Tuple, Optional, List
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Define model path
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'svm_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'feature_scaler.pkl')


class AIServiceError(Exception):
    """Custom exception for AI Service errors"""
    pass


def _ensure_model_dir():
    """Ensure the models directory exists"""
    os.makedirs(MODEL_DIR, exist_ok=True)


def _generate_synthetic_dataset(n_samples: int = 500) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Generate synthetic dataset for training the SVM model.
    
    Dataset characteristics:
    - 500 records with realistic educational metrics
    - Features: Tasa_Aciertos, Tiempo_Promedio, Intentos_Fallidos, Nivel_Actual
    - Target: Siguiente_Nivel (0: Mantener, 1: Avanzar, 2: Retroceder)
    
    Args:
        n_samples (int): Number of samples to generate (default: 500)
    
    Returns:
        Tuple[pd.DataFrame, np.ndarray]: Features DataFrame and target array
    """
    np.random.seed(42)
    
    # Generate realistic features
    data = {
        'Tasa_Aciertos': np.random.uniform(20, 100, n_samples),  # 20-100%
        'Tiempo_Promedio': np.random.uniform(5, 120, n_samples),  # 5-120 seconds
        'Intentos_Fallidos': np.random.randint(0, 50, n_samples),  # 0-50 failures
        'Nivel_Actual': np.random.randint(1, 4, n_samples),  # 1-3 levels
    }
    
    df = pd.DataFrame(data)
    
    # Generate target based on feature relationships
    # Logic:
    # - High accuracy (>80%) + Low time + Few failures -> Advance (1)
    # - Low accuracy (<40%) + High time + Many failures -> Regress (2)
    # - Otherwise -> Maintain (0)
    siguiente_nivel = np.zeros(n_samples, dtype=int)
    
    for i in range(n_samples):
        accuracy = df.loc[i, 'Tasa_Aciertos']
        time_avg = df.loc[i, 'Tiempo_Promedio']
        failed = df.loc[i, 'Intentos_Fallidos']
        
        # Calculate score
        advancement_score = (accuracy / 100) * 100 - (time_avg / 120) * 30 - (failed / 50) * 40
        
        if advancement_score > 40:
            siguiente_nivel[i] = 1  # Avanzar
        elif advancement_score < -20:
            siguiente_nivel[i] = 2  # Retroceder
        else:
            siguiente_nivel[i] = 0  # Mantener
    
    logger.info(f"Generated synthetic dataset with {n_samples} samples")
    logger.info(f"Target distribution - Mantener: {np.sum(siguiente_nivel==0)}, "
                f"Avanzar: {np.sum(siguiente_nivel==1)}, "
                f"Retroceder: {np.sum(siguiente_nivel==2)}")
    
    return df, siguiente_nivel


def train_svm_model(n_samples: int = 500, test_size: float = 0.2, 
                     random_state: int = 42) -> Dict[str, Union[float, int]]:
    """
    Train SVM model on synthetic dataset and save to disk.
    
    This function:
    1. Generates a synthetic dataset of educational metrics
    2. Splits data into training and testing sets
    3. Trains an SVM classifier with RBF kernel
    4. Evaluates model performance
    5. Serializes model and scaler to .pkl files
    
    Args:
        n_samples (int): Number of synthetic samples to generate (default: 500)
        test_size (float): Proportion of data for testing (default: 0.2)
        random_state (int): Random seed for reproducibility (default: 42)
    
    Returns:
        Dict[str, Union[float, int]]: Training results with metrics:
            - accuracy (float): Model accuracy on test set
            - precision (float): Precision score
            - recall (float): Recall score
            - f1 (float): F1 score
            - n_samples (int): Number of training samples
            - n_support_vectors (int): Number of support vectors
            - classes (list): Target classes
    
    Raises:
        AIServiceError: If model training fails
    
    Example:
        >>> results = train_svm_model(n_samples=500)
        >>> print(f"Model accuracy: {results['accuracy']:.3f}")
    """
    try:
        _ensure_model_dir()
        logger.info("Starting SVM model training...")
        
        # Generate synthetic dataset
        X, y = _generate_synthetic_dataset(n_samples)
        
        # Extract feature names for later use
        feature_names = X.columns.tolist()
        logger.info(f"Features: {feature_names}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=test_size, 
            random_state=random_state,
            stratify=y
        )
        logger.info(f"Training set: {len(X_train)} samples, Test set: {len(X_test)} samples")
        
        # Feature scaling (important for SVM)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train SVM model with RBF kernel
        logger.info("Training SVM classifier with RBF kernel...")
        svm_model = SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            random_state=random_state,
            probability=True  # Enable probability estimates
        )
        svm_model.fit(X_train_scaled, y_train)
        logger.info(f"SVM model trained with {len(svm_model.support_vectors_)} support vectors")
        
        # Make predictions
        y_pred = svm_model.predict(X_test_scaled)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        logger.info(f"Model Performance:")
        logger.info(f"  - Accuracy:  {accuracy:.4f}")
        logger.info(f"  - Precision: {precision:.4f}")
        logger.info(f"  - Recall:    {recall:.4f}")
        logger.info(f"  - F1 Score:  {f1:.4f}")
        
        # Save model to disk
        joblib.dump(svm_model, MODEL_PATH)
        logger.info(f"Model saved to {MODEL_PATH}")
        
        # Save scaler to disk
        joblib.dump(scaler, SCALER_PATH)
        logger.info(f"Scaler saved to {SCALER_PATH}")
        
        # Return training results
        results = {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'n_samples': len(X_train),
            'n_support_vectors': len(svm_model.support_vectors_),
            'classes': svm_model.classes_.tolist(),
            'feature_names': feature_names,
            'model_path': MODEL_PATH,
            'scaler_path': SCALER_PATH
        }
        
        logger.info("SVM model training completed successfully")
        return results
    
    except Exception as e:
        logger.error(f"Error training SVM model: {str(e)}")
        raise AIServiceError(f"Failed to train SVM model: {str(e)}")


def predict_next_level(metrics_data: Dict[str, Union[int, float]]) -> Dict[str, Union[int, float, str]]:
    """
    Predict the next progression level for a student based on performance metrics.
    
    This function:
    1. Loads the pre-trained SVM model and scaler from disk
    2. Validates input metrics
    3. Scales features using the training scaler
    4. Makes prediction with probability estimates
    5. Returns predicted level and confidence
    
    Args:
        metrics_data (Dict[str, Union[int, float]]): Dictionary containing:
            - Tasa_Aciertos (float): Accuracy rate (0-100)
            - Tiempo_Promedio (float): Average time per attempt (seconds)
            - Intentos_Fallidos (int): Number of failed attempts
            - Nivel_Actual (int): Current level (1-3)
    
    Returns:
        Dict[str, Union[int, float, str]]: Prediction result with:
            - prediction (int): 0 (Mantener), 1 (Avanzar), 2 (Retroceder)
            - prediction_label (str): Human-readable label
            - confidence (float): Probability confidence (0-1)
            - probabilities (Dict): Full probability distribution
            - input_metrics (Dict): Validated input metrics
    
    Raises:
        AIServiceError: If model is not found, input is invalid, or prediction fails
    
    Example:
        >>> metrics = {
        ...     'Tasa_Aciertos': 85.5,
        ...     'Tiempo_Promedio': 45.3,
        ...     'Intentos_Fallidos': 5,
        ...     'Nivel_Actual': 2
        ... }
        >>> result = predict_next_level(metrics)
        >>> print(f"Prediction: {result['prediction_label']} "
        ...       f"({result['confidence']:.2%})")
    """
    try:
        # Check if model exists
        if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
            logger.warning("Model or scaler not found. Training new model...")
            train_svm_model()
        
        # Load model and scaler
        logger.info("Loading SVM model and scaler...")
        svm_model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        
        # Validate input metrics
        required_fields = ['Tasa_Aciertos', 'Tiempo_Promedio', 'Intentos_Fallidos', 'Nivel_Actual']
        for field in required_fields:
            if field not in metrics_data:
                raise AIServiceError(f"Missing required field: {field}")
        
        # Extract and validate values
        tasa_aciertos = float(metrics_data['Tasa_Aciertos'])
        tiempo_promedio = float(metrics_data['Tiempo_Promedio'])
        intentos_fallidos = int(metrics_data['Intentos_Fallidos'])
        nivel_actual = int(metrics_data['Nivel_Actual'])
        
        # Validate ranges
        if not (0 <= tasa_aciertos <= 100):
            raise AIServiceError(f"Tasa_Aciertos must be between 0-100, got {tasa_aciertos}")
        if tiempo_promedio < 0:
            raise AIServiceError(f"Tiempo_Promedio must be non-negative, got {tiempo_promedio}")
        if intentos_fallidos < 0:
            raise AIServiceError(f"Intentos_Fallidos must be non-negative, got {intentos_fallidos}")
        if not (1 <= nivel_actual <= 3):
            raise AIServiceError(f"Nivel_Actual must be 1-3, got {nivel_actual}")
        
        logger.info(f"Input metrics validated: accuracy={tasa_aciertos}, "
                   f"time={tiempo_promedio}, failures={intentos_fallidos}, level={nivel_actual}")
        
        # Prepare features in correct order
        X_new = np.array([[tasa_aciertos, tiempo_promedio, intentos_fallidos, nivel_actual]])
        
        # Scale features
        X_new_scaled = scaler.transform(X_new)
        
        # Make prediction with probability
        prediction = svm_model.predict(X_new_scaled)[0]
        probabilities = svm_model.predict_proba(X_new_scaled)[0]
        
        # Get confidence (max probability)
        confidence = float(np.max(probabilities))
        
        # Map prediction to label
        prediction_labels = {
            0: 'Mantener Nivel',
            1: 'Avanzar Nivel',
            2: 'Retroceder Nivel'
        }
        prediction_label = prediction_labels.get(prediction, 'Desconocido')
        
        # Build probability dictionary
        prob_dict = {
            'Mantener': float(probabilities[0]),
            'Avanzar': float(probabilities[1]),
            'Retroceder': float(probabilities[2])
        }
        
        result = {
            'prediction': int(prediction),
            'prediction_label': prediction_label,
            'confidence': confidence,
            'probabilities': prob_dict,
            'input_metrics': {
                'Tasa_Aciertos': tasa_aciertos,
                'Tiempo_Promedio': tiempo_promedio,
                'Intentos_Fallidos': intentos_fallidos,
                'Nivel_Actual': nivel_actual
            }
        }
        
        logger.info(f"Prediction: {prediction_label} (confidence: {confidence:.2%})")
        return result
    
    except AIServiceError as e:
        logger.error(f"AI Service Error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in predict_next_level: {str(e)}")
        raise AIServiceError(f"Failed to make prediction: {str(e)}")


def get_model_info() -> Optional[Dict]:
    """
    Get information about the trained model.
    
    Returns:
        Dict: Model metadata including:
            - model_exists (bool): Whether model file exists
            - model_path (str): Full path to model file
            - model_size (float): Size in MB
            - scaler_exists (bool): Whether scaler file exists
            - training_date (str): Approximate creation date
        None: If model doesn't exist
    
    Example:
        >>> info = get_model_info()
        >>> if info:
        ...     print(f"Model size: {info['model_size']} MB")
    """
    try:
        if not os.path.exists(MODEL_PATH):
            logger.warning("Model file not found")
            return None
        
        model_size = os.path.getsize(MODEL_PATH) / (1024 * 1024)  # MB
        scaler_size = os.path.getsize(SCALER_PATH) / (1024 * 1024) if os.path.exists(SCALER_PATH) else 0
        
        info = {
            'model_exists': True,
            'model_path': MODEL_PATH,
            'model_size_mb': round(model_size, 2),
            'scaler_exists': os.path.exists(SCALER_PATH),
            'scaler_size_mb': round(scaler_size, 2),
            'total_size_mb': round(model_size + scaler_size, 2),
            'modification_time': os.path.getmtime(MODEL_PATH)
        }
        
        logger.info(f"Model info: {info}")
        return info
    
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        return None


def delete_model() -> bool:
    """
    Delete trained model and scaler files.
    
    Returns:
        bool: True if deletion successful, False otherwise
    
    Example:
        >>> if delete_model():
        ...     print("Model deleted successfully")
    """
    try:
        deleted = False
        
        if os.path.exists(MODEL_PATH):
            os.remove(MODEL_PATH)
            logger.info(f"Deleted model: {MODEL_PATH}")
            deleted = True
        
        if os.path.exists(SCALER_PATH):
            os.remove(SCALER_PATH)
            logger.info(f"Deleted scaler: {SCALER_PATH}")
            deleted = True
        
        if not deleted:
            logger.warning("No model or scaler files found to delete")
        
        return deleted
    
    except Exception as e:
        logger.error(f"Error deleting model: {str(e)}")
        return False


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
