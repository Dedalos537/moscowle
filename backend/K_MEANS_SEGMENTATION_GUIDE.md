# K-Means Segmentation de Estudiantes - Guía de Uso

## Descripción General

La función `run_k_means_segmentation()` implementa clustering K-Means para segmentar estudiantes en 3 grupos basados en métricas de desempeño:

- **Cluster 0: Avanzados** - Alta precisión, bajo tiempo (desempeño excelente)
- **Cluster 1: Intermedios** - Precisión media, tiempo medio (desempeño moderado)
- **Cluster 2: Necesitan Apoyo** - Baja precisión, alto tiempo (necesitan más práctica)

## Características

✅ **Carga de datos real** desde la tabla `session_metrics`  
✅ **Escalado automático** de features usando StandardScaler  
✅ **Algoritmo K-Means** con k=3 clusters  
✅ **Actualización de base de datos** con asignaciones de cluster  
✅ **Cálculo de centroides** e indicadores de calidad (inertia, silhouette score)  
✅ **Estadísticas detalladas** por cluster  

## Parámetros

```python
def run_k_means_segmentation(db, SessionMetrics, k: int = 3) -> Dict[str, Union[int, float, List, str]]
```

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `db` | SQLAlchemy DB | Instancia de Flask-SQLAlchemy |
| `SessionMetrics` | Model Class | Clase modelo SessionMetrics |
| `k` | int | Número de clusters (default: 3) |

## Features Utilizadas

- **accuracy_rate** (0-100): Porcentaje de respuestas correctas
- **average_time** (segundos): Tiempo promedio por intento

## Retorno

```python
{
    'success': bool,                    # ¿Exitoso?
    'k_clusters': int,                  # Número de clusters
    'total_sessions': int,              # Total de sesiones procesadas
    'updated_sessions': int,            # Sesiones actualizadas
    'centroids': {                      # Centroides por cluster
        'cluster_0': {
            'accuracy_rate': float,
            'average_time': float,
            'label': 'Avanzados'
        },
        ...
    },
    'cluster_labels': {                 # Etiquetas legibles
        0: 'Avanzados',
        1: 'Intermedios',
        2: 'Necesitan Apoyo'
    },
    'clusters_summary': {               # Estadísticas por cluster
        'cluster_0': {
            'size': int,
            'percentage': float,
            'accuracy_rate': {...},
            'average_time': {...}
        },
        ...
    },
    'inertia': float,                   # Suma de distancias cuadradas
    'silhouette_score': float,          # Calidad del clustering (-1 a 1)
    'timestamp': str                    # Timestamp de ejecución
}
```

## Ejemplo de Uso en Ruta

```python
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models import SessionMetrics
from app.services.ai_service import run_k_means_segmentation

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/clustering/run', methods=['POST'])
def run_clustering():
    """
    Endpoint para ejecutar segmentación K-Means
    POST /api/clustering/run
    
    Body (optional):
    {
        "k": 3  # número de clusters (default: 3)
    }
    """
    try:
        data = request.get_json() or {}
        k = data.get('k', 3)
        
        result = run_k_means_segmentation(db, SessionMetrics, k=k)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': f"Clustering completado. {result['updated_sessions']} sesiones actualizadas.",
                'data': result
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'Clustering falló'),
                'data': result
            }), 400
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error durante clustering: {str(e)}'
        }), 500


@api_bp.route('/clustering/summary', methods=['GET'])
def get_clustering_summary():
    """
    Endpoint para obtener resumen de clusters
    GET /api/clustering/summary
    """
    try:
        result = run_k_means_segmentation(db, SessionMetrics)
        
        if result['success']:
            summary = {
                'clusters': result['clusters_summary'],
                'centroids': result['centroids'],
                'quality_metrics': {
                    'inertia': result['inertia'],
                    'silhouette_score': result['silhouette_score']
                },
                'timestamp': result['timestamp']
            }
            return jsonify(summary), 200
        else:
            return jsonify({'error': result.get('error')}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Ejemplo de Uso en Servicio

```python
# app/services/clustering_service.py

from app.extensions import db
from app.models import SessionMetrics
from app.services.ai_service import run_k_means_segmentation
import logging

logger = logging.getLogger(__name__)

def perform_student_segmentation():
    """
    Servicio para segmentar estudiantes
    Puede ejecutarse como tarea programada o manualmente
    """
    try:
        logger.info("Iniciando segmentación de estudiantes...")
        
        result = run_k_means_segmentation(db, SessionMetrics, k=3)
        
        if result['success']:
            logger.info(f"Segmentación completada: {result['updated_sessions']} sesiones actualizadas")
            
            # Procesar resultados
            for cluster_id, summary in result['clusters_summary'].items():
                logger.info(f"{cluster_id}: {summary['size']} estudiantes ({summary['percentage']:.1f}%)")
            
            return result
        else:
            logger.error(f"Segmentación falló: {result.get('error')}")
            return None
    
    except Exception as e:
        logger.error(f"Error durante segmentación: {str(e)}", exc_info=True)
        return None
```

## Ejemplo de Uso Directo

```python
from app import create_app
from app.extensions import db
from app.models import SessionMetrics
from app.services.ai_service import run_k_means_segmentation

# Crear app
app = create_app()

with app.app_context():
    # Ejecutar clustering
    result = run_k_means_segmentation(db, SessionMetrics, k=3)
    
    if result['success']:
        print(f"✓ Sesiones procesadas: {result['total_sessions']}")
        print(f"✓ Sesiones actualizadas: {result['updated_sessions']}")
        print(f"✓ Silhouette Score: {result['silhouette_score']:.4f}")
        
        print("\nCentroides:")
        for cluster_id, centroid in result['centroids'].items():
            print(f"  {cluster_id} ({centroid['label']}):")
            print(f"    - Accuracy: {centroid['accuracy_rate']:.2f}%")
            print(f"    - Time: {centroid['average_time']:.2f}s")
        
        print("\nResumen por Cluster:")
        for cluster_id, summary in result['clusters_summary'].items():
            print(f"  {cluster_id}: {summary['size']} estudiantes ({summary['percentage']:.1f}%)")
    else:
        print(f"✗ Error: {result.get('error')}")
```

## Interpretación de Resultados

### Silhouette Score
- **1.0**: Clustering perfecto
- **0.5**: Clustering bueno
- **0.0**: Solapamiento entre clusters
- **Negativo**: Asignaciones pobres

### Inertia
- Suma de distancias cuadradas dentro de clusters
- Valores menores indican clusters más compactos
- Disminuye conforme aumenta k

### Centroides
Puntos representativos de cada cluster. Indican:
- Accuracy promedio del grupo
- Tiempo promedio del grupo
- Características típicas de cada segmento

## Caso de Uso: Actualización Automática

```python
from flask_apscheduler import APScheduler

scheduler = APScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)  # 2:00 AM diariamente
def automated_clustering():
    """Ejecutar clustering automáticamente cada noche"""
    with app.app_context():
        result = run_k_means_segmentation(db, SessionMetrics)
        if result['success']:
            logger.info(f"Clustering automático: {result['updated_sessions']} sesiones")
```

## Requisitos

- Flask >= 2.2
- Flask-SQLAlchemy >= 3.0
- scikit-learn >= 1.0
- numpy >= 1.20
- pandas >= 1.3
- joblib >= 1.1

## Notas Importantes

1. **Mínimo de datos**: Se requieren al menos k sesiones para clustering
2. **Normalizacion**: Los features se normalizan automáticamente
3. **Persistencia**: Los cluster_id se guardan en la DB inmediatamente
4. **Logaritmo**: Todos los pasos se registran en los logs
5. **Manejador de excepciones**: Proporciona mensajes detallados de error

## Troubleshooting

### "No session metrics data available in database"
- Asegurar que existan registros en `session_metrics`
- Verificar conexión a la base de datos

### "Insufficient data"
- Se necesitan al menos k sesiones (default: 3)
- Agregar más datos o reducir k

### "Unexpected error during K-Means segmentation"
- Revisar logs para detalles
- Verificar que los features sean numéricos válidos
- Comprobar permisos de base de datos

---

**Fecha**: 3 de diciembre de 2025  
**Versión**: 1.0  
**Autor**: AI Assistant
