# K-Means Segmentación de Estudiantes

**Fecha:** 3 de diciembre de 2025  
**Versión:** 1.0  
**Status:** ✅ Implementado y documentado  

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Características](#características)
3. [Función Principal](#función-principal)
4. [Estructura Matemática](#estructura-matemática)
5. [Uso en la Aplicación](#uso-en-la-aplicación)
6. [Ejemplos Prácticos](#ejemplos-prácticos)
7. [Integración con Flask](#integración-con-flask)
8. [Interpretación de Resultados](#interpretación-de-resultados)
9. [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Descripción General

La función `run_k_means_segmentation()` implementa el algoritmo **K-Means clustering** para segmentar estudiantes en 3 grupos basados en dos métricas de desempeño:

### Grupos de Segmentación

| Grupo | ID | Características | Intervención |
|-------|----|--------------------|---|
| **Avanzados** | 0 | ✅ Alta precisión (>80%), ⚡ Bajo tiempo | Mantener o aumentar dificultad |
| **Intermedios** | 1 | 🟡 Precisión media (40-80%), ⏱️ Tiempo medio | Seguimiento y práctica adicional |
| **Necesitan Apoyo** | 2 | ❌ Baja precisión (<40%), 🐌 Alto tiempo | Apoyo intensivo, revisión de conceptos |

---

## ✨ Características

### Funcionalidades Principales

✅ **Carga de datos real** desde la tabla `session_metrics`  
✅ **Normalización automática** usando StandardScaler  
✅ **Algoritmo K-Means** con k=3 clusters configurables  
✅ **Actualización de base de datos** con cluster_id  
✅ **Métricas de calidad** (Inertia, Silhouette Score)  
✅ **Estadísticas detalladas** por cluster  
✅ **Logging completo** para auditoría  
✅ **Manejo robusto** de excepciones  

### Características Técnicas

- **Features escalables**: accuracy_rate, average_time
- **Escalado**: StandardScaler (μ=0, σ=1)
- **Algoritmo**: K-Means con n_init=10
- **Seed**: random_state=42 (reproducibilidad)
- **Persistencia**: Salva cluster_id en DB
- **Performance**: O(n * k * d * i) donde i = iteraciones

---

## 🔧 Función Principal

### Definición

```python
def run_k_means_segmentation(db, SessionMetrics, k: int = 3) -> Dict[str, Union[int, float, List, str]]
```

### Parámetros de Entrada

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `db` | SQLAlchemy DB | ✅ Sí | - | Instancia de Flask-SQLAlchemy |
| `SessionMetrics` | Model Class | ✅ Sí | - | Clase modelo SessionMetrics |
| `k` | int | ❌ No | 3 | Número de clusters |

### Retorno Exitoso

```python
{
    'success': True,                          # ✅ Ejecución exitosa
    'k_clusters': 3,                          # Número de clusters
    'total_sessions': 100,                    # Total sesiones procesadas
    'updated_sessions': 100,                  # Sesiones actualizadas con cluster_id
    
    'centroids': {                            # Centros de clusters
        'cluster_0': {
            'accuracy_rate': 95.2,            # % promedio
            'average_time': 10.5,             # segundos
            'label': 'Avanzados'
        },
        'cluster_1': {
            'accuracy_rate': 65.7,
            'average_time': 35.2,
            'label': 'Intermedios'
        },
        'cluster_2': {
            'accuracy_rate': 35.4,
            'average_time': 80.1,
            'label': 'Necesitan Apoyo'
        }
    },
    
    'cluster_labels': {                       # Mapeo ID -> Etiqueta
        0: 'Avanzados',
        1: 'Intermedios',
        2: 'Necesitan Apoyo'
    },
    
    'clusters_summary': {                     # Estadísticas por cluster
        'cluster_0': {
            'size': 30,                       # Número de sesiones
            'percentage': 30.0,               # % del total
            'accuracy_rate': {                # Estadísticas accuracy
                'mean': 95.2,
                'std': 2.1,
                'min': 90.0,
                'max': 100.0
            },
            'average_time': {                 # Estadísticas time
                'mean': 10.5,
                'std': 1.2,
                'min': 8.0,
                'max': 13.5
            }
        },
        # ... cluster_1 y cluster_2 ...
    },
    
    'inertia': 234.567,                       # Suma distancias² intra-cluster
    'silhouette_score': 0.678,                # Calidad clustering (-1 a 1)
    'timestamp': '2025-12-03T10:30:00.000000' # ISO 8601 timestamp
}
```

### Retorno Fallido

```python
{
    'success': False,
    'error': 'Descripción del error',
    'total_sessions': 0,
    'updated_sessions': 0,
    'timestamp': '2025-12-03T10:30:00.000000'
}
```

---

## 📐 Estructura Matemática

### 1. Extracción de Features

Para cada sesión en `session_metrics`:
$$X_i = \begin{bmatrix} accuracy\_rate_i \\ average\_time_i \end{bmatrix}$$

### 2. Normalización (StandardScaler)

$$X'_i = \frac{X_i - \mu}{\sigma}$$

Donde:
- $\mu$ = media de cada feature
- $\sigma$ = desviación estándar de cada feature

### 3. K-Means Clustering

**Objetivo:** Minimizar la distancia intra-cluster:

$$J = \sum_{i=1}^{n} \sum_{j=1}^{k} w_{ij} ||X_i - C_j||^2$$

Donde:
- $X_i$ = punto i
- $C_j$ = centroide del cluster j
- $w_{ij}$ = 1 si X_i pertenece a cluster j, 0 si no

**Iteración:**
1. Asignar cada punto al centroide más cercano
2. Recalcular centroides como promedio de puntos asignados
3. Repetir hasta convergencia

### 4. Métricas de Calidad

**Inertia (Within-cluster sum of squares):**
$$I = \sum_{i=1}^{n} ||X_i - C_{assigned}||^2$$

**Silhouette Score:**
$$S = \frac{1}{n} \sum_{i=1}^{n} \frac{b_i - a_i}{\max(a_i, b_i)}$$

Donde:
- $a_i$ = distancia media intra-cluster
- $b_i$ = distancia media al cluster más cercano

Interpretación:
- S ≈ 1: Clustering excelente
- S ≈ 0: Solapamiento entre clusters
- S < 0: Puntos posiblemente en cluster incorrecto

---

## 🚀 Uso en la Aplicación

### Ubicación del Código

```
backend/
├── app/
│   ├── services/
│   │   └── ai_service.py          ← Función aquí
│   ├── models/
│   │   └── session_metrics.py     ← Modelo de datos
│   └── extensions.py              ← DB instance
```

### Importación

```python
from app.services.ai_service import run_k_means_segmentation, AIServiceError
from app.extensions import db
from app.models import SessionMetrics
```

---

## 💡 Ejemplos Prácticos

### Ejemplo 1: Uso Directo en Script

```python
#!/usr/bin/env python3
from app import create_app
from app.extensions import db
from app.models import SessionMetrics
from app.services.ai_service import run_k_means_segmentation

app = create_app()

with app.app_context():
    # Ejecutar clustering
    result = run_k_means_segmentation(db, SessionMetrics, k=3)
    
    if result['success']:
        print(f"✓ {result['updated_sessions']} sesiones actualizadas")
        print(f"✓ Silhouette Score: {result['silhouette_score']:.4f}")
        
        # Procesar cada cluster
        for cluster_id, summary in result['clusters_summary'].items():
            print(f"\n{cluster_id}:")
            print(f"  - Tamaño: {summary['size']} ({summary['percentage']:.1f}%)")
            print(f"  - Accuracy: {summary['accuracy_rate']['mean']:.2f}% ± {summary['accuracy_rate']['std']:.2f}%")
            print(f"  - Tiempo: {summary['average_time']['mean']:.2f}s ± {summary['average_time']['std']:.2f}s")
    else:
        print(f"✗ Error: {result['error']}")
```

### Ejemplo 2: Uso en Servicio

```python
# app/services/student_service.py

from app.services.ai_service import run_k_means_segmentation

def segment_students():
    """Segmentar estudiantes por desempeño"""
    try:
        result = run_k_means_segmentation(db, SessionMetrics)
        
        if result['success']:
            # Usar resultados...
            return result
    except Exception as e:
        logger.error(f"Error segmentando: {e}")
        return None
```

### Ejemplo 3: Endpoint API

```python
# routes/clustering_routes.py

from flask import Blueprint, jsonify, request
from flask_jwt_required import jwt_required

api = Blueprint('api', __name__)

@api.route('/api/clustering/run', methods=['POST'])
@jwt_required()
def run_clustering():
    """POST /api/clustering/run"""
    result = run_k_means_segmentation(db, SessionMetrics)
    
    if result['success']:
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    else:
        return jsonify({'error': result['error']}), 400
```

---

## 🔌 Integración con Flask

### 1. Registrar Rutas

```python
# app/__init__.py

from flask import Flask
from routes.clustering_routes import clustering_bp

def create_app():
    app = Flask(__name__)
    
    # ... otras configuraciones ...
    
    # Registrar rutas de clustering
    app.register_blueprint(clustering_bp)
    
    return app
```

### 2. Endpoints Disponibles

Los siguientes endpoints están disponibles en `CLUSTERING_ROUTES_EXAMPLE.py`:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/clustering/run` | Ejecutar clustering |
| GET | `/api/clustering/summary` | Obtener resumen |
| GET | `/api/clustering/centroids` | Obtener centroides |
| GET | `/api/clustering/cluster/{id}/sessions` | Sesiones de cluster |
| GET | `/api/clustering/statistics` | Estadísticas detalladas |
| GET | `/api/clustering/export` | Exportar resultados |

### 3. Consumir desde Frontend

```javascript
// Ejecutar clustering
const response = await fetch('/api/clustering/run', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ k: 3 })
});

const result = await response.json();
console.log(result.data.clusters_summary);
```

---

## 📊 Interpretación de Resultados

### Entender los Centroides

Los centroides representan el "estudiante típico" de cada grupo:

```
Cluster 0 (Avanzados):
  - accuracy_rate: 95.2%  → Muy buenas respuestas
  - average_time: 10.5s   → Resuelve rápido
  ✅ Perfil: Dominan el contenido

Cluster 1 (Intermedios):
  - accuracy_rate: 65.7%  → Respuestas inconsistentes
  - average_time: 35.2s   → Tiempo moderado
  🟡 Perfil: En proceso de aprendizaje

Cluster 2 (Necesitan Apoyo):
  - accuracy_rate: 35.4%  → Muchos errores
  - average_time: 80.1s   → Tardan mucho
  ❌ Perfil: Necesitan refuerzo
```

### Métricas de Calidad

**Silhouette Score = 0.678**
- ✅ Clustering bastante bueno
- Los clusters están bien separados
- Mínimo solapamiento

**Inertia = 234.567**
- Suma de distancias² dentro de clusters
- Menor inertia = clusters más compactos
- Use para comparar modelos con diferente k

### Distribución de Estudiantes

```
Total: 100 sesiones

Cluster 0: 30 (30%)  ← Tercer más grande
Cluster 1: 50 (50%)  ← Más grande (típico)
Cluster 2: 20 (20%)  ← Más pequeño
```

**Interpretación:**
- Mayoría en grupo intermedio (normal)
- 30% ya dominan contenidos
- 20% requieren apoyo intensivo

---

## 🔍 Solución de Problemas

### Error: "No session metrics data available"

**Causa:** No hay registros en la tabla `session_metrics`

**Solución:**
```python
# Insertar datos de prueba
from app.models import SessionMetrics
session = SessionMetrics(
    patient_id=1,
    game_name="Math Game",
    accuracy_rate=85.0,
    average_time=30.0,
    failed_attempts=3,
    previous_level=1
)
db.session.add(session)
db.session.commit()
```

### Error: "Insufficient data"

**Causa:** Menos de k sesiones en BD

**Solución:**
- Opción 1: Aumentar datos
- Opción 2: Reducir k: `run_k_means_segmentation(db, SessionMetrics, k=2)`

### Silhouette Score Negativo

**Causa:** Clusters solapados o data no separable

**Soluciones:**
1. Revisar calidad de datos
2. Usar features adicionales
3. Considerar modelo diferente (DBSCAN)

### Centroide con Valores Inesperados

**Posibilidades:**
1. Features mal escaladas (check StandardScaler)
2. Outliers en datos
3. Distribución no normal

**Solución:**
```python
# Revisar datos raw
sessions = db.session.query(SessionMetrics).all()
for s in sessions:
    print(f"Accuracy: {s.accuracy_rate}, Time: {s.average_time}")
```

### Cambios de Clustering Entre Ejecuciones

**Causa:** K-Means es no-determinista (aunque tiene random_state=42)

**Solución:** Aumentar `n_init` en KMeans (ya está en 10):
```python
# En ai_service.py, línea ~570
kmeans = KMeans(n_clusters=k, random_state=42, n_init=20)  # Aumentar
```

---

## 📦 Dependencias Requeridas

```txt
Flask>=2.2
Flask-SQLAlchemy>=3.0
scikit-learn>=1.0       ← K-Means, StandardScaler
numpy>=1.20            ← Operaciones numéricas
pandas>=1.3            ← DataFrame (opcional)
joblib>=1.1            ← Serialización modelos
```

Instalación:
```bash
pip install scikit-learn>=1.0 numpy>=1.20 pandas>=1.3 joblib>=1.1
```

---

## 🎓 Algoritmo K-Means Paso a Paso

1. **Inicialización:** Seleccionar k centroides aleatorios
2. **Asignación:** Asignar cada punto al centroide más cercano
3. **Actualización:** Recalcular centroides como promedio de asignaciones
4. **Convergencia:** Repetir 2-3 hasta que centroides no cambien
5. **Finalización:** Retornar asignaciones finales

**Complejidad:**
- Tiempo: O(n·k·d·i) donde i = iteraciones
- Espacio: O(n·d)

---

## 📝 Caso de Uso: Educación Personalizada

### Antes del Clustering

```
Todos los estudiantes → Mismo contenido → Resultados variables
```

### Después del Clustering

```
Grupo Avanzados (30%) → Desafíos adicionales → Motivación
Grupo Intermedios (50%) → Práctica regular → Progreso
Grupo Apoyo (20%) → Tutorías + repaso → Recuperación
```

**Beneficios:**
✅ Educación personalizada  
✅ Mejor seguimiento  
✅ Intervención temprana  
✅ Optimización de recursos  

---

## 🔐 Seguridad y Auditoría

- ✅ Logging completo de todas las operaciones
- ✅ Transacciones atómicas (commit/rollback)
- ✅ Validación de entrada
- ✅ Manejo de excepciones robusto
- ✅ JWT protection en endpoints

---

## 📚 Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `backend/app/services/ai_service.py` | Función principal |
| `backend/app/models/session_metrics.py` | Modelo de datos |
| `backend/K_MEANS_SEGMENTATION_GUIDE.md` | Guía completa |
| `backend/CLUSTERING_ROUTES_EXAMPLE.py` | Ejemplos de rutas |
| `backend/test_k_means_segmentation.py` | Script de prueba |
| `backend/requirements.txt` | Dependencias actualizadas |

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs: `flask_dev.log` o `logs/`
2. Ejecutar `test_k_means_segmentation.py`
3. Verificar conexión a BD
4. Consultar documentación en archivos `.md`

---

**Última actualización:** 3 de diciembre de 2025  
**Versión:** 1.0  
**Estado:** ✅ Producción lista
