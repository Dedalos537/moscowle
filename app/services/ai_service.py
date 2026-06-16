import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler

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
        from joblib import dump, load
        from sklearn.cluster import KMeans
        from sklearn.svm import SVC


MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ai_models', 'svm_model.pkl'
)


_train_thread = None
_train_lock = threading.Lock()

try:
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _log_dir = os.path.join(_base_dir, 'logs')
    os.makedirs(_log_dir, exist_ok=True)
    _log_file_path = os.path.join(_log_dir, 'ai_training.log')

    _logger = logging.getLogger('app.ai_service')

    has_handler = False
    for h in _logger.handlers:
        if isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', '') == _log_file_path:
            has_handler = True
            break

    if not has_handler:
        fh = RotatingFileHandler(_log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(formatter)
        _logger.addHandler(fh)
        _logger.setLevel(logging.INFO)

except Exception as e:
    print(f'Warning: Could not setup AI logging: {e}')
    _logger = logging.getLogger('app.ai_service')
    _logger.addHandler(logging.NullHandler())


def get_expert_label(accuracy, avg_time_ms):
    """Reglas de expertos pa etiquetar: 1=Avanzar, 2=Retroceder, 0=Mantener."""
    if accuracy >= 80 and avg_time_ms <= 1500:
        return 1
    elif accuracy < 60 or avg_time_ms > 2500:
        return 2
    else:
        return 0


def start_async_training(real_data=None):
    """
    Starts the model training in a background thread if not already running.
    Non-blocking.
    """
    global _train_thread
    with _train_lock:
        if _train_thread is None or not _train_thread.is_alive():
            _logger.info('Spawning background training thread.')
            _train_thread = threading.Thread(target=train_model_task, args=(real_data,), daemon=True)
            _train_thread.start()
            return True
        else:
            _logger.info('Training already in progress. Skipping request.')
            return False


def train_model_task(real_data=None):
    """
    Actual heavy lifting training task. Should be run in a separate thread.
    """
    try:
        _import_dependencies()
        start_ts = time.time()
        _logger.info('Training task started; real_data_count=%s', len(real_data) if real_data else 0)
        X = []
        Y = []

        for _ in range(300):
            acc = np.random.uniform(0, 100)
            t_ms = np.random.uniform(500, 3000)
            label = get_expert_label(acc, t_ms)
            X.append([acc, t_ms])
            Y.append(label)

        if real_data and len(real_data) > 0:
            for data_point in real_data:
                acc = data_point[0]
                t_ms = data_point[1]
                label = get_expert_label(acc, t_ms)
                for _ in range(3):
                    X.append([acc, t_ms])
                    Y.append(label)

        model = SVC(kernel='rbf', probability=True)
        model.fit(X, Y)

        model_dir = os.path.dirname(MODEL_PATH)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)

        dump(model, MODEL_PATH)
        elapsed = time.time() - start_ts
        _logger.info('Model training completed: path=%s elapsed=%.2fs', MODEL_PATH, elapsed)

    except Exception as e:
        _logger.exception('Model training failed: %s', e)


def train_model(real_data=None):
    """Deprecated: Use start_async_training for non-blocking behavior."""
    _logger.warning('Synchronous train_model called. Prefer start_async_training.')
    train_model_task(real_data)


def predict_level(accuracy, avg_time):
    _import_dependencies()
    if not os.path.exists(MODEL_PATH):
        if os.getenv('SKIP_MODEL_TRAIN'):
            labels = {0: 'Mantener Nivel', 1: 'Avanzar Nivel', 2: 'Retroceder/Apoyo'}
            return 0, labels[0]

        start_async_training(real_data=None)

        labels = {0: 'Mantener Nivel', 1: 'Avanzar Nivel', 2: 'Retroceder/Apoyo'}
        return 0, labels[0]

    try:
        model = load(MODEL_PATH)
        pred = model.predict([[accuracy, avg_time]])[0]
        labels = {0: 'Mantener Nivel', 1: 'Avanzar Nivel', 2: 'Retroceder/Apoyo'}
        return int(pred), labels[int(pred)]
    except Exception:
        return 0, 'Mantener Nivel'


def get_cluster(metrics_data):
    if len(metrics_data) < 3:
        return []
    kmeans = KMeans(n_clusters=3, n_init=10)
    kmeans.fit(metrics_data)
    return kmeans.labels_
