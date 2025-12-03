# Hook useAIRecommendation - Documentación Completa

**Fecha:** 3 de diciembre de 2025  
**Versión:** 1.0  
**Ubicación:** `Dashboard Administrativo Integral/src/hooks/useAIRecommendation.ts`

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Características](#características)
3. [Instalación](#instalación)
4. [API del Hook](#api-del-hook)
5. [Uso Básico](#uso-básico)
6. [Ejemplos Prácticos](#ejemplos-prácticos)
7. [Manejo de Errores](#manejo-de-errores)
8. [Integración con GamesModule](#integración-con-gamesmodule)
9. [TypeScript](#typescript)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

`useAIRecommendation` es un hook personalizado de React que facilita la integración de las recomendaciones de nivel del backend AI en la aplicación frontend.

**Propósito principal:** 
Obtener recomendaciones automáticas de progresión (Mantener, Avanzar, Retroceder) basadas en métricas de desempeño del estudiante.

---

## ✨ Características

✅ **POST a /api/ai/recommend_level** - Llamada API automática  
✅ **JWT Authentication** - Usa token de localStorage  
✅ **VITE_BACKEND_URL** - Compatible con variables de entorno  
✅ **Manejo de Estados** - Loading, Error, Success  
✅ **TypeScript First** - Tipos completos  
✅ **Validación de Entrada** - Valida métricas antes de enviar  
✅ **Cálculo de Nivel** - Calcula próximo nivel automáticamente  
✅ **Reasoning** - Genera explicación legible de la recomendación  
✅ **Error Handling** - Manejo robusto de errores  

---

## 📦 Instalación

El hook está listo para usar. Solo copiar el archivo:

```
Dashboard Administrativo Integral/src/hooks/useAIRecommendation.ts
```

### Dependencias Requeridas

```json
{
  "dependencies": {
    "react": "^18.0.0"
  }
}
```

No requiere librerías externas (usa Fetch API nativa).

---

## 🔧 API del Hook

### Firma de la Función

```typescript
useAIRecommendation(
  metricsData?: StudentMetrics,
  backendUrl?: string
): UseAIRecommendationReturn
```

### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `metricsData` | `StudentMetrics` | No | Métricas del estudiante (auto-fetch si se proporciona) |
| `backendUrl` | `string` | No | URL del backend (default: VITE_BACKEND_URL) |

### Return Type

```typescript
interface UseAIRecommendationReturn {
  // Estado
  recommendation: AIRecommendation | null;
  isLoading: boolean;
  error: string | null;
  success: boolean;

  // Métodos
  getRecommendation(metrics: StudentMetrics): Promise<AIRecommendation>;
  reset(): void;
  fetchRecommendation(): Promise<void>;

  // Utilidades
  getRecommendationLabel(): string;
  getConfidencePercentage(): string;
  getNextLevel(): number | null;
  getReasoning(): string;
}
```

---

## 🚀 Uso Básico

### Ejemplo Más Simple

```typescript
import { useAIRecommendation } from '../hooks/useAIRecommendation';

function MyComponent() {
  const { recommendation, isLoading, error, getRecommendation } = useAIRecommendation();

  const handleClick = async () => {
    try {
      await getRecommendation({
        tasa_aciertos: 85.5,
        tiempo_promedio: 45.3,
        intentos_fallidos: 5,
        nivel_actual: 2
      });
    } catch (err) {
      console.error('Error:', err);
    }
  };

  return (
    <div>
      <button onClick={handleClick}>Obtener Recomendación</button>
      {isLoading && <p>Cargando...</p>}
      {error && <p>Error: {error}</p>}
      {recommendation && (
        <div>
          <h3>{recommendation.prediction_label}</h3>
          <p>Confianza: {(recommendation.confidence * 100).toFixed(1)}%</p>
        </div>
      )}
    </div>
  );
}
```

---

## 💡 Ejemplos Prácticos

### Ejemplo 1: Auto-fetch al Montar

```typescript
import { useAIRecommendation, StudentMetrics } from '../hooks/useAIRecommendation';

function GameResults() {
  const metrics: StudentMetrics = {
    tasa_aciertos: 92,
    tiempo_promedio: 30,
    intentos_fallidos: 2,
    nivel_actual: 2
  };

  // Auto-fetch cuando el componente monta
  const { recommendation, isLoading } = useAIRecommendation(metrics);

  if (isLoading) return <div>Cargando recomendación...</div>;

  if (!recommendation) return null;

  return (
    <div>
      <h2>{recommendation.prediction_label}</h2>
      <p>Próximo nivel: {recommendation.recommended_next_level}</p>
    </div>
  );
}
```

### Ejemplo 2: Con Manejo de Errores

```typescript
function GameResultsWithErrorHandling() {
  const { recommendation, isLoading, error, getRecommendation } = useAIRecommendation();

  const handleRecommendationRequest = async () => {
    try {
      const result = await getRecommendation({
        tasa_aciertos: 75,
        tiempo_promedio: 50,
        intentos_fallidos: 8,
        nivel_actual: 1
      });

      console.log('Recomendación:', result);
    } catch (err) {
      // Error ya está en state.error, pero también podemos capturarlo aquí
      if (err instanceof Error) {
        console.error('Error específico:', err.message);
      }
    }
  };

  if (error) {
    return (
      <div className="error-card">
        <p>❌ {error}</p>
        <button onClick={handleRecommendationRequest}>Reintentar</button>
      </div>
    );
  }

  return (
    <button onClick={handleRecommendationRequest} disabled={isLoading}>
      {isLoading ? 'Procesando...' : 'Obtener Recomendación'}
    </button>
  );
}
```

### Ejemplo 3: Usando Utilidades

```typescript
function RecommendationDisplay() {
  const { recommendation, getNextLevel, getReasoning, getConfidencePercentage } = 
    useAIRecommendation();

  if (!recommendation) return null;

  return (
    <div>
      <p>Nivel Recomendado: {getNextLevel()}</p>
      <p>Confianza: {getConfidencePercentage()}%</p>
      <p>Análisis: {getReasoning()}</p>
    </div>
  );
}
```

### Ejemplo 4: Reset de Estado

```typescript
function RecommendationCard() {
  const { recommendation, isLoading, error, reset, getRecommendation } = 
    useAIRecommendation();

  const handleApply = () => {
    // Aplicar cambio...
    reset(); // Limpiar estado
  };

  const handleDiscard = () => {
    reset(); // Volver al inicio
  };

  // ...resto del código
}
```

---

## 🛡️ Manejo de Errores

### Errores Comunes

#### 1. No authentication token found

```typescript
try {
  await getRecommendation(metrics);
} catch (err) {
  // Usuario no autenticado
  // Redirigir a login
  window.location.href = '/login';
}
```

**Causa:** Usuario no tiene token JWT en localStorage  
**Solución:** Asegurar que el usuario esté autenticado antes de usar el hook

#### 2. Backend error: 400 Bad Request

```typescript
// Validar métricas antes de enviar
const metrics: StudentMetrics = {
  tasa_aciertos: NaN,  // ❌ INCORRECTO
  tiempo_promedio: 45,
  intentos_fallidos: 5,
  nivel_actual: 2
};

// ✅ CORRECTO
const metrics: StudentMetrics = {
  tasa_aciertos: 85.5,    // 0-100
  tiempo_promedio: 45,    // segundos
  intentos_fallidos: 5,   // número
  nivel_actual: 2         // 1-3
};
```

#### 3. Network Error

```typescript
const { error, getRecommendation } = useAIRecommendation();

useEffect(() => {
  const controller = new AbortController();
  
  return () => controller.abort(); // Cancelar petición al desmontar
}, []);

// Implementar retry logic
const retryGetRecommendation = async (maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await getRecommendation(metrics);
    } catch (err) {
      if (i === maxRetries - 1) throw err;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
};
```

---

## 🎮 Integración con GamesModule

### Paso 1: Importar el Hook

```typescript
// GamesModule.tsx
import { useAIRecommendation, StudentMetrics } from '../hooks/useAIRecommendation';
```

### Paso 2: Usar en Componente

```typescript
export const GamesModule: React.FC = () => {
  const [currentGame, setCurrentGame] = useState<Game | null>(null);
  const [sessionMetrics, setSessionMetrics] = useState<StudentMetrics | null>(null);
  const [showRecommendation, setShowRecommendation] = useState(false);

  const { recommendation, isLoading, error, getRecommendation } = 
    useAIRecommendation();

  // Cuando el estudiante termina un juego
  const handleGameComplete = async (metrics: SessionMetrics) => {
    const studentMetrics: StudentMetrics = {
      tasa_aciertos: metrics.accuracy_rate,
      tiempo_promedio: metrics.average_time,
      intentos_fallidos: metrics.failed_attempts,
      nivel_actual: metrics.current_level
    };

    setSessionMetrics(studentMetrics);
    setShowRecommendation(true);

    // Auto-obtener recomendación
    try {
      await getRecommendation(studentMetrics);
    } catch (err) {
      console.error('Error obteniendo recomendación:', err);
    }
  };

  const handleApplyRecommendation = async () => {
    if (!recommendation?.recommended_next_level) return;

    // Guardar cambio en BD
    await updateStudentLevel(recommendation.recommended_next_level);

    // Cerrar modal
    setShowRecommendation(false);
  };

  return (
    <div className="games-module">
      {/* Juego actual */}
      {currentGame && (
        <GameComponent 
          game={currentGame}
          onComplete={handleGameComplete}
        />
      )}

      {/* Modal de recomendación */}
      {showRecommendation && (
        <Modal isOpen={true} onClose={() => setShowRecommendation(false)}>
          {isLoading && <LoadingSpinner />}
          {error && <ErrorMessage message={error} />}
          {recommendation && (
            <GameResultsRecommendation
              recommendation={recommendation}
              metrics={sessionMetrics!}
              onAccept={handleApplyRecommendation}
              onDismiss={() => setShowRecommendation(false)}
            />
          )}
        </Modal>
      )}
    </div>
  );
};
```

### Paso 3: Crear Componente de Recomendación

```typescript
interface GameResultsRecommendationProps {
  recommendation: AIRecommendation;
  metrics: StudentMetrics;
  onAccept: () => void;
  onDismiss: () => void;
}

export const GameResultsRecommendation: React.FC<GameResultsRecommendationProps> = ({
  recommendation,
  metrics,
  onAccept,
  onDismiss
}) => {
  const getIcon = () => {
    if (recommendation.prediction === 1) return '🚀'; // Avanzar
    if (recommendation.prediction === 2) return '📚'; // Retroceder
    return '➡️'; // Mantener
  };

  return (
    <div className="recommendation-card">
      <h2>{getIcon()} {recommendation.prediction_label}</h2>
      
      <MetricsDisplay metrics={metrics} />
      
      <ProbabilityChart probabilities={recommendation.probabilities} />
      
      <LevelRecommendation nextLevel={recommendation.recommended_next_level} />
      
      <div className="actions">
        <button onClick={onAccept}>✓ Aplicar</button>
        <button onClick={onDismiss}>✕ Descartar</button>
      </div>
    </div>
  );
};
```

---

## 🎓 TypeScript

### Interfaces Disponibles

```typescript
// Métricas de entrada
export interface StudentMetrics {
  tasa_aciertos: number;           // 0-100
  tiempo_promedio: number;         // segundos
  intentos_fallidos: number;       // número
  nivel_actual: number;            // 1-3
  sesion_id?: number;              // opcional
  patient_id?: number;             // opcional
}

// Recomendación de salida
export interface AIRecommendation {
  prediction: number;              // 0, 1, o 2
  prediction_label: string;        // "Mantener", "Avanzar", "Retroceder"
  confidence: number;              // 0-1
  probabilities: {
    Mantener: number;
    Avanzar: number;
    Retroceder: number;
  };
  input_metrics: StudentMetrics;
  recommended_next_level?: number;
  reasoning?: string;
}

// Estado del hook
export interface UseAIRecommendationState {
  recommendation: AIRecommendation | null;
  isLoading: boolean;
  error: string | null;
  success: boolean;
}
```

### Type Safety

```typescript
// ✅ CORRECTO
const { recommendation, isLoading } = useAIRecommendation();
if (recommendation && recommendation.prediction === 1) {
  console.log('Avanzar a nivel', recommendation.recommended_next_level);
}

// ❌ INCORRECTO (TypeScript error)
if (recommendation.prediction === 'avanzar') {
  // ...
}
```

---

## 🐛 Troubleshooting

### Problema: Hook retorna null

**Causa:** No se ha llamado `getRecommendation` aún

**Solución:**
```typescript
const { recommendation, getRecommendation } = useAIRecommendation();

// Necesitas llamar a getRecommendation
await getRecommendation(metrics);
```

### Problema: Token expirado

**Síntoma:** Error: "401 Unauthorized"

**Solución:** Implementar refresh token
```typescript
const getAuthToken = () => {
  let token = localStorage.getItem('auth_token');
  
  // Si está expirado, renovar
  if (isTokenExpired(token)) {
    token = refreshToken();
    localStorage.setItem('auth_token', token);
  }
  
  return token;
};
```

### Problema: CORS Error

**Síntoma:** "Access to XMLHttpRequest blocked by CORS policy"

**Solución:** Backend debe permitir CORS
```python
# backend/app/__init__.py
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

### Problema: Loading infinito

**Causa:** Petición no se completa

**Solución:** Agregar timeout
```typescript
const getRecommendationWithTimeout = async (metrics: StudentMetrics) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000); // 10s

  try {
    return await getRecommendation(metrics);
  } finally {
    clearTimeout(timeout);
  }
};
```

---

## 📝 Checklist de Implementación

- [ ] Hook importado en componente
- [ ] Token JWT en localStorage
- [ ] VITE_BACKEND_URL configurada correctamente
- [ ] Métricas validadas antes de enviar
- [ ] Manejo de estados implementado (loading, error, success)
- [ ] Componentes de UI para mostrar recomendación
- [ ] Endpoints API disponibles en backend
- [ ] Testing realizado

---

## 🔗 Archivos Relacionados

- **Hook:** `Dashboard Administrativo Integral/src/hooks/useAIRecommendation.ts`
- **Ejemplo:** `Dashboard Administrativo Integral/src/components/dashboard/AIRecommendationExample.tsx`
- **Backend:** `backend/app/services/ai_service.py` (función predict_next_level)
- **Endpoint API:** `backend/app/routes/` (rutas de /api/ai/recommend_level)

---

## 🚀 Próximas Mejoras

- [ ] Agregar caching de resultados
- [ ] Implementar retry automático
- [ ] Agregar analytics/tracking
- [ ] Visualizaciones avanzadas
- [ ] Historial de recomendaciones
- [ ] Exportar reportes

---

**Fecha:** 3 de diciembre de 2025  
**Versión:** 1.0  
**Status:** ✅ Listo para Producción
