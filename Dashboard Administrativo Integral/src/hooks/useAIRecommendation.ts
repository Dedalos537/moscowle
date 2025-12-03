/**
 * Hook: useAIRecommendation
 * Descripción: Hook personalizado para obtener recomendaciones de nivel
 * basado en métricas de desempeño del estudiante desde el backend AI.
 *
 * Funcionalidades:
 * - POST a /api/ai/recommend_level con metrics del estudiante
 * - Manejo de estados: cargando, error, recomendación
 * - Uso de JWT token desde localStorage
 * - Compatible con VITE_BACKEND_URL
 *
 * Autor: AI Assistant
 * Fecha: 3 de diciembre de 2025
 * Versión: 1.0
 */

import { useState, useCallback } from 'react';

/**
 * Interfaz para las métricas de desempeño del estudiante
 */
export interface StudentMetrics {
  tasa_aciertos: number;           // 0-100: Porcentaje de respuestas correctas
  tiempo_promedio: number;         // segundos: Tiempo promedio por intento
  intentos_fallidos: number;       // Número de intentos fallidos
  nivel_actual: number;            // 1-3: Nivel actual del estudiante
  sesion_id?: number;              // ID de sesión (opcional)
  patient_id?: number;             // ID del paciente (opcional)
}

/**
 * Interfaz para la respuesta de recomendación del backend
 */
export interface AIRecommendation {
  prediction: number;              // 0: Mantener, 1: Avanzar, 2: Retroceder
  prediction_label: string;        // Etiqueta legible
  confidence: number;              // 0-1: Confianza de la predicción
  probabilities: {
    Mantener: number;
    Avanzar: number;
    Retroceder: number;
  };
  input_metrics: StudentMetrics;
  recommended_next_level?: number; // Nivel recomendado
  reasoning?: string;              // Explicación de la recomendación
}

/**
 * Interfaz para el estado del hook
 */
export interface UseAIRecommendationState {
  recommendation: AIRecommendation | null;
  isLoading: boolean;
  error: string | null;
  success: boolean;
}

/**
 * Hook personalizado para obtener recomendaciones de nivel AI
 *
 * @param metricsData - Métricas del estudiante
 * @param backendUrl - URL del backend (por defecto VITE_BACKEND_URL)
 * @returns Objeto con recomendación, estado de carga y errores
 *
 * @example
 * const { recommendation, isLoading, error } = useAIRecommendation({
 *   tasa_aciertos: 85.5,
 *   tiempo_promedio: 45.3,
 *   intentos_fallidos: 5,
 *   nivel_actual: 2
 * });
 */
export function useAIRecommendation(
  metricsData?: StudentMetrics,
  backendUrl?: string
) {
  // Estados
  const [state, setState] = useState<UseAIRecommendationState>({
    recommendation: null,
    isLoading: false,
    error: null,
    success: false
  });

  /**
   * Obtener el token JWT desde localStorage
   */
  const getAuthToken = useCallback(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      throw new Error('No authentication token found. User must be logged in.');
    }
    return token;
  }, []);

  /**
   * Obtener URL del backend
   */
  const getBackendUrl = useCallback(() => {
    return (
      backendUrl ||
      (import.meta.env.VITE_BACKEND_URL as string) ||
      'http://localhost:8000'
    );
  }, [backendUrl]);

  /**
   * Obtener recomendación de nivel desde el backend
   */
  const getRecommendation = useCallback(
    async (metrics: StudentMetrics) => {
      setState(prev => ({
        ...prev,
        isLoading: true,
        error: null,
        success: false
      }));

      try {
        // Validar métricas
        if (!metrics) {
          throw new Error('Metrics data is required');
        }

        if (typeof metrics.tasa_aciertos !== 'number') {
          throw new Error('tasa_aciertos must be a number');
        }

        if (typeof metrics.tiempo_promedio !== 'number') {
          throw new Error('tiempo_promedio must be a number');
        }

        if (typeof metrics.intentos_fallidos !== 'number') {
          throw new Error('intentos_fallidos must be a number');
        }

        if (typeof metrics.nivel_actual !== 'number') {
          throw new Error('nivel_actual must be a number');
        }

        // Obtener token y URL
        const token = getAuthToken();
        const baseUrl = getBackendUrl();

        // Construir URL del endpoint
        const endpoint = `${baseUrl}/api/ai/recommend_level`;

        console.log('[useAIRecommendation] Enviando recomendación:', {
          endpoint,
          metrics
        });

        // Realizar petición POST
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            Tasa_Aciertos: metrics.tasa_aciertos,
            Tiempo_Promedio: metrics.tiempo_promedio,
            Intentos_Fallidos: metrics.intentos_fallidos,
            Nivel_Actual: metrics.nivel_actual
          })
        });

        // Validar respuesta HTTP
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.message ||
            `Backend error: ${response.status} ${response.statusText}`
          );
        }

        // Parsear respuesta
        const recommendation: AIRecommendation = await response.json();

        // Calcular nivel recomendado
        let recommendedNextLevel = metrics.nivel_actual;
        if (recommendation.prediction === 1) {
          // Avanzar
          recommendedNextLevel = Math.min(3, metrics.nivel_actual + 1);
        } else if (recommendation.prediction === 2) {
          // Retroceder
          recommendedNextLevel = Math.max(1, metrics.nivel_actual - 1);
        }
        // Si es 0 (Mantener), se deja igual

        const enrichedRecommendation: AIRecommendation = {
          ...recommendation,
          recommended_next_level: recommendedNextLevel,
          reasoning: getRecommendationReasoning(recommendation, metrics)
        };

        console.log('[useAIRecommendation] Respuesta recibida:', enrichedRecommendation);

        setState(prev => ({
          ...prev,
          recommendation: enrichedRecommendation,
          isLoading: false,
          success: true,
          error: null
        }));

        return enrichedRecommendation;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Error desconocido al obtener recomendación';

        console.error('[useAIRecommendation] Error:', errorMessage);

        setState(prev => ({
          ...prev,
          isLoading: false,
          error: errorMessage,
          success: false,
          recommendation: null
        }));

        throw err;
      }
    },
    [getAuthToken, getBackendUrl]
  );

  /**
   * Generar explicación legible de la recomendación
   */
  const getRecommendationReasoning = (
    recommendation: AIRecommendation,
    metrics: StudentMetrics
  ): string => {
    const confidence = (recommendation.confidence * 100).toFixed(1);
    const label = recommendation.prediction_label;

    let reasoning = `Recomendación: ${label} (Confianza: ${confidence}%).`;

    if (metrics.tasa_aciertos > 80) {
      reasoning += ` Excelente tasa de aciertos (${metrics.tasa_aciertos.toFixed(1)}%).`;
    } else if (metrics.tasa_aciertos < 40) {
      reasoning += ` Baja tasa de aciertos (${metrics.tasa_aciertos.toFixed(1)}%).`;
    }

    if (metrics.tiempo_promedio < 20) {
      reasoning += ` Resuelve muy rápido (${metrics.tiempo_promedio.toFixed(1)}s).`;
    } else if (metrics.tiempo_promedio > 60) {
      reasoning += ` Tarda más tiempo de lo esperado (${metrics.tiempo_promedio.toFixed(1)}s).`;
    }

    return reasoning;
  };

  /**
   * Reiniciar el estado
   */
  const reset = useCallback(() => {
    setState({
      recommendation: null,
      isLoading: false,
      error: null,
      success: false
    });
  }, []);

  /**
   * Si se proporciona metricsData, obtener recomendación automáticamente
   */
  const fetchRecommendation = useCallback(async () => {
    if (metricsData) {
      try {
        await getRecommendation(metricsData);
      } catch (err) {
        console.error('[useAIRecommendation] Auto-fetch failed:', err);
      }
    }
  }, [metricsData, getRecommendation]);

  return {
    // Estado
    recommendation: state.recommendation,
    isLoading: state.isLoading,
    error: state.error,
    success: state.success,

    // Métodos
    getRecommendation,
    reset,
    fetchRecommendation,

    // Utilidades
    getRecommendationLabel: () => state.recommendation?.prediction_label || 'N/A',
    getConfidencePercentage: () => 
      state.recommendation ? (state.recommendation.confidence * 100).toFixed(1) : '0',
    getNextLevel: () => state.recommendation?.recommended_next_level || null,
    getReasoning: () => state.recommendation?.reasoning || ''
  };
}

/**
 * Hook alternativo basado en Axios (si se prefiere)
 * Descomenta esta sección si tienes axios instalado
 */

/*
import axios, { AxiosInstance } from 'axios';

export function useAIRecommendationAxios(
  metricsData?: StudentMetrics,
  axiosInstance?: AxiosInstance
) {
  const [state, setState] = useState<UseAIRecommendationState>({
    recommendation: null,
    isLoading: false,
    error: null,
    success: false
  });

  const instance = axiosInstance || axios.create({
    baseURL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
  });

  const getRecommendation = useCallback(
    async (metrics: StudentMetrics) => {
      setState(prev => ({
        ...prev,
        isLoading: true,
        error: null
      }));

      try {
        const token = localStorage.getItem('auth_token');
        if (!token) throw new Error('No authentication token found');

        const response = await instance.post(
          '/api/ai/recommend_level',
          {
            Tasa_Aciertos: metrics.tasa_aciertos,
            Tiempo_Promedio: metrics.tiempo_promedio,
            Intentos_Fallidos: metrics.intentos_fallidos,
            Nivel_Actual: metrics.nivel_actual
          },
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );

        const recommendation: AIRecommendation = response.data;

        setState(prev => ({
          ...prev,
          recommendation,
          isLoading: false,
          success: true,
          error: null
        }));

        return recommendation;
      } catch (err) {
        const errorMessage =
          axios.isAxiosError(err)
            ? err.response?.data?.message || err.message
            : 'Error desconocido';

        setState(prev => ({
          ...prev,
          isLoading: false,
          error: errorMessage,
          success: false
        }));

        throw err;
      }
    },
    [instance]
  );

  const reset = useCallback(() => {
    setState({
      recommendation: null,
      isLoading: false,
      error: null,
      success: false
    });
  }, []);

  return {
    recommendation: state.recommendation,
    isLoading: state.isLoading,
    error: state.error,
    success: state.success,
    getRecommendation,
    reset
  };
}
*/
