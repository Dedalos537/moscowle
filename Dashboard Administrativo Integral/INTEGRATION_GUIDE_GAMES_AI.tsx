/**
 * Guía Práctica: Integrar useAIRecommendation en GamesModule
 * 
 * Este archivo muestra paso a paso cómo integrar el hook en el
 * módulo de juegos existente.
 *
 * Fecha: 3 de diciembre de 2025
 */

// ============================================================================
// PASO 1: IMPORTAR EL HOOK
// ============================================================================

import { useAIRecommendation, StudentMetrics, AIRecommendation } from '../hooks/useAIRecommendation';

// ============================================================================
// PASO 2: DEFINIR TIPOS LOCALES
// ============================================================================

interface GameSessionData {
  game_id: number;
  student_id: number;
  accuracy_rate: number;      // 0-100
  average_time: number;       // segundos
  failed_attempts: number;
  current_level: number;      // 1-3
  completed_at: Date;
}

interface RecommendationModalState {
  isOpen: boolean;
  metrics: StudentMetrics | null;
  recommendation: AIRecommendation | null;
  isLoadingRecommendation: boolean;
}

// ============================================================================
// PASO 3: CREAR HOOK PERSONALIZADO PARA GAMES
// ============================================================================

/**
 * Hook personalizado que combina la lógica de juegos con recomendaciones
 */
export function useGameWithRecommendation() {
  const [gameSession, setGameSession] = useState<GameSessionData | null>(null);
  const [modalState, setModalState] = useState<RecommendationModalState>({
    isOpen: false,
    metrics: null,
    recommendation: null,
    isLoadingRecommendation: false
  });

  const { recommendation, isLoading, error, getRecommendation, reset } = 
    useAIRecommendation();

  /**
   * Convertir datos de sesión a métricas AI
   */
  const convertSessionToMetrics = (session: GameSessionData): StudentMetrics => {
    return {
      tasa_aciertos: session.accuracy_rate,
      tiempo_promedio: session.average_time,
      intentos_fallidos: session.failed_attempts,
      nivel_actual: session.current_level,
      sesion_id: session.game_id,
      patient_id: session.student_id
    };
  };

  /**
   * Cuando el juego se completa
   */
  const handleGameComplete = async (session: GameSessionData) => {
    try {
      // Guardar sesión
      setGameSession(session);

      // Convertir a métricas
      const metrics = convertSessionToMetrics(session);

      // Actualizar estado modal
      setModalState(prev => ({
        ...prev,
        isOpen: true,
        metrics: metrics,
        isLoadingRecommendation: true
      }));

      // Obtener recomendación
      const rec = await getRecommendation(metrics);

      // Actualizar modal con resultado
      setModalState(prev => ({
        ...prev,
        recommendation: rec,
        isLoadingRecommendation: false
      }));
    } catch (err) {
      console.error('Error en handleGameComplete:', err);
      setModalState(prev => ({
        ...prev,
        isLoadingRecommendation: false
      }));
    }
  };

  /**
   * Aceptar recomendación
   */
  const acceptRecommendation = async () => {
    if (!recommendation?.recommended_next_level) return;

    try {
      // Aquí iría la llamada para actualizar el nivel en BD
      const response = await fetch('/api/student/update-level', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          student_id: gameSession?.student_id,
          new_level: recommendation.recommended_next_level
        })
      });

      if (!response.ok) throw new Error('Failed to update level');

      // Cerrar modal y limpiar
      closeRecommendationModal();
    } catch (err) {
      console.error('Error acceptando recomendación:', err);
    }
  };

  /**
   * Descartar recomendación
   */
  const closeRecommendationModal = () => {
    setModalState({
      isOpen: false,
      metrics: null,
      recommendation: null,
      isLoadingRecommendation: false
    });
    reset();
  };

  return {
    // Estado
    gameSession,
    modalState,
    isLoading,
    error,

    // Métodos
    handleGameComplete,
    acceptRecommendation,
    closeRecommendationModal
  };
}

// ============================================================================
// PASO 4: USAR EN GAMESMODULE
// ============================================================================

/**
 * Componente GamesModule actualizado con soporte para recomendaciones AI
 */
export const GamesModuleWithAI: React.FC = () => {
  const [games, setGames] = useState<Game[]>([]);
  const [currentGame, setCurrentGame] = useState<Game | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const {
    gameSession,
    modalState,
    isLoading,
    error,
    handleGameComplete,
    acceptRecommendation,
    closeRecommendationModal
  } = useGameWithRecommendation();

  // Cargar juegos
  useEffect(() => {
    loadGames();
  }, []);

  const loadGames = async () => {
    // Implementar carga de juegos
  };

  const startGame = (game: Game) => {
    setCurrentGame(game);
    setIsPlaying(true);
  };

  const onGameEnd = (metrics: GameSessionData) => {
    setIsPlaying(false);
    handleGameComplete(metrics);
  };

  return (
    <div className="games-module">
      {/* Área de juegos */}
      {!isPlaying ? (
        <GamesList games={games} onSelectGame={startGame} />
      ) : (
        <GameComponent game={currentGame!} onEnd={onGameEnd} />
      )}

      {/* Modal de recomendación */}
      {modalState.isOpen && (
        <RecommendationModal
          isOpen={modalState.isOpen}
          isLoading={modalState.isLoadingRecommendation}
          recommendation={modalState.recommendation}
          metrics={modalState.metrics}
          error={error}
          onAccept={acceptRecommendation}
          onDismiss={closeRecommendationModal}
        />
      )}
    </div>
  );
};

// ============================================================================
// PASO 5: COMPONENTES DE UI
// ============================================================================

/**
 * Modal que muestra la recomendación
 */
interface RecommendationModalProps {
  isOpen: boolean;
  isLoading: boolean;
  recommendation: AIRecommendation | null;
  metrics: StudentMetrics | null;
  error: string | null;
  onAccept: () => void;
  onDismiss: () => void;
}

export const RecommendationModal: React.FC<RecommendationModalProps> = ({
  isOpen,
  isLoading,
  recommendation,
  metrics,
  error,
  onAccept,
  onDismiss
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-2xl w-full max-h-96 overflow-y-auto">
        {/* Encabezado */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold">Recomendación de Nivel</h2>
          <button
            onClick={onDismiss}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-lg text-gray-600">Analizando desempeño...</span>
          </div>
        )}

        {/* Error */}
        {error && !isLoading && (
          <div className="bg-red-50 border border-red-200 rounded p-4 mb-4">
            <p className="text-red-700">❌ {error}</p>
          </div>
        )}

        {/* Contenido */}
        {!isLoading && recommendation && metrics && (
          <div className="space-y-6">
            {/* Recomendación Principal */}
            <RecommendationHeader recommendation={recommendation} />

            {/* Métricas */}
            <MetricsDisplay metrics={metrics} />

            {/* Gráfico de Probabilidades */}
            <ProbabilityChart probabilities={recommendation.probabilities} />

            {/* Análisis */}
            {recommendation.reasoning && (
              <div className="bg-blue-50 border border-blue-200 rounded p-4">
                <p className="text-sm text-blue-900">
                  💡 {recommendation.reasoning}
                </p>
              </div>
            )}

            {/* Acciones */}
            <div className="flex gap-4 pt-4">
              <button
                onClick={onAccept}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded"
              >
                ✓ Aplicar Cambio
              </button>
              <button
                onClick={onDismiss}
                className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-3 px-4 rounded"
              >
                ✕ Descartar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Encabezado con recomendación principal
 */
const RecommendationHeader: React.FC<{ recommendation: AIRecommendation }> = ({
  recommendation
}) => {
  const getIcon = () => {
    if (recommendation.prediction === 1) return '🚀';
    if (recommendation.prediction === 2) return '📚';
    return '➡️';
  };

  const getColor = () => {
    if (recommendation.prediction === 1) return 'text-green-600';
    if (recommendation.prediction === 2) return 'text-yellow-600';
    return 'text-blue-600';
  };

  return (
    <div className="flex items-center justify-between bg-gray-50 p-4 rounded">
      <div>
        <p className={`text-4xl font-bold ${getColor()}`}>
          {getIcon()} {recommendation.prediction_label}
        </p>
        <p className="text-gray-600 mt-2">
          Próximo Nivel: <span className="font-bold">{recommendation.recommended_next_level}</span>
        </p>
      </div>
      <div className="text-right">
        <p className="text-gray-600 text-sm">Confianza</p>
        <p className="text-3xl font-bold text-gray-900">
          {(recommendation.confidence * 100).toFixed(0)}%
        </p>
      </div>
    </div>
  );
};

/**
 * Mostrar métricas del estudiante
 */
const MetricsDisplay: React.FC<{ metrics: StudentMetrics }> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-gray-50 p-4 rounded">
        <p className="text-gray-600 text-sm font-semibold">Precisión</p>
        <p className="text-3xl font-bold text-gray-900">
          {metrics.tasa_aciertos.toFixed(1)}%
        </p>
      </div>
      <div className="bg-gray-50 p-4 rounded">
        <p className="text-gray-600 text-sm font-semibold">Tiempo Promedio</p>
        <p className="text-3xl font-bold text-gray-900">
          {metrics.tiempo_promedio.toFixed(1)}s
        </p>
      </div>
      <div className="bg-gray-50 p-4 rounded">
        <p className="text-gray-600 text-sm font-semibold">Intentos Fallidos</p>
        <p className="text-3xl font-bold text-gray-900">
          {metrics.intentos_fallidos}
        </p>
      </div>
      <div className="bg-gray-50 p-4 rounded">
        <p className="text-gray-600 text-sm font-semibold">Nivel Actual</p>
        <p className="text-3xl font-bold text-gray-900">
          {metrics.nivel_actual}
        </p>
      </div>
    </div>
  );
};

/**
 * Gráfico de probabilidades
 */
const ProbabilityChart: React.FC<{ probabilities: Record<string, number> }> = ({
  probabilities
}) => {
  return (
    <div className="bg-gray-50 p-4 rounded">
      <p className="text-gray-600 text-sm font-semibold mb-4">Distribución de Probabilidades</p>
      <div className="space-y-3">
        {Object.entries(probabilities).map(([label, value]) => (
          <div key={label}>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-600">{label}</span>
              <span className="text-sm font-bold">{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${value * 100}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// PASO 6: USAR EN EXISTING GAMESMODULE
// ============================================================================

// En tu GamesModule.tsx existente, solo agrega:

/*
import { useAIRecommendation } from '../hooks/useAIRecommendation';

// En el componente:
const { recommendation, isLoading, error, getRecommendation } = useAIRecommendation();

// Cuando se completa el juego:
const onGameComplete = async (sessionData) => {
  const metrics = {
    tasa_aciertos: sessionData.accuracy_rate,
    tiempo_promedio: sessionData.average_time,
    intentos_fallidos: sessionData.failed_attempts,
    nivel_actual: sessionData.current_level
  };

  try {
    await getRecommendation(metrics);
    // Mostrar recomendación al usuario
  } catch (err) {
    console.error('Error:', err);
  }
};
*/

export default GamesModuleWithAI;
