# AI Service Module - Documentación Completa

## 📋 Resumen Ejecutivo

El módulo **ai_service.py** implementa un modelo de clasificación Support Vector Machine (SVM) con kernel RBF para predecir el siguiente nivel de progresión de estudiantes en juegos terapéuticos basándose en métricas de desempeño.

**Características principales:**
- ✅ Modelo SVM con kernel RBF entrenado en 500 muestras sintéticas
- ✅ 97% de precisión en predicciones
- ✅ Serialización a archivos .pkl para persistencia
- ✅ Escalado de características con StandardScaler
- ✅ Validación robusta de entrada
- ✅ Integración con SessionMetrics API

---

## 🏗️ Arquitectura

### Estructura de Archivos

```
backend/
├── app/
│   ├── services/
│   │   └── ai_service.py          # Módulo principal de AI
│   └── routes/
│       └── session_metrics_routes.py  # API integrada con AI
├── models/                         # Directorio para modelos serializado
│   ├── svm_model.pkl              # Modelo SVM entrenado
│   └── feature_scaler.pkl         # Escalador de características
├── train_model.py                 # Script para entrenar/administrar modelo
└── test_ai_service.py             # Script de pruebas

```

### Flujo de Datos

```
Métricas de Estudiante
    ↓
┌─────────────────────────────────────┐
│ Validación de Entrada              │
│ - Rangos de valores               │
│ - Campos requeridos               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Escalado de Características        │
│ (StandardScaler)                  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Predicción SVM                     │
│ - predict(): clase                │
│ - predict_proba(): confianza      │
└─────────────────────────────────────┘
    ↓
Resultado de Predicción (0, 1, 2)
+ Confianza
+ Probabilidades completas
```

---

## 🧠 Modelo SVM

### Especificaciones

| Parámetro | Valor |
|-----------|-------|
| **Algoritmo** | Support Vector Machine (SVM) |
| **Kernel** | RBF (Radial Basis Function) |
| **Regularización (C)** | 1.0 |
| **Gamma** | 'scale' (1 / (n_features * X.var())) |
| **Muestras de Entrenamiento** | 400 (80% de 500) |
| **Muestras de Test** | 100 (20% de 500) |
| **Vectores de Soporte** | 143 |

### Métricas de Desempeño

```
Accuracy:  0.9700 (97.00%)
Precision: 0.9703
Recall:    0.9700
F1 Score:  0.9697
```

---

## 📊 Dataset Sintético

### Características

| Campo | Rango | Tipo | Descripción |
|-------|-------|------|-------------|
| **Tasa_Aciertos** | 20-100% | Float | Porcentaje de respuestas correctas |
| **Tiempo_Promedio** | 5-120s | Float | Tiempo promedio por intento |
| **Intentos_Fallidos** | 0-50 | Integer | Cantidad de intentos fallidos |
| **Nivel_Actual** | 1-3 | Integer | Nivel actual de dificultad |

### Variable Objetivo (Siguiente_Nivel)

```
0: Mantener Nivel  → Desempeño promedio
1: Avanzar Nivel   → Desempeño excelente
2: Retroceder      → Desempeño deficiente
```

### Lógica de Generación

```python
advancement_score = (accuracy / 100) * 100 - (time / 120) * 30 - (failures / 50) * 40

if advancement_score > 40:
    siguiente_nivel = 1  # Avanzar
elif advancement_score < -20:
    siguiente_nivel = 2  # Retroceder
else:
    siguiente_nivel = 0  # Mantener
```

---

## 🔧 API de Funciones

### 1. `train_svm_model()`

**Propósito:** Entrenar el modelo SVM y serializar a disco.

**Firma:**
```python
def train_svm_model(
    n_samples: int = 500,
    test_size: float = 0.2,
    random_state: int = 42
) -> Dict[str, Union[float, int]]
```

**Parámetros:**
- `n_samples` (int): Número de muestras sintéticas (default: 500)
- `test_size` (float): Proporción para testing (default: 0.2)
- `random_state` (int): Semilla para reproducibilidad (default: 42)

**Retorna:**
```python
{
    'accuracy': 0.97,
    'precision': 0.9703,
    'recall': 0.9700,
    'f1': 0.9697,
    'n_samples': 400,
    'n_support_vectors': 143,
    'classes': [0, 1, 2],
    'feature_names': ['Tasa_Aciertos', 'Tiempo_Promedio', ...],
    'model_path': '/path/to/svm_model.pkl',
    'scaler_path': '/path/to/feature_scaler.pkl'
}
```

**Ejemplo:**
```python
from app.services.ai_service import train_svm_model

results = train_svm_model(n_samples=500)
print(f"Modelo entrenado con {results['accuracy']:.2%} de precisión")
```

**Excepciones:**
- `AIServiceError`: Si el entrenamiento falla

---

### 2. `predict_next_level()`

**Propósito:** Predecir el siguiente nivel para un estudiante.

**Firma:**
```python
def predict_next_level(
    metrics_data: Dict[str, Union[int, float]]
) -> Dict[str, Union[int, float, str]]
```

**Parámetros:**
```python
metrics_data = {
    'Tasa_Aciertos': 85.5,           # 0-100
    'Tiempo_Promedio': 45.3,         # segundos, ≥0
    'Intentos_Fallidos': 5,          # ≥0
    'Nivel_Actual': 2                # 1-3
}
```

**Retorna:**
```python
{
    'prediction': 1,                          # 0, 1, o 2
    'prediction_label': 'Avanzar Nivel',      # Etiqueta legible
    'confidence': 0.9978,                     # 0-1
    'probabilities': {
        'Mantener': 0.0000,
        'Avanzar': 0.9978,
        'Retroceder': 0.0022
    },
    'input_metrics': {
        'Tasa_Aciertos': 85.5,
        'Tiempo_Promedio': 45.3,
        'Intentos_Fallidos': 5,
        'Nivel_Actual': 2
    }
}
```

**Ejemplo:**
```python
from app.services.ai_service import predict_next_level

metrics = {
    'Tasa_Aciertos': 92.0,
    'Tiempo_Promedio': 35.0,
    'Intentos_Fallidos': 3,
    'Nivel_Actual': 1
}

result = predict_next_level(metrics)
print(f"Predicción: {result['prediction_label']}")
print(f"Confianza: {result['confidence']:.2%}")
```

**Validaciones:**
- Tasa_Aciertos: debe estar entre 0-100
- Tiempo_Promedio: debe ser ≥0
- Intentos_Fallidos: debe ser ≥0
- Nivel_Actual: debe ser 1-3
- Todos los campos son requeridos

**Excepciones:**
- `AIServiceError`: Si el modelo no existe, la entrada es inválida, o falla la predicción

---

### 3. `get_model_info()`

**Propósito:** Obtener información del modelo entrenado.

**Firma:**
```python
def get_model_info() -> Optional[Dict]
```

**Retorna:**
```python
{
    'model_exists': True,
    'model_path': '/path/to/svm_model.pkl',
    'model_size_mb': 0.01,
    'scaler_exists': True,
    'scaler_size_mb': 0.001,
    'total_size_mb': 0.011,
    'modification_time': 1701619200.0
}
```

---

### 4. `delete_model()`

**Propósito:** Eliminar archivos del modelo y escalador.

**Firma:**
```python
def delete_model() -> bool
```

**Retorna:** True si se eliminó exitosamente, False en caso contrario

---

## 🌐 Integración con API

### Endpoint: POST /api/session-metrics/

El endpoint fue actualizado para usar automáticamente la predicción de IA.

**Request:**
```json
{
    "patient_id": 1,
    "game_name": "Memoria Visual",
    "accuracy_rate": 85.5,
    "average_time": 45.3,
    "failed_attempts": 5,
    "previous_level": 2,
    "predicted_next_level": null
}
```

**Response (201 Created):**
```json
{
    "id": 42,
    "patient_id": 1,
    "game_name": "Memoria Visual",
    "accuracy_rate": 85.5,
    "average_time": 45.3,
    "failed_attempts": 5,
    "previous_level": 2,
    "predicted_next_level": 1,
    "cluster_id": null,
    "created_at": "2025-12-03T15:30:45.123456",
    "ai_prediction": {
        "predicted_level": 1,
        "used_for_prediction": true,
        "all_probabilities": {
            "Mantener": 0.0000,
            "Avanzar": 0.9978,
            "Retroceder": 0.0022
        }
    }
}
```

**Comportamiento:**
- Si `predicted_next_level` es `null`, se usa la predicción de IA
- Si `predicted_next_level` tiene un valor, se respeta ese valor
- Siempre se devuelve `ai_prediction` con el resultado del modelo
- Si la IA falla, continúa sin predicción (no bloquea la creación)

---

## 🚀 Scripts de Administración

### train_model.py

Script para entrenar, inspeccionar y administrar el modelo.

**Comandos:**

```bash
# Entrenar modelo con 500 muestras (default)
python train_model.py

# Entrenar con cantidad personalizada
python train_model.py --samples 1000

# Ver información del modelo
python train_model.py --info

# Eliminar modelo existente
python train_model.py --delete
```

**Salida de entrenamiento:**
```
======================================================================
  SVM MODEL TRAINING SCRIPT - MOSCOWLE AI SERVICE
======================================================================

🚀 Training SVM Model
  Samples:     500
  Test size:   0.2
  Kernel:      RBF
  ...

✅ MODEL TRAINING COMPLETED SUCCESSFULLY

📈 Performance Metrics
  Accuracy:        0.9700 (97.00%)
  Precision:       0.9703
  Recall:          0.9700
  F1 Score:        0.9697

🔧 Model Details
  Training samples: 400
  Support vectors:  143
  Classes:          [0, 1, 2]
  ...
```

### test_ai_service.py

Script para probar predicciones en diferentes escenarios.

```bash
python test_ai_service.py
```

Prueba 5 casos de estudiantes:
1. Excelente (debe avanzar) - 95% accuracy
2. Bueno (debe avanzar) - 85% accuracy
3. Promedio (debe mantener) - 65% accuracy
4. Bajo (debe retroceder) - 35% accuracy
5. Muy bajo (debe retroceder) - 20% accuracy

---

## 📦 Dependencias

Instalar con:
```bash
pip install numpy pandas scikit-learn joblib
```

| Paquete | Versión | Propósito |
|---------|---------|----------|
| **numpy** | ≥1.20.0 | Operaciones numéricas |
| **pandas** | ≥1.3.0 | Manipulación de datos |
| **scikit-learn** | ≥1.0.0 | Modelo SVM y preprocessing |
| **joblib** | ≥1.0.0 | Serialización de modelos |

---

## 🛡️ Manejo de Errores

### Excepciones Personalizadas

```python
class AIServiceError(Exception):
    """Error en el servicio de AI"""
    pass
```

### Escenarios de Error

| Escenario | Comportamiento |
|-----------|----------------|
| Modelo no existe | Se entrena automáticamente |
| Campo faltante | AIServiceError |
| Valor fuera de rango | AIServiceError |
| Error de predicción | AIServiceError |
| Error en API | Continúa sin predicción (graceful fallback) |

### Ejemplo de Manejo

```python
try:
    result = predict_next_level(metrics)
except AIServiceError as e:
    logger.error(f"AI prediction failed: {e}")
    # Usar valor por defecto o null
```

---

## 📊 Casos de Uso

### 1. Predicción Inmediata post-Sesión

```python
# Después de que estudiante completa una sesión de juego
metrics = {
    'Tasa_Aciertos': 78.5,
    'Tiempo_Promedio': 52.1,
    'Intentos_Fallidos': 8,
    'Nivel_Actual': 2
}

result = predict_next_level(metrics)

if result['prediction'] == 1:
    # Mostrar feedback: "¡Estás progresando bien!"
    advance_to_next_level()
elif result['prediction'] == 2:
    # Mostrar feedback: "Necesitas practicar más"
    reinforce_current_level()
```

### 2. Análisis de Cohortes

```python
# Analizar patrones en grupo de estudiantes
predictions = []
for session in patient_sessions:
    metrics = extract_metrics(session)
    pred = predict_next_level(metrics)
    predictions.append(pred['prediction'])

# Calcular distribución
advance_count = sum(1 for p in predictions if p == 1)
maintain_count = sum(1 for p in predictions if p == 0)
regress_count = sum(1 for p in predictions if p == 2)
```

### 3. Reentrenamiento Periódico

```python
# Cada mes, reentrena con nuevos datos
from app.services.ai_service import train_svm_model

# Ejecutar mensualmente
monthly_results = train_svm_model(n_samples=1000)
log_model_performance(monthly_results)
```

---

## 🔄 Flujo Completo de Integración

```
1. POST /api/session-metrics/
   ↓
2. Validar esquema (Marshmallow)
   ↓
3. Llamar predict_next_level(metrics)
   ↓
4. ├─ Cargar modelo .pkl
   ├─ Escalar características
   ├─ Hacer predicción SVM
   └─ Retornar resultado + confianza
   ↓
5. Usar predicción para llenar predicted_next_level
   ↓
6. Guardar en BD (session_metrics tabla)
   ↓
7. Retornar 201 + resultado con ai_prediction info
```

---

## 🧪 Resultados de Pruebas

```
✅ Excellent Student (95% accuracy) → Avanzar (99.33% confidence)
✅ Good Student (85% accuracy) → Avanzar (99.78% confidence)
✅ Average Student (65% accuracy) → Mantener (90.66% confidence)
✅ Struggling Student (35% accuracy) → Retroceder (81.19% confidence)
✅ Very Poor Student (20% accuracy) → Retroceder (99.49% confidence)

✅ Error Handling:
   - Missing fields detected
   - Invalid ranges rejected
   - Type validation working
```

---

## 🎓 Mejoras Futuras

1. **Reentrenamiento Automático**
   - Detectar cuando accuracy cae
   - Reentrena con datos históricos reales

2. **Hiperparámetros Adaptativos**
   - Grid search para optimización
   - Cross-validation

3. **Modelos Múltiples**
   - Modelo específico por juego
   - Ensemble de modelos

4. **Features Adicionales**
   - Patrones de comportamiento
   - Horarios preferidos
   - Racha de sesiones

5. **Explicabilidad (XAI)**
   - SHAP values para interpretabilidad
   - Explicar por qué la predicción

---

## 📝 Registros y Logging

El módulo utiliza Python's `logging` module:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Starting SVM model training...")
logger.warning("Model not found. Training new model...")
logger.error(f"Error in prediction: {str(e)}")
```

---

## ✅ Checklist de Verificación

- [x] Módulo ai_service.py creado
- [x] Dataset sintético generado (500 muestras)
- [x] Modelo SVM entrenado (97% accuracy)
- [x] Modelo serializado a .pkl
- [x] Función train_svm_model() implementada
- [x] Función predict_next_level() implementada
- [x] Validación robusta de entrada
- [x] Manejo de errores completo
- [x] Integración con SessionMetrics API
- [x] Script train_model.py creado
- [x] Script test_ai_service.py creado
- [x] Todas las pruebas pasando
- [x] Documentación completada

---

**Versión:** 1.0
**Fecha:** 3 de diciembre, 2025
**Estado:** Producción
