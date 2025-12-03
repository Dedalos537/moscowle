# QUICK START - K-Means Segmentación

**Integración rápida de la función en 5 minutos**

---

## ⚡ Paso 1: Verificar Instalación (1 min)

```bash
# Asegurar que las dependencias estén instaladas
pip install -r backend/requirements.txt

# Verificar que scikit-learn esté disponible
python -c "from sklearn.cluster import KMeans; print('✓ scikit-learn OK')"
```

---

## ⚡ Paso 2: Verificar la Función (1 min)

```bash
# Ir al directorio backend
cd backend

# Verificar que la función existe
grep -n "def run_k_means_segmentation" app/services/ai_service.py
```

Deberías ver:
```
420:def run_k_means_segmentation(db, SessionMetrics, k: int = 3) -> Dict[str, Union[int, float, List, str]]:
```

---

## ⚡ Paso 3: Probar la Función (2 min)

```bash
# Ejecutar el script de prueba
python test_k_means_segmentation.py
```

Salida esperada:
```
======================================================================
K-MEANS SEGMENTATION TEST
======================================================================

📊 Total sessions in database: 9
🔄 Running K-Means segmentation...

✅ SEGMENTATION SUCCESSFUL

📈 Results Summary:
   - Total sessions processed: 9
   - Sessions updated: 9
   - Number of clusters: 3
   - Inertia: 123.4567
   - Silhouette Score: 0.6789

📍 Cluster Centroids:
   cluster_0 - Avanzados:
      Accuracy: 95.00%
      Average Time: 10.00s
   ... (más clusters)

✅ TEST COMPLETED SUCCESSFULLY
```

---

## ⚡ Paso 4: Usar en Código Python (1 min)

### Opción A: Script Directo

```python
#!/usr/bin/env python3
from app import create_app
from app.extensions import db
from app.models import SessionMetrics
from app.services.ai_service import run_k_means_segmentation

app = create_app()

with app.app_context():
    # Ejecutar
    result = run_k_means_segmentation(db, SessionMetrics)
    
    # Usar resultado
    if result['success']:
        print(f"✓ {result['updated_sessions']} sesiones actualizadas")
        print(f"✓ Silhouette: {result['silhouette_score']:.3f}")
    else:
        print(f"✗ Error: {result['error']}")
```

### Opción B: En Endpoint API

```python
# routes/api.py
from flask import Blueprint, jsonify

api = Blueprint('api', __name__)

@api.route('/api/clustering/run', methods=['POST'])
def run_clustering():
    from app.services.ai_service import run_k_means_segmentation
    result = run_k_means_segmentation(db, SessionMetrics)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({'error': result['error']}), 400

# En app/__init__.py
app.register_blueprint(api)
```

### Opción C: Tarea Programada

```python
# Con APScheduler
from flask_apscheduler import APScheduler

scheduler = APScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)  # 2 AM diario
def nightly_clustering():
    with app.app_context():
        result = run_k_means_segmentation(db, SessionMetrics)
        if result['success']:
            print(f"✓ Clustering: {result['updated_sessions']} sesiones")

scheduler.start()
```

---

## 📊 Interpretar Resultado

```python
result = run_k_means_segmentation(db, SessionMetrics)

# Resultado exitoso
if result['success']:
    
    # 1. Cuántas sesiones se procesaron
    print(f"Total procesadas: {result['total_sessions']}")
    print(f"Actualizadas: {result['updated_sessions']}")
    
    # 2. Centros de los clusters
    for cluster_id, centroid in result['centroids'].items():
        print(f"{cluster_id}: {centroid['label']}")
        print(f"  Accuracy: {centroid['accuracy_rate']:.1f}%")
        print(f"  Time: {centroid['average_time']:.1f}s")
    
    # 3. Tamaño de cada grupo
    for cluster_id, summary in result['clusters_summary'].items():
        print(f"{cluster_id}: {summary['size']} estudiantes ({summary['percentage']:.1f}%)")
    
    # 4. Calidad del clustering
    print(f"Silhouette: {result['silhouette_score']:.3f}")  # 0.5-1.0 = bueno
    print(f"Inertia: {result['inertia']:.2f}")               # menor = mejor

# Resultado fallido
else:
    print(f"Error: {result['error']}")
```

---

## 🐛 Problemas Comunes

### ❌ "No session metrics data available"
```python
# Solución: Agregar datos de prueba
from app.models import SessionMetrics
session = SessionMetrics(
    patient_id=1, game_name="Test", 
    accuracy_rate=85.0, average_time=30.0,
    failed_attempts=3, previous_level=1
)
db.session.add(session)
db.session.commit()
```

### ❌ "ImportError: No module named 'sklearn'"
```bash
# Solución: Instalar scikit-learn
pip install scikit-learn>=1.0
pip install -r backend/requirements.txt
```

### ❌ "Insufficient data: N sessions, need at least k for k clusters"
```python
# Solución: Agregar más datos o reducir k
result = run_k_means_segmentation(db, SessionMetrics, k=2)  # En lugar de 3
```

---

## ✅ Checklist de Integración

- [ ] `requirements.txt` tiene scikit-learn, numpy, pandas, joblib
- [ ] `app/services/ai_service.py` tiene función `run_k_means_segmentation`
- [ ] `app/models/session_metrics.py` tiene campo `cluster_id`
- [ ] Test ejecuta sin errores: `python test_k_means_segmentation.py`
- [ ] BD tiene datos en tabla `session_metrics`
- [ ] Rutas API registradas (opcional, pero recomendado)
- [ ] Documentación leída: `K_MEANS_IMPLEMENTATION_README.md`

---

## 📁 Archivos de Referencia

```
backend/
├── app/services/ai_service.py          ← Función aquí (línea 420+)
├── app/models/session_metrics.py       ← Modelo con cluster_id
├── requirements.txt                     ← Dependencias actualizadas
│
├── K_MEANS_IMPLEMENTATION_README.md    ← Documentación completa
├── K_MEANS_SEGMENTATION_GUIDE.md       ← Guía de uso
├── K_MEANS_IMPLEMENTATION_SUMMARY.md   ← Resumen ejecutivo
├── CLUSTERING_ROUTES_EXAMPLE.py        ← Ejemplos de rutas
└── test_k_means_segmentation.py        ← Script de prueba
```

---

## 📞 Parámetros Configurables

```python
# Número de clusters (default: 3)
result = run_k_means_segmentation(db, SessionMetrics, k=2)   # 2 clusters
result = run_k_means_segmentation(db, SessionMetrics, k=3)   # 3 clusters
result = run_k_means_segmentation(db, SessionMetrics, k=4)   # 4 clusters

# Features usadas (hardcoded):
# - accuracy_rate (0-100%)
# - average_time (segundos)
```

---

## 🎯 Caso de Uso

```python
# Scenario: Ejecutar cada noche a las 2 AM

def automated_student_segmentation():
    """Segmentar estudiantes automáticamente"""
    app = create_app()
    
    with app.app_context():
        logger = logging.getLogger(__name__)
        
        try:
            result = run_k_means_segmentation(db, SessionMetrics)
            
            if result['success']:
                # Logging
                logger.info(f"✓ Clustering completado")
                logger.info(f"  - Sesiones: {result['total_sessions']}")
                logger.info(f"  - Actualizadas: {result['updated_sessions']}")
                logger.info(f"  - Silhouette: {result['silhouette_score']:.3f}")
                
                # Opcional: Enviar notificación
                # send_email(f"Clustering completado: {result['updated_sessions']} sesiones")
                
                return True
            else:
                logger.error(f"✗ Clustering falló: {result['error']}")
                return False
        
        except Exception as e:
            logger.error(f"✗ Excepción: {e}", exc_info=True)
            return False
```

---

## 🚀 Próximos Pasos

1. **Hoy:** Correr test_k_means_segmentation.py
2. **Mañana:** Registrar endpoint API
3. **Próxima semana:** Integrar en Dashboard
4. **Futuro:** Agregar más features y visualizaciones

---

**Tiempo total de integración:** 5-10 minutos ⚡

---

*Documentación: 3 de diciembre de 2025*
