#!/usr/bin/env python
"""
Test Script for AI Service
Tests the predict_next_level function with various student metrics

Usage:
    python test_ai_service.py

Author: AI Assistant
Date: December 3, 2025
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import predict_next_level, get_model_info, train_svm_model


def test_predictions():
    """Test predictions with various student metrics"""
    
    # First, ensure model is trained
    print("\n" + "="*70)
    print("  AI SERVICE TEST")
    print("="*70 + "\n")
    
    print("1️⃣ Checking Model Status\n")
    info = get_model_info()
    if not info:
        print("   ⚠️  Model not found. Training new model...")
        train_svm_model()
        info = get_model_info()
    
    if info:
        print(f"   ✅ Model loaded successfully")
        print(f"      Size: {info['model_size_mb']} MB")
        print(f"      Scaler: {'✅' if info['scaler_exists'] else '❌'}\n")
    
    # Test cases with different student performance levels
    test_cases = [
        {
            'name': '🌟 Excellent Student (Should Advance)',
            'metrics': {
                'Tasa_Aciertos': 95.0,
                'Tiempo_Promedio': 30.0,
                'Intentos_Fallidos': 2,
                'Nivel_Actual': 1
            }
        },
        {
            'name': '⭐ Good Student (Should Advance)',
            'metrics': {
                'Tasa_Aciertos': 85.0,
                'Tiempo_Promedio': 45.0,
                'Intentos_Fallidos': 5,
                'Nivel_Actual': 2
            }
        },
        {
            'name': '😐 Average Student (Should Maintain)',
            'metrics': {
                'Tasa_Aciertos': 65.0,
                'Tiempo_Promedio': 60.0,
                'Intentos_Fallidos': 15,
                'Nivel_Actual': 2
            }
        },
        {
            'name': '📉 Struggling Student (Should Regress)',
            'metrics': {
                'Tasa_Aciertos': 35.0,
                'Tiempo_Promedio': 100.0,
                'Intentos_Fallidos': 40,
                'Nivel_Actual': 3
            }
        },
        {
            'name': '❌ Very Poor Student (Should Regress)',
            'metrics': {
                'Tasa_Aciertos': 20.0,
                'Tiempo_Promedio': 110.0,
                'Intentos_Fallidos': 45,
                'Nivel_Actual': 2
            }
        }
    ]
    
    print("2️⃣ Running Predictions\n")
    print("-"*70 + "\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{test_case['name']}")
        print(f"   Input Metrics:")
        metrics = test_case['metrics']
        print(f"      Tasa de Aciertos:     {metrics['Tasa_Aciertos']:.1f}%")
        print(f"      Tiempo Promedio:      {metrics['Tiempo_Promedio']:.1f}s")
        print(f"      Intentos Fallidos:    {metrics['Intentos_Fallidos']}")
        print(f"      Nivel Actual:         {metrics['Nivel_Actual']}")
        
        try:
            result = predict_next_level(metrics)
            
            print(f"\n   🎯 Prediction Result:")
            print(f"      Action:               {result['prediction_label']}")
            print(f"      Confidence:           {result['confidence']:.2%}")
            print(f"      Probabilities:")
            probs = result['probabilities']
            print(f"         - Mantener Nivel: {probs['Mantener']:.2%}")
            print(f"         - Avanzar Nivel:  {probs['Avanzar']:.2%}")
            print(f"         - Retroceder:     {probs['Retroceder']:.2%}")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        print("\n" + "-"*70 + "\n")
    
    # Test error handling
    print("3️⃣ Testing Error Handling\n")
    
    error_cases = [
        {
            'name': 'Missing required field',
            'metrics': {
                'Tasa_Aciertos': 85.0,
                'Tiempo_Promedio': 45.0,
                # Missing: Intentos_Fallidos, Nivel_Actual
            }
        },
        {
            'name': 'Invalid accuracy (>100)',
            'metrics': {
                'Tasa_Aciertos': 150.0,  # Invalid
                'Tiempo_Promedio': 45.0,
                'Intentos_Fallidos': 5,
                'Nivel_Actual': 2
            }
        },
        {
            'name': 'Invalid level (0)',
            'metrics': {
                'Tasa_Aciertos': 85.0,
                'Tiempo_Promedio': 45.0,
                'Intentos_Fallidos': 5,
                'Nivel_Actual': 0  # Invalid (must be 1-3)
            }
        }
    ]
    
    for error_case in error_cases:
        print(f"   Testing: {error_case['name']}")
        try:
            result = predict_next_level(error_case['metrics'])
            print(f"      ❌ Expected error but got result")
        except Exception as e:
            print(f"      ✅ Caught expected error: {str(e)}")
        print()
    
    print("="*70)
    print("  ✅ ALL TESTS COMPLETED")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_predictions()
