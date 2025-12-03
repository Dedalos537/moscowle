/**
 * Ejemplo: Integración de useAIRecommendation en GamesModule
 * ñDescripción: Muestra cómo usar el hook para obtener recomendaciones
 * de nivel después de completar un juego.
 *
 * Fecha: 3 de diciembre de 2025
 * Versión: 1.0
 */

import React, { useState } from 'react';
import { useAIRecommendation, StudentMetrics } from '../hooks/useAIRecommendation';

/**
 * Componente de ejemplo: GameResultsRecommendation
 * Se muestra después de completar un juego
 */
export const GameResultsRecommendation: React.FC<{
  sessionMetrics: StudentMetrics;
  studentName?: string;
  onAccept?: (nextLevel: number) => void;
  onDismiss?: () => void;
}> = ({
  sessionMetrics,
  studentName = 'Estudiante',
  onAccept,
  onDismiss
}) => {
  const { recommendation, isLoading, error, getRecommendation } = useAIRecommendation();
  const [hasRequested, setHasRequested] = useState(false);

  const handleRequestRecommendation = async () => {
    try {
      setHasRequested(true);
      await getRecommendation(sessionMetrics);
    } catch (err) {
      console.error('Error solicitando recomendación:', err);
    }
  };

  const handleAccept = () => {
    if (recommendation?.recommended_next_level && onAccept) {
      onAccept(recommendation.recommended_next_level);
    }
  };

  if (!hasRequested) {
    return (
      <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-6 max-w-md">
        <h3 className="text-lg font-bold text-blue-900 mb-4">
          📊 Análisis de Desempeño
        </h3>
        <p className="text-gray-700 mb-4">
          Se han recopilado las métricas del juego. ¿Deseas obtener una recomendación
          de nivel para {studentName}?
        </p>
        <button
          onClick={handleRequestRecommendation}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Obtener Recomendación AI
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-gray-50 border-2 border-gray-200 rounded-lg p-6 max-w-md">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mr-3"></div>
          <p className="text-gray-700">Procesando recomendación AI...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6 max-w-md">
        <h3 className="text-lg font-bold text-red-900 mb-2">⚠️ Error</h3>
        <p className="text-red-700 mb-4">{error}</p>
        <button
          onClick={() => setHasRequested(false)}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (!recommendation) {
    return null;
  }

  // Colores según recomendación
  const getRecommendationColor = () => {
    switch (recommendation.prediction) {
      case 1: // Avanzar
        return 'green';
      case 2: // Retroceder
        return 'orange';
      default: // Mantener
        return 'blue';
    }
  };

  const getRecommendationIcon = () => {
    switch (recommendation.prediction) {
      case 1:
        return '🚀'; // Avanzar
      case 2:
        return '📚'; // Retroceder
      default:
        return '➡️'; // Mantener
    }
  };

  const colorClass = {
    green: 'bg-green-50 border-green-200',
    orange: 'bg-yellow-50 border-yellow-200',
    blue: 'bg-blue-50 border-blue-200'
  }[getRecommendationColor()];

  const textColorClass = {
    green: 'text-green-900',
    orange: 'text-yellow-900',
    blue: 'text-blue-900'
  }[getRecommendationColor()];

  return (
    <div className={`${colorClass} border-2 rounded-lg p-6 max-w-md`}>
      {/* Encabezado */}
      <div className="flex items-center justify-between mb-4">
        <h3 className={`text-2xl font-bold ${textColorClass}`}>
          {getRecommendationIcon()} {recommendation.prediction_label}
        </h3>
        <span className="bg-gray-200 text-gray-800 px-3 py-1 rounded-full text-sm font-bold">
          {(recommendation.confidence * 100).toFixed(0)}% confianza
        </span>
      </div>

      {/* Métricas */}
      <div className="mb-6 grid grid-cols-2 gap-4">
        <div className="bg-white p-3 rounded border border-gray-200">
          <p className="text-gray-600 text-sm font-semibold">Precisión</p>
          <p className="text-2xl font-bold text-gray-900">
            {sessionMetrics.tasa_aciertos.toFixed(1)}%
          </p>
        </div>
        <div className="bg-white p-3 rounded border border-gray-200">
          <p className="text-gray-600 text-sm font-semibold">Tiempo Promedio</p>
          <p className="text-2xl font-bold text-gray-900">
            {sessionMetrics.tiempo_promedio.toFixed(1)}s
          </p>
        </div>
        <div className="bg-white p-3 rounded border border-gray-200">
          <p className="text-gray-600 text-sm font-semibold">Intentos Fallidos</p>
          <p className="text-2xl font-bold text-gray-900">
            {sessionMetrics.intentos_fallidos}
          </p>
        </div>
        <div className="bg-white p-3 rounded border border-gray-200">
          <p className="text-gray-600 text-sm font-semibold">Nivel Actual</p>
          <p className="text-2xl font-bold text-gray-900">
            {sessionMetrics.nivel_actual}
          </p>
        </div>
      </div>

      {/* Distribución de probabilidades */}
      <div className="mb-6 bg-white p-4 rounded border border-gray-200">
        <p className="text-gray-700 font-semibold mb-3">Distribución de Probabilidades</p>
        <div className="space-y-2">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-600">Mantener Nivel</span>
              <span className="text-sm font-bold text-gray-900">
                {(recommendation.probabilities.Mantener * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full"
                style={{ width: `${recommendation.probabilities.Mantener * 100}%` }}
              ></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-600">Avanzar Nivel</span>
              <span className="text-sm font-bold text-gray-900">
                {(recommendation.probabilities.Avanzar * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-500 h-2 rounded-full"
                style={{ width: `${recommendation.probabilities.Avanzar * 100}%` }}
              ></div>
            </div>
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-600">Retroceder Nivel</span>
              <span className="text-sm font-bold text-gray-900">
                {(recommendation.probabilities.Retroceder * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-orange-500 h-2 rounded-full"
                style={{ width: `${recommendation.probabilities.Retroceder * 100}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Razonamiento */}
      {recommendation.reasoning && (
        <div className="mb-6 bg-white p-4 rounded border border-gray-200">
          <p className="text-gray-700 font-semibold mb-2">💡 Análisis</p>
          <p className="text-gray-600 text-sm">{recommendation.reasoning}</p>
        </div>
      )}

      {/* Información de próximo nivel */}
      {recommendation.recommended_next_level && (
        <div className="mb-6 bg-white p-4 rounded border border-gray-200">
          <p className="text-gray-700 font-semibold mb-2">📍 Próximo Nivel Recomendado</p>
          <p className="text-3xl font-bold text-gray-900">
            Nivel {recommendation.recommended_next_level}
          </p>
          <p className="text-gray-600 text-sm mt-2">
            {recommendation.prediction === 1
              ? '✅ El estudiante está listo para avanzar'
              : recommendation.prediction === 2
              ? '📚 Se recomienda repasar contenidos previos'
              : '➡️ El estudiante puede continuar al mismo nivel'}
          </p>
        </div>
      )}

      {/* Botones de acción */}
      <div className="flex gap-3">
        <button
          onClick={handleAccept}
          className={`flex-1 font-bold py-2 px-4 rounded text-white ${
            getRecommendationColor() === 'green'
              ? 'bg-green-600 hover:bg-green-700'
              : getRecommendationColor() === 'orange'
              ? 'bg-yellow-600 hover:bg-yellow-700'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          ✓ Aplicar Cambio
        </button>
        <button
          onClick={onDismiss}
          className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded"
        >
          ✕ Descartar
        </button>
      </div>
    </div>
  );
};

/**
 * Ejemplo de uso en GamesModule
 */
export const GameModuleIntegrationExample: React.FC = () => {
  const [sessionMetrics, setSessionMetrics] = useState<StudentMetrics | null>(null);
  const [showRecommendation, setShowRecommendation] = useState(false);

  // Simular completación de juego
  const handleGameComplete = (metrics: StudentMetrics) => {
    setSessionMetrics(metrics);
    setShowRecommendation(true);
  };

  const handleApplyRecommendation = (nextLevel: number) => {
    console.log('Aplicando nuevo nivel:', nextLevel);
    // Aquí iría la lógica para cambiar el nivel del estudiante
    setShowRecommendation(false);
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Módulo de Juegos</h2>

      {/* Juego */}
      <div className="bg-gray-100 p-4 rounded mb-6 border-2 border-gray-300">
        <p className="text-gray-700">Juego en progreso...</p>
        <button
          onClick={() =>
            handleGameComplete({
              tasa_aciertos: 85.5,
              tiempo_promedio: 45.3,
              intentos_fallidos: 5,
              nivel_actual: 2
            })
          }
          className="mt-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Completar Juego
        </button>
      </div>

      {/* Recomendación */}
      {showRecommendation && sessionMetrics && (
        <GameResultsRecommendation
          sessionMetrics={sessionMetrics}
          studentName="Juan García"
          onAccept={handleApplyRecommendation}
          onDismiss={() => setShowRecommendation(false)}
        />
      )}
    </div>
  );
};
