#!/usr/bin/env python
"""
SVM Model Training Script
Trains and serializes the SVM model for level prediction in Moscowle

Usage:
    python train_model.py              # Train with default 500 samples
    python train_model.py --samples 1000  # Train with custom samples
    python train_model.py --info       # Display current model info
    python train_model.py --delete     # Delete existing model

Author: AI Assistant
Date: December 3, 2025
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import train_svm_model, get_model_info, delete_model


def main():
    """Main entry point for training script"""
    
    parser = argparse.ArgumentParser(
        description='Train and manage SVM model for Moscowle AI predictions'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=500,
        help='Number of synthetic samples to generate (default: 500)'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set proportion (default: 0.2)'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Display current model information'
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete existing model and scaler'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  SVM MODEL TRAINING SCRIPT - MOSCOWLE AI SERVICE")
    print("="*70 + "\n")
    
    # Handle delete
    if args.delete:
        print("🗑️  Deleting model and scaler...")
        if delete_model():
            print("✅ Model deleted successfully\n")
        else:
            print("⚠️  No model found to delete\n")
        return
    
    # Handle info
    if args.info:
        print("📊 Model Information\n")
        info = get_model_info()
        if info:
            print(f"  Model exists:     ✅")
            print(f"  Model path:       {info['model_path']}")
            print(f"  Model size:       {info['model_size_mb']} MB")
            print(f"  Scaler exists:    {'✅' if info['scaler_exists'] else '❌'}")
            print(f"  Scaler size:      {info['scaler_size_mb']} MB")
            print(f"  Total size:       {info['total_size_mb']} MB")
            print(f"  Last modified:    {info['modification_time']}\n")
        else:
            print("  ❌ No model found\n")
            print("  Run this script without --info to train a new model\n")
        return
    
    # Train model
    print(f"🚀 Training SVM Model")
    print(f"  Samples:     {args.samples}")
    print(f"  Test size:   {args.test_size}")
    print(f"  Kernel:      RBF")
    print(f"  Features:    ['Tasa_Aciertos', 'Tiempo_Promedio', 'Intentos_Fallidos', 'Nivel_Actual']")
    print(f"  Target:      'Siguiente_Nivel' (0: Mantener, 1: Avanzar, 2: Retroceder)")
    print("\n" + "-"*70 + "\n")
    
    try:
        results = train_svm_model(
            n_samples=args.samples,
            test_size=args.test_size
        )
        
        print("\n" + "-"*70)
        print("\n✅ MODEL TRAINING COMPLETED SUCCESSFULLY\n")
        
        print("📈 Performance Metrics")
        print(f"  Accuracy:        {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)")
        print(f"  Precision:       {results['precision']:.4f}")
        print(f"  Recall:          {results['recall']:.4f}")
        print(f"  F1 Score:        {results['f1']:.4f}")
        
        print(f"\n🔧 Model Details")
        print(f"  Training samples: {results['n_samples']}")
        print(f"  Support vectors:  {results['n_support_vectors']}")
        print(f"  Classes:          {results['classes']}")
        print(f"  Features:         {results['feature_names']}")
        
        print(f"\n💾 Saved Files")
        print(f"  Model:   {results['model_path']}")
        print(f"  Scaler:  {results['scaler_path']}")
        
        print("\n✨ Ready for predictions!")
        print("   Import: from app.services.ai_service import predict_next_level")
        print("   Usage:  result = predict_next_level(metrics_data)")
        
        print("\n" + "="*70 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        print("="*70 + "\n")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
