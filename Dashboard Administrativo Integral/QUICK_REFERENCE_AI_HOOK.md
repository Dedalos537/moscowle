# ⚡ Quick Reference - useAIRecommendation Hook

**Ubicación:** `src/hooks/useAIRecommendation.ts`  
**Fecha:** 3 de diciembre de 2025

---

## 🚀 Uso Más Rápido

```typescript
import { useAIRecommendation } from '../hooks/useAIRecommendation';

// Usar en componente
const { recommendation, isLoading, error, getRecommendation } = useAIRecommendation();

// Obtener recomendación
await getRecommendation({
  tasa_aciertos: 85,
  tiempo_promedio: 30,
  intentos_fallidos: 5,
  nivel_actual: 2
});

// Usar resultado
console.log(recommendation?.prediction_label);  // "Avanzar Nivel"
console.log(recommendation?.recommended_next_level);  // 3
```

---

## 📋 API Completa

| Propiedad/Método | Tipo | Descripción |
|------------------|------|-------------|
| `recommendation` | `AIRecommendation \| null` | Recomendación obtenida |
| `isLoading` | `boolean` | ¿Cargando? |
| `error` | `string \| null` | Mensaje de error |
| `success` | `boolean` | ¿Éxito? |
| `getRecommendation(metrics)` | `Promise<AIRecommendation>` | Obtener recomendación |
| `reset()` | `void` | Limpiar estado |
| `fetchRecommendation()` | `Promise<void>` | Auto-fetch |
| `getRecommendationLabel()` | `string` | Label legible |
| `getConfidencePercentage()` | `string` | Confianza % |
| `getNextLevel()` | `number \| null` | Próximo nivel |
| `getReasoning()` | `string` | Explicación |

---

## 💾 Interfaces

```typescript
// Input
interface StudentMetrics {
  tasa_aciertos: number;       // 0-100
  tiempo_promedio: number;     // segundos
  intentos_fallidos: number;   // número
  nivel_actual: number;        // 1-3
  sesion_id?: number;
  patient_id?: number;
}

// Output
interface AIRecommendation {
  prediction: number;          // 0|1|2
  prediction_label: string;    // "Mantener"|"Avanzar"|"Retroceder"
  confidence: number;          // 0-1
  probabilities: {
    Mantener: number;
    Avanzar: number;
    Retroceder: number;
  };
  input_metrics: StudentMetrics;
  recommended_next_level?: number;
  reasoning?: string;
}
```

---

## 📝 Ejemplos Rápidos

### Manual Trigger
```typescript
const { getRecommendation } = useAIRecommendation();

<button onClick={async () => {
  await getRecommendation(metrics);
}}>
  Obtener Recomendación
</button>
```

### Auto-fetch
```typescript
const { recommendation } = useAIRecommendation(metrics);
// Automáticamente obtiene cuando cambia metrics
```

### Con Manejo de Errores
```typescript
const { recommendation, isLoading, error } = useAIRecommendation();

if (isLoading) return <Spinner />;
if (error) return <ErrorMessage error={error} />;
if (recommendation) return <RecommendationCard rec={recommendation} />;
```

### Estados
```typescript
const { isLoading, error, success, recommendation } = useAIRecommendation();

// Exactamente un estado es true en cada momento
if (isLoading) { /* cargando */ }
if (error) { /* error */ }
if (success && recommendation) { /* éxito */ }
```

---

## 🎨 Componente Minimal

```tsx
function GameResults() {
  const { recommendation, isLoading, error, getRecommendation } = 
    useAIRecommendation();

  return (
    <div>
      <button onClick={() => getRecommendation(metrics)}>
        Get AI Recommendation
      </button>

      {isLoading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      {recommendation && (
        <div>
          <h2>{recommendation.prediction_label}</h2>
          <p>Level: {recommendation.recommended_next_level}</p>
          <p>Confidence: {(recommendation.confidence * 100).toFixed(0)}%</p>
        </div>
      )}
    </div>
  );
}
```

---

## 🔧 Configuración

```typescript
// Default (usa VITE_BACKEND_URL)
const hook1 = useAIRecommendation();

// Con URL personalizada
const hook2 = useAIRecommendation(undefined, 'http://api.example.com');

// Con auto-fetch
const metrics = { /* ... */ };
const hook3 = useAIRecommendation(metrics);
```

---

## 🛠️ Troubleshooting Rápido

| Problema | Solución |
|----------|----------|
| No authentication token | Login primero: `localStorage.setItem('auth_token', token)` |
| Loading infinito | Revisar conexión a backend |
| Error 400 Bad Request | Validar métricas (números válidos, rangos correctos) |
| recommendation es null | Esperar isLoading=false primero |

---

## 📦 Instalación en Proyecto

```bash
# 1. Copiar archivo
cp useAIRecommendation.ts src/hooks/

# 2. Importar
import { useAIRecommendation } from '../hooks/useAIRecommendation';

# 3. Usar
const { recommendation } = useAIRecommendation();
```

---

## 🎯 Casos de Uso Comunes

### Case 1: Mostrar Recomendación después de Juego
```typescript
const onGameComplete = async () => {
  const rec = await getRecommendation(gameMetrics);
  showModal(rec);
};
```

### Case 2: Auto-Actualizar Nivel
```typescript
const { recommendation } = useAIRecommendation(metrics);

useEffect(() => {
  if (recommendation?.recommended_next_level) {
    updateStudentLevel(recommendation.recommended_next_level);
  }
}, [recommendation]);
```

### Case 3: Analytics/Logging
```typescript
const { recommendation } = useAIRecommendation();

useEffect(() => {
  if (recommendation) {
    analytics.track('recommendation_received', {
      prediction: recommendation.prediction,
      confidence: recommendation.confidence
    });
  }
}, [recommendation]);
```

---

## 🎓 Valores Esperados

```
tasa_aciertos:     0-100 (ej: 85.5)
tiempo_promedio:   0-∞ segundos (ej: 45.3)
intentos_fallidos: 0-∞ número (ej: 5)
nivel_actual:      1-3 (ej: 2)

prediction:        0 (Mantener) | 1 (Avanzar) | 2 (Retroceder)
confidence:        0-1 (ej: 0.678)
```

---

## 📚 Documentación Completa

Ver: `USE_AI_RECOMMENDATION_HOOK.md`

---

**Version:** 1.0  
**Status:** ✅ Production Ready
