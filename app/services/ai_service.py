import os
import threading
import time
import logging
from logging.handlers import RotatingFileHandler

# Lazy imports for heavy AI libraries
np = None
pd = None
KMeans = None
load = None
dump = None
SVC = None

def _import_dependencies():
    global np, pd, KMeans, load, dump, SVC
    if np is None:
        import numpy as np
        import pandas as pd
        from sklearn.cluster import KMeans
        from joblib import load, dump
        from sklearn.svm import SVC

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ai_models', 'svm_model.pkl')


# internal guard to avoid spawning multiple training threads
_train_thread = None
_train_lock = threading.Lock()

# configure module logger to write training progress to a rotating file
# Use absolute path for logs
try:
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _log_dir = os.path.join(_base_dir, 'logs')
    os.makedirs(_log_dir, exist_ok=True)
    _log_file_path = os.path.join(_log_dir, 'ai_training.log')
    
    _logger = logging.getLogger('app.ai_service')
    
    # Check if handler already exists
    has_handler = False
    for h in _logger.handlers:
        if isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', '') == _log_file_path:
            has_handler = True
            break
            
    if not has_handler:
        fh = RotatingFileHandler(
            _log_file_path,
            maxBytes=5 * 1024 * 1024, # 5 MB
            backupCount=5
        )
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        _logger.addHandler(fh)
        _logger.setLevel(logging.INFO)

except Exception as e:
    # Fallback to null handler or print if filesystem is read-only or path invalid
    print(f"Warning: Could not setup AI logging: {e}")
    _logger = logging.getLogger('app.ai_service')
    _logger.addHandler(logging.NullHandler())


def get_expert_label(accuracy, avg_time_ms):
    """
    Define expert rules for labeling data.
    1: Avanzar Nivel (High Accuracy & Fast)
    2: Retroceder/Apoyo (Low Accuracy OR Slow)
    0: Mantener Nivel (Average)
    """
    # Logic refined for better gameplay experience
    if accuracy >= 80 and avg_time_ms <= 1500:
        return 1
    elif accuracy < 60 or avg_time_ms > 2500:
        return 2
    else:
        return 0

def train_model(real_data=None):
    """
    Train the SVM model.
    real_data: List of [accuracy, avg_time_ms] from actual user sessions.
    """
    _import_dependencies()
    start_ts = time.time()
    _logger.info('Training started; real_data_count=%s', len(real_data) if real_data else 0)
    X = []
    Y = []
    
    # 1. Generate Synthetic Data (Base Knowledge) to ensure model stability
    # We use 300 points to maintain a solid baseline
    for _ in range(300):
        acc = np.random.uniform(0, 100)
        t_ms = np.random.uniform(500, 3000)
        label = get_expert_label(acc, t_ms)
        X.append([acc, t_ms])
        Y.append(label)

    # 2. Incorporate Real Data (Retraining/Adaptation)
    if real_data and len(real_data) > 0:
        _logger.info('Retraining with %d real data points', len(real_data))
        for data_point in real_data:
            acc = data_point[0]
            t_ms = data_point[1]
            # In a future version, this label could come from therapist feedback
            # For now, we auto-label to adapt the decision boundaries to the user's data distribution
            label = get_expert_label(acc, t_ms)

            # We add the real data multiple times (oversampling) to give it more weight
            # This ensures the model adapts to the specific user patterns
            for _ in range(3):
                X.append([acc, t_ms])
                Y.append(label)

    try:
        model = SVC(kernel='rbf', probability=True)
        model.fit(X, Y)
    except Exception as e:
        _logger.exception('Model training failed: %s', e)
        raise
    
    # ensure the directory for the model exists
    model_dir = os.path.dirname(MODEL_PATH)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)

    dump(model, MODEL_PATH)
    elapsed = time.time() - start_ts
    _logger.info('Modelo re-entrenado y guardado exitosamente; path=%s elapsed_seconds=%.2f', MODEL_PATH, elapsed)
    print("Modelo re-entrenado y guardado exitosamente.")

def predict_level(accuracy, avg_time):
    _import_dependencies()
    if not os.path.exists(MODEL_PATH):
        # Allow skipping model training (useful for fast startup/dev).
        # Set SKIP_MODEL_TRAIN=1 in the environment to avoid triggering train_model().
        if os.getenv('SKIP_MODEL_TRAIN'):
            print('SKIP_MODEL_TRAIN set: skipping model training and returning default prediction.')
            labels = {0: "Mantener Nivel", 1: "Avanzar Nivel", 2: "Retroceder/Apoyo"}
            return 0, labels[0]

        # If model missing, start training in background (daemon) and return default immediately.
        global _train_thread
        with _train_lock:
            if _train_thread is None or not _train_thread.is_alive():
                print('Model file missing: starting background training thread.')
                _train_thread = threading.Thread(target=train_model, daemon=True)
                _train_thread.start()
            else:
                print('Background training already in progress; returning default prediction.')

        labels = {0: "Mantener Nivel", 1: "Avanzar Nivel", 2: "Retroceder/Apoyo"}
        return 0, labels[0]
    
    model = load(MODEL_PATH)
    # predict returns an array; take the first (and only) element
    pred = model.predict([[accuracy, avg_time]])[0]

    labels = {0: "Mantener Nivel", 1: "Avanzar Nivel", 2: "Retroceder/Apoyo"}
    
    return int(pred), labels[int(pred)]

def get_cluster(metrics_data):
    if len(metrics_data) < 3: return []
    kmeans = KMeans(n_clusters=3, n_init=10)
    kmeans.fit(metrics_data)
    return kmeans.labels_
