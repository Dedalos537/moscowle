#!/usr/bin/env python
"""
AI Service Integration Examples
Ejemplos prácticos de cómo usar el módulo ai_service en el backend

Author: AI Assistant
Date: December 3, 2025
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import (
    predict_next_level,
    train_svm_model,
    get_model_info,
    AIServiceError
)


# ============================================================================
# EJEMPLO 1: Predicción Simple
# ============================================================================

def example_simple_prediction():
    """Predicción básica para un estudiante"""
    print("\n" + "="*70)
    print("EJEMPLO 1: Predicción Simple")
    print("="*70 + "\n")
    
    # Métricas de un estudiante
    student_metrics = {
        'Tasa_Aciertos': 88.5,
        'Tiempo_Promedio': 42.3,
        'Intentos_Fallidos': 4,
        'Nivel_Actual': 2
    }
    
    print("📊 Métricas del Estudiante:")
    print(f"   Tasa de Aciertos:    {student_metrics['Tasa_Aciertos']:.1f}%")
    print(f"   Tiempo Promedio:     {student_metrics['Tiempo_Promedio']:.1f}s")
    print(f"   Intentos Fallidos:   {student_metrics['Intentos_Fallidos']}")
    print(f"   Nivel Actual:        {student_metrics['Nivel_Actual']}")
    
    # Hacer predicción
    result = predict_next_level(student_metrics)
    
    print(f"\n🎯 Resultado de Predicción:")
    print(f"   Acción:              {result['prediction_label']}")
    print(f"   Confianza:           {result['confidence']:.2%}")
    print(f"   Valor Numérico:      {result['prediction']}")
    
    return result


# ============================================================================
# EJEMPLO 2: Lote de Predicciones
# ============================================================================

def example_batch_predictions():
    """Predicción para múltiples estudiantes"""
    print("\n" + "="*70)
    print("EJEMPLO 2: Lote de Predicciones")
    print("="*70 + "\n")
    
    students = [
        {
            'id': 1,
            'name': 'María García',
            'metrics': {
                'Tasa_Aciertos': 92.0,
                'Tiempo_Promedio': 35.0,
                'Intentos_Fallidos': 2,
                'Nivel_Actual': 1
            }
        },
        {
            'id': 2,
            'name': 'Juan Pérez',
            'metrics': {
                'Tasa_Aciertos': 65.5,
                'Tiempo_Promedio': 65.0,
                'Intentos_Fallidos': 18,
                'Nivel_Actual': 2
            }
        },
        {
            'id': 3,
            'name': 'Ana López',
            'metrics': {
                'Tasa_Aciertos': 40.0,
                'Tiempo_Promedio': 95.0,
                'Intentos_Fallidos': 35,
                'Nivel_Actual': 3
            }
        }
    ]
    
    predictions = []
    
    for student in students:
        print(f"📝 Prediciendo para {student['name']}...")
        result = predict_next_level(student['metrics'])
        
        prediction = {
            'student_id': student['id'],
            'name': student['name'],
            'prediction': result['prediction'],
            'prediction_label': result['prediction_label'],
            'confidence': result['confidence']
        }
        predictions.append(prediction)
        
        print(f"   ✓ {result['prediction_label']} ({result['confidence']:.1%})\n")
    
    # Resumen
    print("📊 RESUMEN:")
    advance = sum(1 for p in predictions if p['prediction'] == 1)
    maintain = sum(1 for p in predictions if p['prediction'] == 0)
    regress = sum(1 for p in predictions if p['prediction'] == 2)
    
    print(f"   Avanzar:     {advance} estudiantes")
    print(f"   Mantener:    {maintain} estudiantes")
    print(f"   Retroceder:  {regress} estudiantes")
    
    return predictions


# ============================================================================
# EJEMPLO 3: Análisis por Confianza
# ============================================================================

def example_confidence_analysis():
    """Analizar predicciones agrupadas por confianza"""
    print("\n" + "="*70)
    print("EJEMPLO 3: Análisis por Confianza")
    print("="*70 + "\n")
    
    # Generar predicciones variadas
    test_cases = [
        {'accuracy': 95.0, 'time': 30.0, 'failures': 1, 'level': 1},
        {'accuracy': 80.0, 'time': 50.0, 'failures': 8, 'level': 2},
        {'accuracy': 60.0, 'time': 70.0, 'failures': 20, 'level': 2},
        {'accuracy': 30.0, 'time': 100.0, 'failures': 40, 'level': 3},
        {'accuracy': 70.0, 'time': 60.0, 'failures': 15, 'level': 2},
    ]
    
    high_confidence = []
    medium_confidence = []
    low_confidence = []
    
    for case in test_cases:
        metrics = {
            'Tasa_Aciertos': case['accuracy'],
            'Tiempo_Promedio': case['time'],
            'Intentos_Fallidos': case['failures'],
            'Nivel_Actual': case['level']
        }
        
        result = predict_next_level(metrics)
        confidence = result['confidence']
        
        if confidence >= 0.9:
            high_confidence.append(result)
        elif confidence >= 0.75:
            medium_confidence.append(result)
        else:
            low_confidence.append(result)
    
    print(f"🔴 Alta Confianza (≥90%):      {len(high_confidence)} predicciones")
    for pred in high_confidence:
        print(f"   • {pred['prediction_label']} ({pred['confidence']:.1%})")
    
    print(f"\n🟡 Confianza Media (75-90%):   {len(medium_confidence)} predicciones")
    for pred in medium_confidence:
        print(f"   • {pred['prediction_label']} ({pred['confidence']:.1%})")
    
    print(f"\n🟢 Baja Confianza (<75%):      {len(low_confidence)} predicciones")
    for pred in low_confidence:
        print(f"   • {pred['prediction_label']} ({pred['confidence']:.1%})")


# ============================================================================
# EJEMPLO 4: Simulación de Progresión de Estudiante
# ============================================================================

def example_student_progression():
    """Simular progresión de un estudiante a lo largo de múltiples sesiones"""
    print("\n" + "="*70)
    print("EJEMPLO 4: Progresión del Estudiante")
    print("="*70 + "\n")
    
    print("📈 Simulando progresión de Juan a lo largo de 6 sesiones...\n")
    
    # Simular mejora progresiva del estudiante
    sessions = [
        {
            'session': 1,
            'accuracy': 45.0,
            'time': 90.0,
            'failures': 30,
            'level': 1,
            'description': 'Primera sesión - Bajo desempeño'
        },
        {
            'session': 2,
            'accuracy': 55.0,
            'time': 75.0,
            'failures': 25,
            'level': 1,
            'description': 'Mejorando lentamente'
        },
        {
            'session': 3,
            'accuracy': 65.0,
            'time': 60.0,
            'failures': 18,
            'level': 1,
            'description': 'Progreso visible'
        },
        {
            'session': 4,
            'accuracy': 72.0,
            'time': 55.0,
            'failures': 12,
            'level': 2,
            'description': 'Rindió bien, pasó a nivel 2'
        },
        {
            'session': 5,
            'accuracy': 80.0,
            'time': 48.0,
            'failures': 7,
            'level': 2,
            'description': 'Dominando nivel 2'
        },
        {
            'session': 6,
            'accuracy': 88.0,
            'time': 40.0,
            'failures': 3,
            'level': 2,
            'description': 'Listo para nivel 3'
        }
    ]
    
    predictions_log = []
    
    for session in sessions:
        metrics = {
            'Tasa_Aciertos': session['accuracy'],
            'Tiempo_Promedio': session['time'],
            'Intentos_Fallidos': session['failures'],
            'Nivel_Actual': session['level']
        }
        
        result = predict_next_level(metrics)
        
        print(f"Sesión {session['session']}: {session['description']}")
        print(f"  📊 Accuracy: {session['accuracy']:.1f}% | Tiempo: {session['time']:.0f}s")
        print(f"  🎯 Predicción: {result['prediction_label']} ({result['confidence']:.1%})")
        
        predictions_log.append({
            'session': session['session'],
            'prediction': result['prediction_label'],
            'confidence': result['confidence']
        })
        
        print()
    
    return predictions_log


# ============================================================================
# EJEMPLO 5: Manejo de Errores
# ============================================================================

def example_error_handling():
    """Demostrar manejo de errores"""
    print("\n" + "="*70)
    print("EJEMPLO 5: Manejo de Errores")
    print("="*70 + "\n")
    
    error_cases = [
        {
            'name': 'Campo faltante',
            'metrics': {'Tasa_Aciertos': 85.0}  # Faltan otros campos
        },
        {
            'name': 'Valor fuera de rango (accuracy > 100)',
            'metrics': {
                'Tasa_Aciertos': 150.0,
                'Tiempo_Promedio': 45.0,
                'Intentos_Fallidos': 5,
                'Nivel_Actual': 2
            }
        },
        {
            'name': 'Nivel inválido',
            'metrics': {
                'Tasa_Aciertos': 85.0,
                'Tiempo_Promedio': 45.0,
                'Intentos_Fallidos': 5,
                'Nivel_Actual': 5  # Debe ser 1-3
            }
        },
        {
            'name': 'Intentos fallidos negativo',
            'metrics': {
                'Tasa_Aciertos': 85.0,
                'Tiempo_Promedio': 45.0,
                'Intentos_Fallidos': -5,  # No puede ser negativo
                'Nivel_Actual': 2
            }
        }
    ]
    
    for case in error_cases:
        print(f"❌ Caso: {case['name']}")
        try:
            result = predict_next_level(case['metrics'])
            print(f"   Resultado: {result['prediction_label']}\n")
        except AIServiceError as e:
            print(f"   Error capturado: {str(e)}\n")


# ============================================================================
# EJEMPLO 6: Información del Modelo
# ============================================================================

def example_model_info():
    """Ver información del modelo entrenado"""
    print("\n" + "="*70)
    print("EJEMPLO 6: Información del Modelo")
    print("="*70 + "\n")
    
    info = get_model_info()
    
    if info:
        print("✅ Modelo Entrenado")
        print(f"   Ruta:        {info['model_path']}")
        print(f"   Tamaño:      {info['model_size_mb']} MB")
        print(f"   Escalador:   {'✅' if info['scaler_exists'] else '❌'}")
        print(f"   Tamaño Total: {info['total_size_mb']} MB")
        print(f"   Fecha:       {info['modification_time']}")
    else:
        print("❌ Modelo no entrenado")
        print("   Ejecuta: python train_model.py")


# ============================================================================
# EJEMPLO 7: JSON Response para API
# ============================================================================

def example_json_response():
    """Ejemplo de respuesta JSON para API"""
    print("\n" + "="*70)
    print("EJEMPLO 7: Respuesta JSON para API")
    print("="*70 + "\n")
    
    metrics = {
        'Tasa_Aciertos': 87.0,
        'Tiempo_Promedio': 48.0,
        'Intentos_Fallidos': 6,
        'Nivel_Actual': 2
    }
    
    result = predict_next_level(metrics)
    
    # Simulando respuesta de API
    api_response = {
        'status': 'success',
        'data': {
            'id': 42,
            'patient_id': 1,
            'game_name': 'Memoria Visual',
            'metrics': metrics,
            'ai_prediction': {
                'prediction': result['prediction'],
                'label': result['prediction_label'],
                'confidence': result['confidence'],
                'probabilities': result['probabilities']
            }
        }
    }
    
    print("📤 Respuesta JSON:")
    print(json.dumps(api_response, indent=2, ensure_ascii=False))


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecutar todos los ejemplos"""
    print("\n" + "="*70)
    print("  AI SERVICE - EJEMPLOS DE INTEGRACIÓN")
    print("="*70)
    
    try:
        # Ejecutar ejemplos
        example_simple_prediction()
        example_batch_predictions()
        example_confidence_analysis()
        example_student_progression()
        example_error_handling()
        example_model_info()
        example_json_response()
        
        print("\n" + "="*70)
        print("  ✅ TODOS LOS EJEMPLOS COMPLETADOS")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error en ejemplos: {str(e)}\n")
        return 1
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
