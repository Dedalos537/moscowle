import os
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from joblib import load, dump
from sklearn.svm import SVC

MODEL_PATH= 'ai_models/svm_model.pkl'

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
    X = []
    Y = []
    
    # 1. Generate Synthetic Data (Base Knowledge) to ensure model stability
    # We use 300 points to maintain a solid baseline
    for _ in range(300):
        acc = np.random.uniform(0, 100)
        time = np.random.uniform(500, 3000)
        label = get_expert_label(acc, time)
        X.append([acc, time])
        Y.append(label)

    # 2. Incorporate Real Data (Retraining/Adaptation)
    if real_data and len(real_data) > 0:
        print(f"Retraining with {len(real_data)} real data points...")
        for data_point in real_data:
            acc = data_point[0]
            time = data_point[1]
            # In a future version, this label could come from therapist feedback
            # For now, we auto-label to adapt the decision boundaries to the user's data distribution
            label = get_expert_label(acc, time)
            
            # We add the real data multiple times (oversampling) to give it more weight
            # This ensures the model adapts to the specific user patterns
            for _ in range(3): 
                X.append([acc, time])
                Y.append(label)

    model = SVC(kernel='rbf', probability=True)
    model.fit(X, Y)
    
    # ensure the directory for the model exists
    model_dir = os.path.dirname(MODEL_PATH)
    if model_dir and not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
    dump(model, MODEL_PATH)
    print("Modelo re-entrenado y guardado exitosamente.")

def predict_level(accuracy, avg_time):
    if not os.path.exists(MODEL_PATH):
        train_model()
    
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
