"""
Workflow Intelligence Service - Aprende y optimiza flujos de trabajo
Intercepta eventos, almacena patrones, mejora predicciones sobre la marcha
"""
import json
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from app.extensions import db
import numpy as np

logger = logging.getLogger('app')

class WorkflowPattern:
    """Detecta y almacena patrones de flujo de trabajo"""
    
    def __init__(self):
        self.intent_sequence = []  # Secuencia de intenciones (ej: [unpaid_users, register_payment])
        self.time_between_actions = []  # Tiempo entre acciones consecutivas
        self.common_parameters = defaultdict(Counter)  # Parámetros frecuentes por intención
        self.session_start = None
        self.total_sessions = 0
        
    def record_action(self, intent, params, timestamp=None):
        """Registra una acción realizada"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if self.session_start:
            elapsed = (timestamp - self.session_start).total_seconds()
            self.time_between_actions.append(elapsed)
        
        self.intent_sequence.append(intent)
        self.session_start = timestamp
        
        # Guardar parámetros comunes
        for key, value in params.items():
            if isinstance(value, (str, int, float)):
                self.common_parameters[intent][str(value)] += 1
    
    def get_next_likely_intent(self, current_intent):
        """Predice qué intención viene después basado en patrones"""
        try:
            indices = [i for i, x in enumerate(self.intent_sequence) if x == current_intent]
            if not indices:
                return None
            
            # Mirar qué viene después del último match
            next_indices = [i + 1 for i in indices if i + 1 < len(self.intent_sequence)]
            if not next_indices:
                return None
            
            # Contar ocurrencias
            next_intents = [self.intent_sequence[i] for i in next_indices]
            most_common = Counter(next_intents).most_common(1)
            return most_common[0][0] if most_common else None
        except:
            return None
    
    def get_predicted_parameters(self, intent):
        """Retorna parámetros más probables para una intención"""
        if intent not in self.common_parameters:
            return {}
        
        params = self.common_parameters[intent]
        return {
            'most_used': params.most_common(3),
            'frequency': dict(params)
        }
    
    def export_stats(self):
        """Exporta estadísticas del patrón"""
        avg_time = np.mean(self.time_between_actions) if self.time_between_actions else 0
        
        return {
            'total_actions': len(self.intent_sequence),
            'unique_intents': len(set(self.intent_sequence)),
            'avg_time_between_actions': round(avg_time, 2),
            'intent_sequence': self.intent_sequence[-10:],  # Últimas 10
            'common_parameters': {k: dict(v.most_common(5)) for k, v in self.common_parameters.items()},
            'total_sessions': self.total_sessions
        }

# Instancia global para tracking activo
workflow_intelligence = WorkflowPattern()

def track_workflow(intent, params):
    """Rastrear flujo de trabajo automáticamente"""
    try:
        workflow_intelligence.record_action(intent, params)
        logger.info(f"📊 Workflow tracked: {intent} | Secuencia: {len(workflow_intelligence.intent_sequence)} acciones")
    except Exception as e:
        logger.error(f"Error tracking workflow: {e}")

def predict_next_action(current_intent):
    """Predecir próxima acción del usuario"""
    next_intent = workflow_intelligence.get_next_likely_intent(current_intent)
    if next_intent:
        logger.info(f"🎯 Próxima acción predicha: {next_intent}")
        return next_intent
    return None

def get_smart_defaults(intent):
    """Obtener parámetros por defecto basados en patrones"""
    predictions = workflow_intelligence.get_predicted_parameters(intent)
    if predictions and predictions.get('most_used'):
        most_common = predictions['most_used'][0]
        return {
            'suggested_value': most_common[0],
            'frequency': most_common[1],
            'alternatives': [x[0] for x in predictions['most_used'][1:]]
        }
    return {}

def get_workflow_stats():
    """Obtener estadísticas de flujos"""
    return workflow_intelligence.export_stats()
