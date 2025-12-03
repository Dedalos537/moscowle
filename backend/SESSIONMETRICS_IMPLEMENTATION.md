# SessionMetrics Implementation Summary

## ✅ Componentes Implementados

### 1. **Modelo SQLAlchemy** (`backend/app/models/session_metrics.py`)

```python
class SessionMetrics(db.Model):
    - id: Integer PK
    - patient_id: Integer FK → patients.id (con cascade delete)
    - game_name: String(255) - nombre del juego/actividad
    - accuracy_rate: Float - tasa de aciertos (0-100%)
    - average_time: Float - tiempo promedio en segundos
    - failed_attempts: Integer - intentos fallidos
    - previous_level: Integer - nivel actual (1-3)
    - predicted_next_level: Integer - próximo nivel predicho (0-3, nullable)
    - cluster_id: Integer - ID del cluster K-Means (nullable)
    - created_at: DateTime - timestamp de creación (default: UTC now)
    - Relationship: patient (backref: session_metrics)
    - Índices: patient_id, game_name, created_at, patient_game, cluster_date
```

**Características:**
- Foreign Key a `patients.id` con CASCADE DELETE
- Timestamps automáticos con UTC
- Método `to_dict()` para serialización
- Índices optimizados para queries comunes

---

### 2. **Esquemas Marshmallow** (`backend/app/schemas/session_metrics_schema.py`)

#### a) **SessionMetricsSchema** (Serialización general)
```python
- id: Int (dump_only)
- patient_id: Int (required, min=1)
- game_name: Str (required, 1-255 chars)
- accuracy_rate: Float (required, 0-100)
- average_time: Float (required, >=0)
- failed_attempts: Int (required, >=0)
- previous_level: Int (required, 1-3)
- predicted_next_level: Int (optional, 0-3, allow_none)
- cluster_id: Int (optional, >=0, allow_none)
- created_at: DateTime (dump_only)
```

#### b) **CreateSessionMetricsSchema** (POST requests)
- Todos los campos requeridos excepto `predicted_next_level` y `cluster_id`
- Validaciones estrictas

#### c) **UpdateSessionMetricsSchema** (PUT/PATCH requests)
- Todos los campos opcionales
- Permite actualizaciones parciales

---

### 3. **Rutas API** (`backend/app/routes/session_metrics_routes.py`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/session-metrics/` | Obtener todas las métricas (con filtros y paginación) |
| GET | `/api/session-metrics/{id}` | Obtener métrica específica |
| GET | `/api/session-metrics/patient/{patient_id}` | Obtener todas las métricas de un paciente |
| GET | `/api/session-metrics/patient/{patient_id}/summary` | Resumen agregado del paciente |
| POST | `/api/session-metrics/` | Crear nueva métrica |
| PUT | `/api/session-metrics/{id}` | Actualizar métrica existente |
| DELETE | `/api/session-metrics/{id}` | Eliminar métrica |

**Todas las rutas requieren autenticación JWT**

---

### 4. **Migración SQL** (`backend/migrations/session_metrics_migration.sql`)

```sql
CREATE TABLE session_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    game_name VARCHAR(255) NOT NULL,
    accuracy_rate FLOAT DEFAULT 0.0,
    average_time FLOAT DEFAULT 0.0,
    failed_attempts INT DEFAULT 0,
    previous_level INT DEFAULT 1,
    predicted_next_level INT,
    cluster_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    INDEX idx_patient_id (patient_id),
    INDEX idx_game_name (game_name),
    INDEX idx_created_at (created_at),
    INDEX idx_patient_game (patient_id, game_name),
    INDEX idx_cluster_date (cluster_id, created_at)
)
```

---

### 5. **Scripts de Utilidad**

#### a) **migrate_session_metrics.py**
```bash
python backend/migrate_session_metrics.py
```
- Crea la tabla automáticamente
- Verifica la estructura de la tabla
- Manejo de errores

#### b) **insert_sample_metrics.py**
```bash
python backend/insert_sample_metrics.py
```
- Inserta datos de prueba realistas
- Crea pacientes de prueba si no existen
- Genera 5-8 sesiones por paciente
- Datos aleatorios pero consistentes

---

### 6. **Registro en la Aplicación** (`backend/app/__init__.py`)

```python
# Importar modelo
from .models import session_metrics as _session_metrics

# Registrar blueprint
from .routes.session_metrics_routes import session_metrics_bp
app.register_blueprint(session_metrics_bp, url_prefix="/api/session-metrics")
```

---

## 🚀 Cómo Usar

### Paso 1: Crear la tabla

```bash
cd /Users/apple/Documents/moscowle/backend
python migrate_session_metrics.py
```

**Salida esperada:**
```
[Migration] Starting session_metrics table creation...
[Migration] ✅ SessionMetrics table created successfully!
[Migration] ✅ Table 'session_metrics' verified in database
[Migration] Table structure:
  - id: INTEGER
  - patient_id: INTEGER
  - game_name: VARCHAR(255)
  - accuracy_rate: FLOAT
  - average_time: FLOAT
  - failed_attempts: INTEGER
  - previous_level: INTEGER
  - predicted_next_level: INTEGER
  - cluster_id: INTEGER
  - created_at: DATETIME
```

### Paso 2: Insertar datos de prueba (opcional)

```bash
python backend/insert_sample_metrics.py
```

**Salida esperada:**
```
[Sample Data] Starting insertion of sample session metrics...
[Sample Data] ✅ Inserted 38 sample session metrics

[Sample Data] Summary:
  - Total metrics: 38
  - Patients with data: 5
  - Unique games: 6
```

### Paso 3: Usar la API

#### Crear una métrica después de un juego:
```bash
curl -X POST http://localhost:5001/api/session-metrics/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "game_name": "Memory Match",
    "accuracy_rate": 87.5,
    "average_time": 2.3,
    "failed_attempts": 2,
    "previous_level": 2,
    "predicted_next_level": 3
  }'
```

#### Obtener métricas de un paciente:
```bash
curl http://localhost:5001/api/session-metrics/patient/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Obtener resumen agregado:
```bash
curl http://localhost:5001/api/session-metrics/patient/1/summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📋 Validaciones Implementadas

### Campos Requeridos (POST):
- ✅ `patient_id`: Debe existir en tabla `patients`
- ✅ `game_name`: 1-255 caracteres
- ✅ `accuracy_rate`: 0-100
- ✅ `average_time`: ≥ 0
- ✅ `failed_attempts`: ≥ 0
- ✅ `previous_level`: 1-3

### Campos Opcionales:
- ✅ `predicted_next_level`: 0-3 o null
- ✅ `cluster_id`: ≥ 0 o null

### Errores Comunes:
```json
{
  "msg": "Validation failed",
  "errors": {
    "accuracy_rate": ["Must be between 0 and 100"]
  }
}
```

---

## 🔗 Relaciones

### Foreign Key: patient_id → patients.id

```
patients (1) ─────────── (Many) session_metrics
                         
Cuando se elimina un paciente:
- Todas sus metrics se eliminan automáticamente (CASCADE DELETE)

Backref: Patient.session_metrics (lazy='dynamic')
- Permite queries: patient.session_metrics.filter_by(game_name='...')
```

---

## 📊 Queries Útiles

### Metrics por juego para un paciente:
```python
SessionMetrics.query.filter_by(
    patient_id=patient_id,
    game_name='Memory Match'
).order_by(SessionMetrics.created_at.desc()).all()
```

### Pacientes por cluster:
```python
SessionMetrics.query.filter_by(cluster_id=1).distinct(SessionMetrics.patient_id).all()
```

### Promedio de accuraccy por juego:
```python
from sqlalchemy import func
db.session.query(
    SessionMetrics.game_name,
    func.avg(SessionMetrics.accuracy_rate).label('avg_accuracy')
).group_by(SessionMetrics.game_name).all()
```

---

## 🎯 Casos de Uso

### 1. **Registrar sesión después de un juego**
Frontend captura: accuracy, tiempo, intentos fallidos
POST → guardar en DB con nivel actual
Backend calcula: `predicted_next_level`

### 2. **ML Pipeline**
- Lee: todas las métricas no asignadas (cluster_id = null)
- Ejecuta: K-Means clustering
- Asigna: cluster_id con PUT

### 3. **Dashboard de Progreso**
- GET `/api/session-metrics/patient/{id}/summary`
- Muestra: gráficos de progreso, cambios de nivel, patrones

### 4. **Análisis de Rendimiento**
- Filtra por rango de fechas
- Agrupa por juego
- Calcula estadísticas

---

## 📁 Archivos Creados

```
backend/
├── app/
│   ├── models/
│   │   └── session_metrics.py          ← Modelo ORM
│   ├── schemas/
│   │   └── session_metrics_schema.py    ← Esquemas Marshmallow
│   └── routes/
│       └── session_metrics_routes.py    ← Rutas API
├── migrations/
│   └── session_metrics_migration.sql    ← Script SQL
├── migrate_session_metrics.py           ← Script de migración
├── insert_sample_metrics.py             ← Script de datos de prueba
└── SESSION_METRICS_API.md               ← Documentación completa
```

---

## ✨ Características Extras

1. **Paginación**: limit/offset en todos los endpoints GET
2. **Filtrado**: por `patient_id`, `game_name`
3. **Índices optimizados**: para queries comunes
4. **Timestamps automáticos**: UTC con `datetime.utcnow`
5. **Cascade delete**: elimina métricas al eliminar paciente
6. **Summary endpoint**: resumen agregado para ML
7. **Manejo de errores**: validación completa + respuestas claras
8. **JWT required**: todas las rutas protegidas

---

## 🧪 Testing

### Crear métrica de prueba:
```python
from app.models.session_metrics import SessionMetrics
from app.extensions import db

metric = SessionMetrics(
    patient_id=1,
    game_name="Test Game",
    accuracy_rate=85.5,
    average_time=2.0,
    failed_attempts=1,
    previous_level=2,
    predicted_next_level=3
)
db.session.add(metric)
db.session.commit()
```

### Query de verificación:
```python
from app.models.session_metrics import SessionMetrics
metrics = SessionMetrics.query.filter_by(patient_id=1).all()
print(f"Total metrics for patient 1: {len(metrics)}")
```

---

## 🔐 Seguridad

- ✅ JWT required en todas las rutas
- ✅ Validación de entrada con Marshmallow
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Type hints en funciones
- ✅ Error handling robusto

---

## 📈 Próximos Pasos

1. **Frontend Integration**: Crear componentes React para visualizar métricas
2. **ML Pipeline**: Script Python para asignar cluster_id
3. **Webhooks**: Notificaciones cuando `predicted_next_level` cambia
4. **Batch Import**: Endpoint para importar métricas en lote
5. **Export**: Generar reportes en CSV/PDF

---

## 📚 Documentación

Ver `backend/SESSION_METRICS_API.md` para:
- Descripción completa de todos los endpoints
- Ejemplos de curl
- Manejo de errores
- Casos de uso reales

---

**Implementación completada**: ✅ 2025-12-03
